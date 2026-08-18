"""Finalize Node.

Saves analysis results and structured optimized resumes for on-demand PDF generation.
Publishes the terminal 'complete' SSE event to the client.
"""

import asyncio
import json
import logging
from typing import Any, Dict

from app.api.schemas import AnalyzeResponse, ExperienceExample, OptimizationResult
from app.graph.state import GraphState
from app.services.temp_storage import get_session_dir

logger = logging.getLogger(__name__)


async def _publish(queue: asyncio.Queue, event: str, data: dict) -> None:
    if queue:
        await queue.put((event, data))


async def finalize_node(state: GraphState) -> Dict[str, Any]:
    queue = state.get("queue")
    session_id = state["session_id"]
    resume_analysis = state.get("resume_analysis")
    job_analyses = state.get("job_analyses", [])
    optimized_resumes = state.get("optimized_resumes", [])
    experience_examples_data = state.get("experience_examples", [])

    # Prepare optimization results metadata (download URLs will generate PDF on-demand)
    optimization_results: list[OptimizationResult] = []
    for idx, opt in enumerate(optimized_resumes):
        job_idx = opt.job_index if opt.job_index is not None else idx
        download_url = f"/api/v1/download/{session_id}/{job_idx}"
        optimization_results.append(
            OptimizationResult(
                job_index=opt.job_index,
                download_url=download_url,
                changes_summary=opt.changes_made,
                estimated_score_after=opt.estimated_ats_score,
            )
        )

    # Convert experience examples to typed models
    parsed_examples = [ExperienceExample.model_validate(ex) for ex in experience_examples_data]

    response = AnalyzeResponse(
        session_id=session_id,
        resume_analysis=resume_analysis,
        job_analyses=job_analyses,
        optimizations=optimization_results,
        experience_examples=parsed_examples,
    )

    session_dir = get_session_dir(session_id)
    session_dir.mkdir(parents=True, exist_ok=True)

    # Save full API response
    result_path = session_dir / "result.json"
    result_path.write_text(response.model_dump_json(indent=2), encoding="utf-8")

    # Save serialized optimized resumes specifically for on-demand PDF generator service
    optimized_path = session_dir / "optimized_resumes.json"
    optimized_payload = [opt.model_dump() for opt in optimized_resumes]
    optimized_path.write_text(json.dumps(optimized_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    await _publish(queue, "complete", {
        "progress": 100,
        "message": "Análise concluída com sucesso! Seu resultado está pronto.",
        "session_id": session_id,
        "result": response.model_dump(),
    })

    return {
        "optimization_results": optimization_results,
    }
