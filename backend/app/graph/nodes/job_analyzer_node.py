"""Job Analyzer Node."""

import asyncio
import logging
from typing import Any, Dict
from app.agents.job_agent import JobAnalystAgent
from app.api.schemas import JobAnalysis
from app.config import settings
from app.domain.job import StructuredJob
from app.graph.state import GraphState

logger = logging.getLogger(__name__)


async def _publish(queue: asyncio.Queue, event: str, data: dict) -> None:
    if queue:
        await queue.put((event, data))


async def job_analyzer_node(state: GraphState) -> Dict[str, Any]:
    queue = state.get("queue")
    jobs = state["jobs"]
    total_jobs = len(jobs)

    await _publish(queue, "progress", {
        "step": "job_analysis", "progress": 25,
        "message": f"Analisando {total_jobs} descrição(ões) de vaga...",
    })

    job_agent = JobAnalystAgent()
    job_tasks = [job_agent.analyze(job, idx) for idx, job in enumerate(jobs)]
    results = await asyncio.wait_for(
        asyncio.gather(*job_tasks),
        timeout=settings.llm_timeout,
    )

    structured_jobs: list[StructuredJob] = [r[0] for r in results]
    job_analyses: list[JobAnalysis] = [r[1] for r in results]

    structured_jobs_sorted = sorted(structured_jobs, key=lambda sj: sj.job_index)
    job_analyses_sorted = sorted(job_analyses, key=lambda ja: ja.job_index)

    await _publish(queue, "progress", {
        "step": "job_analysis", "progress": 40,
        "message": "Análise de vaga(s) concluída.",
    })

    return {
        "structured_jobs": structured_jobs_sorted,
        "job_analyses": job_analyses_sorted,
    }
