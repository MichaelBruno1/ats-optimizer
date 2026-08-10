"""PDF Generation Node."""

import asyncio
import logging
from typing import Any, Dict
from app.api.schemas import OptimizationResult
from app.graph.state import GraphState
from app.services.pdf_generator import generate_pdf
from app.services.temp_storage import get_pdf_path

logger = logging.getLogger(__name__)


async def _publish(queue: asyncio.Queue, event: str, data: dict) -> None:
    if queue:
        await queue.put((event, data))


async def generate_pdfs_node(state: GraphState) -> Dict[str, Any]:
    queue = state.get("queue")
    session_id = state["session_id"]
    resume_analysis = state["resume_analysis"]
    optimized_resumes = state["optimized_resumes"]

    await _publish(queue, "progress", {
        "step": "pdf_generation", "progress": 85,
        "message": "Gerando arquivo(s) PDF...",
    })

    optimization_results: list[OptimizationResult] = []
    loop = asyncio.get_event_loop()

    for optimized in optimized_resumes:
        idx = optimized.job_index if optimized.job_index is not None else 0
        pdf_path = get_pdf_path(session_id, idx)

        await loop.run_in_executor(
            None, generate_pdf, optimized, pdf_path, resume_analysis,
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

    await _publish(queue, "progress", {
        "step": "pdf_generation", "progress": 95,
        "message": "PDF(s) gerados com sucesso.",
    })

    return {
        "optimization_results": optimization_results,
        "pdf_generated": True,
    }
