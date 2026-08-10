"""Node functions for the ATS optimization LangGraph pipeline.

Each node corresponds to one stage of the original _run_pipeline function,
preserving all business logic, SSE progress publishing, and error handling.
"""

import asyncio
import json
import logging
from typing import Any, Dict

from app.agents.job_analyst import JobAnalystAgent
from app.agents.resume_analyst import ResumeAnalystAgent
from app.agents.resume_optimizer import ResumeOptimizerAgent
from app.api.schemas import (
    AnalyzeResponse,
    OptimizationResult,
    OptimizedResume,
    ResumeAnalysis,
)
from app.config import settings
from app.services.pdf_generator import generate_pdf
from app.services.temp_storage import get_pdf_path, get_session_dir

from .state import GraphState

logger = logging.getLogger(__name__)


async def _publish(queue: asyncio.Queue, event: str, data: dict) -> None:
    """Publish an SSE event to a session queue."""
    await queue.put((event, data))


# ── Node 1: Resume Analysis ──────────────────────────────────────────────────


async def analyze_resume_node(state: GraphState) -> Dict[str, Any]:
    """Execute ResumeAnalystAgent and return updated state."""
    queue = state["queue"]

    await _publish(queue, "progress", {
        "step": "resume_analysis", "progress": 5,
        "message": "Analisando currículo...",
    })

    resume_agent = ResumeAnalystAgent()
    resume_analysis: ResumeAnalysis = await asyncio.wait_for(
        resume_agent.analyze(state["resume_text"]),
        timeout=settings.llm_timeout,
    )

    await _publish(queue, "progress", {
        "step": "resume_analysis", "progress": 20,
        "message": "Análise de currículo concluída.",
    })

    return {"resume_analysis": resume_analysis}


# ── Node 2: Job Analysis (concurrent) ────────────────────────────────────────


async def analyze_jobs_node(state: GraphState) -> Dict[str, Any]:
    """Execute JobAnalystAgent for all jobs concurrently."""
    queue = state["queue"]
    jobs = state["jobs"]
    total_jobs = len(jobs)

    await _publish(queue, "progress", {
        "step": "job_analysis", "progress": 25,
        "message": f"Analisando {total_jobs} descrição(ões) de vaga...",
    })

    job_agent = JobAnalystAgent()
    job_tasks = [job_agent.analyze(job, idx) for idx, job in enumerate(jobs)]
    job_analyses = await asyncio.wait_for(
        asyncio.gather(*job_tasks),
        timeout=settings.llm_timeout,
    )
    job_analyses_sorted = sorted(job_analyses, key=lambda ja: ja.job_index)

    await _publish(queue, "progress", {
        "step": "job_analysis", "progress": 50,
        "message": "Análise de vaga(s) concluída.",
    })

    return {"job_analyses": job_analyses_sorted}


# ── Node 3: Resume Optimization ──────────────────────────────────────────────


async def optimize_node(state: GraphState) -> Dict[str, Any]:
    """Execute ResumeOptimizerAgent in single or per_job mode."""
    if state.get("error"):
        logger.warning("Skipping optimization due to prior error: %s", state["error"])
        return {}

    resume_analysis = state.get("resume_analysis")
    job_analyses = state.get("job_analyses")
    if not resume_analysis or not job_analyses:
        logger.warning("Missing analysis results — skipping optimization.")
        return {"error": "Missing resume or job analysis"}

    queue = state["queue"]
    output_mode = state["output_mode"]
    resume_text = state["resume_text"]

    opt_mode_desc = "modo unificado" if output_mode == "single" else "modo por vaga"
    await _publish(queue, "progress", {
        "step": "optimization", "progress": 55,
        "message": f"Otimizando currículo ({opt_mode_desc})...",
    })

    optimizer = ResumeOptimizerAgent()
    optimized_resumes: list[OptimizedResume] = []

    if output_mode == "single":
        optimized = await asyncio.wait_for(
            optimizer.optimize_single(
                resume_analysis=resume_analysis,
                job_analyses=job_analyses,
                original_resume_text=resume_text,
            ),
            timeout=settings.llm_timeout,
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
            await asyncio.wait_for(
                asyncio.gather(*opt_tasks),
                timeout=settings.llm_timeout,
            )
        )

    await _publish(queue, "progress", {
        "step": "optimization", "progress": 75,
        "message": "Otimização concluída.",
    })

    return {"optimized_resumes": optimized_resumes}


# ── Node 4: PDF Generation ───────────────────────────────────────────────────


async def generate_pdfs_node(state: GraphState) -> Dict[str, Any]:
    """Generate PDF files for each optimized resume using WeasyPrint."""
    queue = state["queue"]
    session_id = state["session_id"]
    resume_analysis = state["resume_analysis"]
    optimized_resumes = state["optimized_resumes"]

    await _publish(queue, "progress", {
        "step": "pdf_generation", "progress": 80,
        "message": "Gerando PDF(s)...",
    })

    optimization_results: list[OptimizationResult] = []
    loop = asyncio.get_event_loop()

    for optimized in optimized_resumes:
        idx = optimized.job_index if optimized.job_index is not None else 0
        pdf_path = get_pdf_path(session_id, idx)

        # Run WeasyPrint in a thread pool to avoid blocking the event loop
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


# ── Node 5: Finalize ─────────────────────────────────────────────────────────


async def finalize_node(state: GraphState) -> Dict[str, Any]:
    """Build final response, persist result.json, and publish 'complete' SSE."""
    queue = state["queue"]
    session_id = state["session_id"]

    response = AnalyzeResponse(
        session_id=session_id,
        resume_analysis=state["resume_analysis"],
        job_analyses=state["job_analyses"],
        optimizations=state["optimization_results"],
    )

    # Persist serialized result for late-arriving SSE consumers
    result_path = get_session_dir(session_id) / "result.json"
    result_path.write_text(
        response.model_dump_json(indent=2), encoding="utf-8",
    )

    await _publish(queue, "complete", {
        "progress": 100,
        "message": "Processamento concluído. Seu currículo otimizado está pronto!",
        "session_id": session_id,
        "result": response.model_dump(),
    })

    return {}
