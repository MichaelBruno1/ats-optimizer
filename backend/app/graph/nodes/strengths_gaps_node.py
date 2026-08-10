"""Strengths & Gaps Node."""

import asyncio
import logging
from typing import Any, Dict
from app.agents.strength_gap_agent import StrengthGapAnalystAgent
from app.graph.state import GraphState

logger = logging.getLogger(__name__)


async def strengths_gaps_node(state: GraphState) -> Dict[str, Any]:
    resume = state["structured_resume"]
    jobs = state["structured_jobs"]
    match_results = state["match_results"]

    agent = StrengthGapAnalystAgent()
    strengths, weaknesses, gap_summary = await agent.analyze_strengths_and_gaps(
        resume, jobs[0], match_results[0]
    )

    resume_analysis = state.get("resume_analysis")
    if resume_analysis:
        resume_analysis.strengths = strengths
        resume_analysis.weaknesses = weaknesses

    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "gap_analysis_summary": gap_summary,
        "resume_analysis": resume_analysis,
    }
