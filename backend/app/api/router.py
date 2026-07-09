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

from app.agents.job_analyst import JobAnalystAgent
from app.agents.resume_analyst import ResumeAnalystAgent
from app.agents.resume_optimizer import ResumeOptimizerAgent
from app.api.schemas import (
    AnalyzeResponse,
    JobAnalysis,
    JobInput,
    OptimizationResult,
    OptimizedResume,
    ResumeAnalysis,
)
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

# Sentinel value published to a queue when processing ends
_DONE_SENTINEL = "__DONE__"


# ─────────────────────────────────────────────────────────────────────────────
# Helper: SSE event formatting
# ─────────────────────────────────────────────────────────────────────────────


def _sse_event(event: str, data: dict) -> str:
    """Format a single Server-Sent Event string.

    Args:
        event: The SSE event type name.
        data: The event payload dict (will be JSON-serialised).

    Returns:
        Properly formatted SSE string with event name and data fields.
    """
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _publish(queue: asyncio.Queue, event: str, data: dict) -> None:
    """Publish an SSE event to a session queue.

    Args:
        queue: The asyncio.Queue for the session.
        event: SSE event type name.
        data: Event payload.
    """
    await queue.put((event, data))


# ─────────────────────────────────────────────────────────────────────────────
# Background processing pipeline
# ─────────────────────────────────────────────────────────────────────────────


async def _run_pipeline(
    session_id: str,
    resume_text: str,
    jobs: list[JobInput],
    output_mode: str,
    queue: asyncio.Queue,
) -> None:
    """Full ATS Optimizer processing pipeline, executed as a background task.

    Stages:
      1. Resume analysis (resume analyst agent)
      2. Job analysis — all jobs processed concurrently (job analyst agent)
      3. Resume optimization — single or per_job mode (optimizer agent)
      4. PDF generation for each optimized resume

    Progress events are published to ``queue`` at each stage. A terminal
    'complete' or 'error' event is always published at the end, followed by
    the _DONE_SENTINEL to signal the SSE generator to close.

    Args:
        session_id: The session identifier used to locate temp storage.
        resume_text: Extracted plain text from the uploaded resume.
        jobs: List of job inputs submitted by the user.
        output_mode: 'single' or 'per_job'.
        queue: asyncio.Queue for publishing SSE progress events.
    """
    try:
        # ── Stage 1: Resume Analysis ──────────────────────────────────────────
        await _publish(
            queue, "progress",
            {"step": "resume_analysis", "progress": 5, "message": "Analisando currículo..."}
        )

        resume_agent = ResumeAnalystAgent()
        resume_analysis: ResumeAnalysis = await asyncio.wait_for(
            resume_agent.analyze(resume_text), timeout=settings.llm_timeout
        )

        await _publish(
            queue, "progress",
            {"step": "resume_analysis", "progress": 20, "message": "Análise de currículo concluída."}
        )

        # ── Stage 2: Job Analysis (concurrent) ───────────────────────────────
        total_jobs = len(jobs)
        await _publish(
            queue, "progress",
            {
                "step": "job_analysis",
                "progress": 25,
                "message": f"Analisando {total_jobs} descrição(ões) de vaga...",
            }
        )

        job_agent = JobAnalystAgent()
        job_tasks = [
            job_agent.analyze(job, idx) for idx, job in enumerate(jobs)
        ]
        job_analyses: list[JobAnalysis] = await asyncio.wait_for(
            asyncio.gather(*job_tasks), timeout=settings.llm_timeout
        )
        # Ensure order by index
        job_analyses.sort(key=lambda ja: ja.job_index)

        await _publish(
            queue, "progress",
            {"step": "job_analysis", "progress": 50, "message": "Análise de vaga(s) concluída."}
        )

        # ── Stage 3: Optimization ─────────────────────────────────────────────
        opt_mode_desc = "modo unificado" if output_mode == "single" else "modo por vaga"
        await _publish(
            queue, "progress",
            {
                "step": "optimization",
                "progress": 55,
                "message": f"Otimizando currículo ({opt_mode_desc})...",
            }
        )

        optimizer = ResumeOptimizerAgent()
        optimized_resumes: list[OptimizedResume] = []

        if output_mode == "single":
            optimized = await asyncio.wait_for(
                optimizer.optimize_single(
                    resume_analysis=resume_analysis,
                    job_analyses=job_analyses,
                    original_resume_text=resume_text,
                ),
                timeout=settings.llm_timeout
            )
            optimized_resumes.append(optimized)
        else:  # per_job
            opt_tasks = [
                optimizer.optimize_for_job(
                    resume_analysis=resume_analysis,
                    job_analysis=ja,
                    original_resume_text=resume_text,
                )
                for ja in job_analyses
            ]
            optimized_resumes = list(
                await asyncio.wait_for(asyncio.gather(*opt_tasks), timeout=settings.llm_timeout)
            )

        await _publish(
            queue, "progress",
            {"step": "optimization", "progress": 75, "message": "Otimização concluída."}
        )

        # ── Stage 4: PDF Generation ────────────────────────────────────────────
        await _publish(
            queue, "progress",
            {"step": "pdf_generation", "progress": 80, "message": "Gerando PDF(s)..."}
        )

        optimization_results: list[OptimizationResult] = []

        for optimized in optimized_resumes:
            # Use job_index from model or fall back to 0 for single mode
            idx = optimized.job_index if optimized.job_index is not None else 0
            pdf_path = get_pdf_path(session_id, idx)

            # Run WeasyPrint in a thread pool to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                generate_pdf,
                optimized,
                pdf_path,
                resume_analysis,
            )

            download_url = f"/api/v1/download/{session_id}/{idx}"
            optimization_results.append(
                OptimizationResult(
                    job_index=optimized.job_index,
                    download_url=download_url,
                    changes_summary=optimized.changes_made,
                    estimated_score_after=optimized.estimated_ats_score,
                )
            )

        await _publish(
            queue, "progress",
            {"step": "pdf_generation", "progress": 95, "message": "PDF(s) gerados com sucesso."}
        )

        # ── Build final response payload ──────────────────────────────────────
        response = AnalyzeResponse(
            session_id=session_id,
            resume_analysis=resume_analysis,
            job_analyses=job_analyses,
            optimizations=optimization_results,
        )

        # Store the serialized result so GET /progress can include it in
        # the 'complete' event for frontends that use the SSE channel.
        result_path = get_session_dir(session_id) / "result.json"
        result_path.write_text(
            response.model_dump_json(indent=2), encoding="utf-8"
        )

        await _publish(
            queue, "complete",
            {
                "progress": 100,
                "message": "Processamento concluído. Seu currículo otimizado está pronto!",
                "session_id": session_id,
                "result": response.model_dump(),
            }
        )

    except Exception as exc:
        logger.exception("Pipeline failed for session %s", session_id)
        await _publish(
            queue, "error",
            {"message": f"Falha no processamento: {exc}"}
        )

    finally:
        # Signal the SSE generator to close the stream
        await queue.put(_DONE_SENTINEL)


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

    # ── Parse and validate resume file ───────────────────────────────────────
    try:
        resume_text = await extract_text_from_upload(resume)
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
        _run_pipeline(
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
