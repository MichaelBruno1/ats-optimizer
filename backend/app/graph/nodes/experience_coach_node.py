"""Experience Coach Node."""

import asyncio
import logging
from typing import Any, Dict

from app.agents.experience_coach_agent import ExperienceCoachAgent
from app.graph.state import GraphState

logger = logging.getLogger(__name__)


async def _publish(queue: asyncio.Queue, event: str, data: dict) -> None:
    if queue:
        await queue.put((event, data))


async def experience_coach_node(state: GraphState) -> Dict[str, Any]:
    queue = state.get("queue")
    resume = state["structured_resume"]
    jobs = state["structured_jobs"]

    await _publish(queue, "progress", {
        "step": "coach", "progress": 58,
        "message": "Elaborando sugestões de aprimoramento para descrição de experiências...",
    })

    coach = ExperienceCoachAgent()
    examples = await coach.generate_suggestions(resume, jobs)

    return {
        "experience_examples": [e.model_dump() for e in examples],
    }
