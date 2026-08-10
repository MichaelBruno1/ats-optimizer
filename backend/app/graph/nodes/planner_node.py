"""Optimization Planner Node."""

import asyncio
import logging
from typing import Any, Dict
from app.agents.planner_agent import OptimizationPlannerAgent
from app.domain.optimization import OptimizationPlan
from app.graph.state import GraphState

logger = logging.getLogger(__name__)


async def _publish(queue: asyncio.Queue, event: str, data: dict) -> None:
    if queue:
        await queue.put((event, data))


async def planner_node(state: GraphState) -> Dict[str, Any]:
    queue = state.get("queue")
    resume = state["structured_resume"]
    jobs = state["structured_jobs"]
    match_results = state["match_results"]

    await _publish(queue, "progress", {
        "step": "planning", "progress": 55,
        "message": "Gerando plano estratégico de otimização...",
    })

    planner = OptimizationPlannerAgent()
    plans: list[OptimizationPlan] = []

    for job, m_res in zip(jobs, match_results):
        plan = await planner.create_plan(resume, job, m_res)
        plans.append(plan)

    return {"optimization_plans": plans}
