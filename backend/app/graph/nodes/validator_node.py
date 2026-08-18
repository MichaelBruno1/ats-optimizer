"""ATS & Anti-Hallucination Validator Node.

Combines programmatic anti-hallucination validation with deterministic ATS score recalculation.
Tracks score progression across optimization iterations to stop when score no longer improves.
"""

import asyncio
import logging
from typing import Any, Dict

from app.agents.validator_agent import ATSValidatorAgent
from app.domain.resume import (
    ContactInfo,
    EducationEntry,
    ExperienceEntry,
    StructuredResume,
)
from app.domain.scoring import ATSScoreResult
from app.domain.validation import ValidationResult
from app.graph.state import GraphState
from app.services.matching_engine import MatchingEngine
from app.services.scoring import ScoringService

logger = logging.getLogger(__name__)


async def _publish(queue: asyncio.Queue, event: str, data: dict) -> None:
    if queue:
        await queue.put((event, data))


def _build_structured_from_optimized(
    optimized,
    structured_resume: StructuredResume,
) -> StructuredResume:
    """Reconstruct a StructuredResume model from an OptimizedResume for deterministic re-scoring."""
    exp_entries = []
    for e in optimized.content.experience:
        exp_entries.append(
            ExperienceEntry(
                company=e.company,
                role=e.role,
                start_date=e.start_date,
                end_date=e.end_date,
                description=e.description,
                achievements=e.achievements,
            )
        )

    edu_entries = []
    for ed in optimized.content.education:
        edu_entries.append(
            EducationEntry(
                institution=ed.institution,
                degree=ed.degree,
                field=ed.field,
                graduation_year=ed.graduation_year,
            )
        )

    raw_text = (
        f"{optimized.content.professional_summary}\n"
        f"Habilidades: {', '.join(optimized.content.skills)}\n"
        + "\n".join(
            f"{e.role} {e.company} {e.description} {' '.join(e.achievements)}"
            for e in optimized.content.experience
        )
    )

    return StructuredResume(
        candidate_name=structured_resume.candidate_name,
        contact_info=structured_resume.contact_info or ContactInfo(),
        professional_summary=optimized.content.professional_summary,
        skills=optimized.content.skills,
        experience=exp_entries,
        education=edu_entries,
        certifications=optimized.content.certifications,
        languages=structured_resume.languages,
        total_years_experience=structured_resume.total_years_experience,
        formatting_issues=[],
        raw_text=raw_text,
    )


async def validator_node(state: GraphState) -> Dict[str, Any]:
    queue = state.get("queue")
    optimized_resumes = state.get("optimized_resumes", [])
    structured_resume = state["structured_resume"]
    structured_jobs = state["structured_jobs"]
    resume_text = state["resume_text"]
    current_history = list(state.get("score_history", []))

    iteration = state.get("optimization_iteration", 1)

    await _publish(queue, "progress", {
        "step": "validation", "progress": 78,
        "message": f"Validando qualidade, normas ATS e anti-alucinação (iteração {iteration})...",
    })

    validator = ATSValidatorAgent()
    validation_results: list[ValidationResult] = []
    all_approved = True

    for opt in optimized_resumes:
        res = await validator.validate(opt, structured_resume, resume_text)
        validation_results.append(res)
        if not res.approved:
            all_approved = False

    # ── Recalculate deterministic ATS score for optimized resume(s) ───
    scoring_service = ScoringService()
    ats_scores_after: list[ATSScoreResult] = []
    iteration_scores: list[int] = []

    for idx, opt in enumerate(optimized_resumes):
        target_job = structured_jobs[idx] if idx < len(structured_jobs) else structured_jobs[0]
        opt_structured = _build_structured_from_optimized(opt, structured_resume)

        match_res = MatchingEngine.match(opt_structured, target_job)
        score_res = scoring_service.calculate_score(opt_structured, target_job, match_res)

        ats_scores_after.append(score_res)
        iteration_scores.append(score_res.score)

        # Update the estimated_ats_score and compatibility_score on the OptimizedResume model
        opt.estimated_ats_score = score_res.score
        opt.compatibility_score = score_res.score

    # Compute current overall score (average across jobs if multiple)
    avg_score = int(round(sum(iteration_scores) / len(iteration_scores))) if iteration_scores else 0
    current_history.append(avg_score)

    logger.info(
        "Iteration %d ATS score after optimization: %d (Score history: %s)",
        iteration,
        avg_score,
        current_history,
    )

    await _publish(queue, "progress", {
        "step": "validation", "progress": 82,
        "message": f"Score ATS calculado na iteração {iteration}: {avg_score} pontos.",
    })

    return {
        "validation_results": validation_results,
        "approved": all_approved,
        "ats_scores_after": ats_scores_after,
        "score_history": current_history,
    }
