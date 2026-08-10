"""Resume Optimizer Node."""

import asyncio
import logging
from typing import Any, Dict
from app.agents.optimizer_agent import ResumeOptimizerAgent
from app.api.schemas import OptimizedResume
from app.config import settings
from app.graph.state import GraphState

logger = logging.getLogger(__name__)


async def _publish(queue: asyncio.Queue, event: str, data: dict) -> None:
    if queue:
        await queue.put((event, data))


async def optimizer_node(state: GraphState) -> Dict[str, Any]:
    queue = state.get("queue")
    output_mode = state["output_mode"]
    resume_text = state["resume_text"]
    resume_analysis = state["resume_analysis"]
    job_analyses = state["job_analyses"]
    structured_resume = state.get("structured_resume")
    plans = state.get("optimization_plans", [])

    current_iter = state.get("optimization_iteration", 0) + 1

    opt_mode_desc = "modo unificado" if output_mode == "single" else "modo por vaga"
    await _publish(queue, "progress", {
        "step": "optimization", "progress": 60 + min(15, current_iter * 5),
        "message": f"Otimizando currículo ({opt_mode_desc} — iteração {current_iter})...",
    })

    optimizer = ResumeOptimizerAgent()
    optimized_resumes: list[OptimizedResume] = []

    if output_mode == "single":
        opt = await asyncio.wait_for(
            optimizer.optimize_single(
                resume_analysis=resume_analysis,
                job_analyses=job_analyses,
                original_resume_text=resume_text,
                structured_resume=structured_resume,
                optimization_plan=plans[0] if plans else None,
            ),
            timeout=settings.llm_timeout,
        )
        optimized_resumes.append(opt)
    else:
        opt_tasks = [
            optimizer.optimize_for_job(
                resume_analysis=resume_analysis,
                job_analysis=ja,
                original_resume_text=resume_text,
                structured_resume=structured_resume,
                optimization_plan=plans[idx] if idx < len(plans) else None,
            )
            for idx, ja in enumerate(job_analyses)
        ]
        optimized_resumes = list(
            await asyncio.wait_for(
                asyncio.gather(*opt_tasks),
                timeout=settings.llm_timeout,
            )
        )

    return {
        "optimized_resumes": optimized_resumes,
        "optimization_iteration": current_iter,
    }
