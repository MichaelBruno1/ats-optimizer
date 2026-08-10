"""Matcher & Scoring Node (Deterministic)."""

import asyncio
import logging
from typing import Any, Dict
from app.domain.eligibility import EligibilityResult
from app.domain.matching import JobMatchResult
from app.domain.scoring import ATSScoreResult
from app.graph.state import GraphState
from app.services.eligibility import EligibilityService
from app.services.matching_engine import MatchingEngine
from app.services.scoring import ScoringService

logger = logging.getLogger(__name__)


async def _publish(queue: asyncio.Queue, event: str, data: dict) -> None:
    if queue:
        await queue.put((event, data))


async def matcher_node(state: GraphState) -> Dict[str, Any]:
    queue = state.get("queue")
    resume = state["structured_resume"]
    jobs = state["structured_jobs"]

    await _publish(queue, "progress", {
        "step": "matching", "progress": 45,
        "message": "Executando motor de matching e scoring determinístico...",
    })

    match_results: list[JobMatchResult] = []
    ats_scores_before: list[ATSScoreResult] = []
    eligibility_results: list[EligibilityResult] = []

    scoring_service = ScoringService()

    for job in jobs:
        m_res = MatchingEngine.match(resume, job)
        s_res = scoring_service.calculate_score(resume, job, m_res)
        e_res = EligibilityService.evaluate_eligibility(resume, job, m_res)

        match_results.append(m_res)
        ats_scores_before.append(s_res)
        eligibility_results.append(e_res)

    # Update legacy ATS scores in ResumeAnalysis & JobAnalysis
    resume_analysis = state.get("resume_analysis")
    job_analyses = state.get("job_analyses")

    if resume_analysis and ats_scores_before:
        resume_analysis.ats_readability_score = ats_scores_before[0].score

    if job_analyses:
        for ja, score_res, match_res in zip(job_analyses, ats_scores_before, match_results):
            ja.compatibility_score = score_res.score
            ja.ats_keywords = match_res.matched_keywords
            ja.gap_analysis = f"Palavras-chave ausentes: {', '.join(match_res.missing_keywords[:10])}."

    await _publish(queue, "progress", {
        "step": "matching", "progress": 50,
        "message": "Matching e cálculo de pontuação concluídos.",
    })

    return {
        "match_results": match_results,
        "ats_scores_before": ats_scores_before,
        "eligibility_results": eligibility_results,
        "resume_analysis": resume_analysis,
        "job_analyses": job_analyses,
    }
