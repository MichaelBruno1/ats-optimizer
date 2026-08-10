"""ATS & Anti-Hallucination Validator Node."""

import asyncio
import logging
from typing import Any, Dict
from app.agents.validator_agent import ATSValidatorAgent
from app.domain.validation import ValidationResult
from app.graph.state import GraphState

logger = logging.getLogger(__name__)


async def _publish(queue: asyncio.Queue, event: str, data: dict) -> None:
    if queue:
        await queue.put((event, data))


async def validator_node(state: GraphState) -> Dict[str, Any]:
    queue = state.get("queue")
    optimized_resumes = state.get("optimized_resumes", [])
    structured_resume = state["structured_resume"]
    resume_text = state["resume_text"]

    await _publish(queue, "progress", {
        "step": "validation", "progress": 78,
        "message": "Validando currículo otimizado (anti-alucinação e normas ATS)...",
    })

    validator = ATSValidatorAgent()
    validation_results: list[ValidationResult] = []

    all_approved = True

    for opt in optimized_resumes:
        res = await validator.validate(opt, structured_resume, resume_text)
        validation_results.append(res)
        if not res.approved:
            all_approved = False

    return {
        "validation_results": validation_results,
        "approved": all_approved,
    }
