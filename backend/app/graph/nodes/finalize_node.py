"""Finalize Node."""

import asyncio
import logging
from typing import Any, Dict
from app.api.schemas import AnalyzeResponse
from app.graph.state import GraphState
from app.services.temp_storage import get_session_dir

logger = logging.getLogger(__name__)


async def _publish(queue: asyncio.Queue, event: str, data: dict) -> None:
    if queue:
        await queue.put((event, data))


async def finalize_node(state: GraphState) -> Dict[str, Any]:
    queue = state.get("queue")
    session_id = state["session_id"]

    response = AnalyzeResponse(
        session_id=session_id,
        resume_analysis=state["resume_analysis"],
        job_analyses=state["job_analyses"],
        optimizations=state["optimization_results"],
    )

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
