"""Resume Optimizer Agent.

Produces ATS-optimized resume content by intelligently reorganizing and
rephrasing the candidate's existing experience to match job requirements.

STRICT RULE: The agent NEVER fabricates information. It only reformulates
what is already present in the resume analysis.
"""

import json
import logging

from app.agents.base_agent import AgentError, BaseAgent
from app.api.schemas import (
    JobAnalysis,
    OptimizedResume,
    ResumeAnalysis,
)

logger = logging.getLogger(__name__)


class ResumeOptimizerAgent(BaseAgent):
    """Transforms a resume to maximize ATS compatibility for target job(s).

    Supports two output modes:
    - ``single``: One balanced resume optimized for all provided job analyses.
    - ``per_job``: A highly focused resume for a single job analysis.
    """

    system_prompt_file = "resume_optimization.txt"

    async def optimize_single(
        self,
        resume_analysis: ResumeAnalysis,
        job_analyses: list[JobAnalysis],
        original_resume_text: str,
    ) -> OptimizedResume:
        """Create one balanced resume optimized for all provided jobs.

        Args:
            resume_analysis: Structured analysis of the candidate's resume.
            job_analyses: List of all analyzed job descriptions.
            original_resume_text: Raw resume text (for context/grounding).

        Returns:
            A validated OptimizedResume with job_index=None.

        Raises:
            AgentError: If the LLM call fails or validation fails.
        """
        all_job_titles = ", ".join(ja.title for ja in job_analyses)
        all_keywords = sorted(
            {kw for ja in job_analyses for kw in ja.ats_keywords}
        )

        user_message = self._build_message(
            mode="single",
            resume_analysis=resume_analysis,
            job_analyses=job_analyses,
            original_resume_text=original_resume_text,
            target_description=(
                f"Target roles: {all_job_titles}\n"
                f"Combined ATS keywords to prioritize: {', '.join(all_keywords[:40])}"
            ),
        )

        logger.info(
            "Optimizing resume (single mode) for %d job(s): %s",
            len(job_analyses),
            all_job_titles,
        )
        raw = await self._invoke(user_message)
        raw["job_index"] = None

        try:
            return OptimizedResume.model_validate(raw)
        except Exception as exc:
            logger.error(
                "OptimizedResume (single) validation failed: %s — raw: %s",
                exc,
                json.dumps(raw)[:400],
            )
            raise AgentError(
                f"Optimization response (single) failed schema validation: {exc}"
            ) from exc

    async def optimize_for_job(
        self,
        resume_analysis: ResumeAnalysis,
        job_analysis: JobAnalysis,
        original_resume_text: str,
    ) -> OptimizedResume:
        """Create a focused resume optimized exclusively for one specific job.

        Args:
            resume_analysis: Structured analysis of the candidate's resume.
            job_analysis: Analysis of the specific target job.
            original_resume_text: Raw resume text (for context/grounding).

        Returns:
            A validated OptimizedResume with the correct job_index.

        Raises:
            AgentError: If the LLM call fails or validation fails.
        """
        user_message = self._build_message(
            mode="per_job",
            resume_analysis=resume_analysis,
            job_analyses=[job_analysis],
            original_resume_text=original_resume_text,
            target_description=(
                f"Target role: {job_analysis.title}"
                + (f" at {job_analysis.company}" if job_analysis.company else "")
                + f"\nJob index: {job_analysis.job_index}"
                + f"\nATS keywords to incorporate: {', '.join(job_analysis.ats_keywords[:30])}"
                + f"\nRequired skills: {', '.join(job_analysis.required_skills[:20])}"
            ),
        )

        logger.info(
            "Optimizing resume (per_job mode) for job #%d: '%s'",
            job_analysis.job_index,
            job_analysis.title,
        )
        raw = await self._invoke(user_message)
        raw["job_index"] = job_analysis.job_index

        try:
            return OptimizedResume.model_validate(raw)
        except Exception as exc:
            logger.error(
                "OptimizedResume (job #%d) validation failed: %s — raw: %s",
                job_analysis.job_index,
                exc,
                json.dumps(raw)[:400],
            )
            raise AgentError(
                f"Optimization response for job #{job_analysis.job_index} "
                f"failed schema validation: {exc}"
            ) from exc

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _build_message(
        mode: str,
        resume_analysis: ResumeAnalysis,
        job_analyses: list[JobAnalysis],
        original_resume_text: str,
        target_description: str,
    ) -> str:
        """Compose the user-turn message for the optimizer agent.

        Args:
            mode: 'single' or 'per_job'.
            resume_analysis: Parsed resume structure.
            job_analyses: One or more job analyses to optimize for.
            original_resume_text: Original resume text for context.
            target_description: Human-readable summary of the target job(s).

        Returns:
            Formatted string to send as the user message.
        """
        job_analyses_json = json.dumps(
            [ja.model_dump() for ja in job_analyses], ensure_ascii=False, indent=2
        )
        resume_analysis_json = json.dumps(
            resume_analysis.model_dump(), ensure_ascii=False, indent=2
        )

        return (
            f"Mode: {mode}\n\n"
            f"{target_description}\n\n"
            f"=== ORIGINAL RESUME TEXT (ground truth — do not invent beyond this) ===\n"
            f"{original_resume_text[:6000]}\n\n"
            f"=== STRUCTURED RESUME ANALYSIS ===\n"
            f"{resume_analysis_json}\n\n"
            f"=== JOB ANALYSIS (target requirements) ===\n"
            f"{job_analyses_json}"
        )
