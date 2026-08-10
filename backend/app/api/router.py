"""API Router for ATS Optimizer.

Implements all five endpoints:
- POST   /api/v1/analyze          — Upload resume + jobs, run full pipeline
- GET    /api/v1/download/{id}/{i} — Download generated PDF
- GET    /api/v1/progress/{id}    — Server-Sent Events for progress
- GET    /api/v1/health           — Health check
- GET    /api/v1/config           — App configuration metadata

Architecture (SSE + async):
  POST /analyze creates a session, registers an asyncio Queue, launches
  the processing pipeline as a background asyncio task, and returns the
  session_id immediately so the frontend can open the SSE channel.
  The pipeline task publishes progress events to the Queue.
  GET /progress/{session_id} streams those events as SSE until it receives
  the terminal 'complete' or 'error' event.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import AsyncGenerator

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from app.api.schemas import JobInput
from app.graph.pipeline import run_graph_pipeline
from app.config import settings
from app.services.document_parser import (
    DocumentParseError,
    FileTooLargeError,
    UnsupportedFormatError,
    extract_text_from_upload,
)
from app.services.pdf_generator import generate_pdf
from app.services.temp_storage import (
    create_session,
    deregister_queue,
    get_pdf_path,
    get_queue,
    get_session_dir,
    register_queue,
    session_exists,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Re-import SSE helpers needed by the progress endpoint
_DONE_SENTINEL = "__DONE__"


def _sse_event(event: str, data: dict) -> str:
    """Format a single Server-Sent Event string.

    Args:
        event: The SSE event type name.
        data: The event payload dict (will be JSON-serialised).

    Returns:
        Properly formatted SSE string with event name and data fields.
    """
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/analyze",
    response_model=dict,
    summary="Submit resume and job descriptions for ATS optimization",
    description=(
        "Upload a resume file and one or more job descriptions. "
        "Returns a session_id immediately. Use GET /progress/{session_id} "
        "for real-time progress via Server-Sent Events, then GET /download "
        "to retrieve the optimized PDF."
    ),
)
async def analyze(
    resume: UploadFile = File(..., description="Resume file (.pdf, .docx, .txt — max 5 MB)"),
    jobs: str = Form(..., description="JSON array of {title, company?, description}"),
    output_mode: str = Form(
        default="single",
        description="'single' (one balanced resume) or 'per_job' (one per vacancy)",
    ),
) -> dict:
    """Accept a resume upload + job list, start the pipeline, return session_id."""
    # ── Validate output_mode ──────────────────────────────────────────────────
    if output_mode not in ("single", "per_job"):
        raise HTTPException(
            status_code=422,
            detail="output_mode must be 'single' or 'per_job'.",
        )

    # ── Parse jobs JSON ───────────────────────────────────────────────────────
    try:
        raw_jobs = json.loads(jobs)
        if not isinstance(raw_jobs, list) or not raw_jobs:
            raise ValueError("jobs must be a non-empty JSON array.")
        job_list: list[JobInput] = [JobInput.model_validate(j) for j in raw_jobs]
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"Invalid jobs payload: {exc}") from exc

    if len(job_list) > settings.max_jobs:
        raise HTTPException(
            status_code=422,
            detail=f"Too many jobs. Maximum is {settings.max_jobs}, received {len(job_list)}.",
        )

    try:
        resume_text = await extract_text_from_upload(resume)
        # Safety truncation to prevent local LLM context window overflows
        MAX_RESUME_CHARS = 12000
        if len(resume_text) > MAX_RESUME_CHARS:
            logger.warning(
                "Extracted resume text too long (%d chars). Truncating to %d chars.",
                len(resume_text),
                MAX_RESUME_CHARS
            )
            resume_text = (
                resume_text[:MAX_RESUME_CHARS]
                + "\n\n... [Conteúdo truncado para conformidade com a janela de contexto do modelo] ..."
            )
    except FileTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except UnsupportedFormatError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except DocumentParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # ── Create session & register SSE queue ──────────────────────────────────
    session_id = create_session()
    queue = register_queue(session_id)

    logger.info(
        "New session %s — mode=%s, jobs=%d, resume_chars=%d",
        session_id,
        output_mode,
        len(job_list),
        len(resume_text),
    )

    # ── Launch background pipeline ────────────────────────────────────────────
    asyncio.create_task(
        run_graph_pipeline(
            session_id=session_id,
            resume_text=resume_text,
            jobs=job_list,
            output_mode=output_mode,
            queue=queue,
        ),
        name=f"pipeline-{session_id}",
    )

    # Return immediately with the session_id so the frontend can open SSE
    return {"session_id": session_id, "message": "Processing started. Connect to the SSE endpoint for progress."}


@router.get(
    "/progress/{session_id}",
    summary="Stream real-time processing progress via Server-Sent Events",
    description=(
        "Opens an SSE stream for the given session. Events are emitted as the "
        "pipeline progresses through resume analysis, job analysis, optimization, "
        "and PDF generation. The stream closes after a 'complete' or 'error' event."
    ),
)
async def progress(session_id: str) -> StreamingResponse:
    """SSE endpoint that streams pipeline progress events for a session."""
    queue = get_queue(session_id)
    if queue is None:
        # Session may have already completed — try to return the stored result
        result_path = get_session_dir(session_id) / "result.json"
        if result_path.exists():
            result_data = json.loads(result_path.read_text(encoding="utf-8"))

            async def _already_done() -> AsyncGenerator[str, None]:
                yield _sse_event(
                    "complete",
                    {
                        "progress": 100,
                        "message": "Processing already complete.",
                        "session_id": session_id,
                        "result": result_data,
                    },
                )

            return StreamingResponse(
                _already_done(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no",
                },
            )

        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' not found or has expired.",
        )

    async def _event_generator() -> AsyncGenerator[str, None]:
        """Consume the session queue and yield SSE-formatted strings."""
        try:
            while True:
                item = await asyncio.wait_for(queue.get(), timeout=settings.llm_timeout)

                if item is _DONE_SENTINEL:
                    deregister_queue(session_id)
                    break

                event_name, event_data = item
                yield _sse_event(event_name, event_data)

                # Stop streaming after terminal events
                if event_name in ("complete", "error"):
                    deregister_queue(session_id)
                    break

        except asyncio.TimeoutError:
            yield _sse_event("error", {"message": "Processing timed out after 120 seconds."})
            deregister_queue(session_id)

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get(
    "/download/{session_id}/{job_index}",
    summary="Download the optimized PDF resume",
    description="Returns the generated PDF file for the given session and job index.",
)
async def download(session_id: str, job_index: int) -> FileResponse:
    """Serve the generated PDF file as a downloadable attachment."""
    if not session_exists(session_id):
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' not found or has expired.",
        )

    pdf_path = get_pdf_path(session_id, job_index)
    if not pdf_path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                f"PDF for job_index={job_index} not found in session '{session_id}'. "
                "The file may still be generating or the index may be invalid."
            ),
        )

    filename = f"optimized_resume_{job_index}.pdf"
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/health",
    summary="Health check",
    description="Returns the service health status and current LLM configuration.",
)
async def health() -> dict:
    """Simple health check endpoint."""
    return {
        "status": "healthy",
        "llm_provider": settings.llm_provider,
        "model": settings.llm_model,
    }


@router.get(
    "/config",
    summary="Application configuration",
    description="Returns public configuration metadata for the frontend.",
)
async def config() -> dict:
    """Return public application configuration."""
    return {
        "provider": settings.llm_provider,
        "model": settings.llm_model,
        "max_jobs": settings.max_jobs,
        "accepted_formats": [".pdf", ".docx", ".txt"],
        "max_file_size_mb": settings.max_file_size_mb,
        "output_modes": ["single", "per_job"],
        "llm_timeout": settings.llm_timeout,
    }
