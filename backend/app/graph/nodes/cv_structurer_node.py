"""CV Structurer Node with Caching."""

import asyncio
import logging
from typing import Any, Dict
from app.agents.cv_agent import CVStructurerAgent
from app.api.schemas import ResumeAnalysis
from app.config import settings
from app.graph.state import GraphState
from app.services.resume_cache import ResumeCacheService

logger = logging.getLogger(__name__)


async def _publish(queue: asyncio.Queue, event: str, data: dict) -> None:
    if queue:
        await queue.put((event, data))


async def cv_structurer_node(state: GraphState) -> Dict[str, Any]:
    queue = state.get("queue")
    resume_text = state["resume_text"]

    # 1. Check cache first
    cached = ResumeCacheService.get(resume_text)
    if cached:
        cached_structured, cached_analysis = cached
        await _publish(queue, "progress", {
            "step": "resume_analysis", "progress": 20,
            "message": "Estruturação de currículo recuperada do cache com sucesso.",
        })
        return {
            "structured_resume": cached_structured,
            "resume_analysis": cached_analysis,
        }

    await _publish(queue, "progress", {
        "step": "resume_analysis", "progress": 5,
        "message": "Analisando e estruturando currículo...",
    })

    cv_agent = CVStructurerAgent()
    structured_resume = await asyncio.wait_for(
        cv_agent.structure_cv(resume_text),
        timeout=settings.llm_timeout,
    )

    # Legacy ResumeAnalysis compatibility
    resume_analysis = ResumeAnalysis(
        candidate_name=structured_resume.candidate_name,
        contact_info=structured_resume.contact_info.model_dump(),
        professional_summary=structured_resume.professional_summary,
        skills=structured_resume.skills,
        experience=[
            {
                "company": e.company,
                "role": e.role,
                "start_date": e.start_date,
                "end_date": e.end_date,
                "description": e.description,
                "achievements": e.achievements,
            }
            for e in structured_resume.experience
        ],
        education=[
            {
                "institution": ed.institution,
                "degree": ed.degree,
                "field": ed.field,
                "graduation_year": ed.graduation_year,
            }
            for ed in structured_resume.education
        ],
        certifications=structured_resume.certifications,
        languages=structured_resume.languages,
        total_years_experience=structured_resume.total_years_experience,
        formatting_issues=structured_resume.formatting_issues,
        ats_readability_score=85,
    )

    # 2. Store in cache for subsequent runs
    ResumeCacheService.set(resume_text, structured_resume, resume_analysis)

    await _publish(queue, "progress", {
        "step": "resume_analysis", "progress": 20,
        "message": "Estruturação de currículo concluída.",
    })

    return {
        "structured_resume": structured_resume,
        "resume_analysis": resume_analysis,
    }
