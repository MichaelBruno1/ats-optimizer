"""Resume Optimizer Agent.

Transforms candidate resumes according to the OptimizationPlan while strictly preventing hallucination.
"""

import asyncio
import json
import logging
from app.agents.base_agent import AgentError, BaseAgent
from app.api.schemas import JobAnalysis, OptimizedResume, ResumeAnalysis
from app.domain.optimization import OptimizationPlan
from app.domain.resume import StructuredResume
from app.services.skill_normalization import normalize_skill

logger = logging.getLogger(__name__)


class ResumeOptimizerAgent(BaseAgent):
    """Executes ATS optimization based on structured analysis and optimization plan."""

    system_prompt_file = "resume_optimization.md"

    @property
    def semaphore(self) -> asyncio.Semaphore:
        if not hasattr(self, "_semaphore"):
            self._semaphore = asyncio.Semaphore(3)
        return self._semaphore

    def _filter_hallucinated_skills(
        self,
        optimized: OptimizedResume,
        structured_resume: StructuredResume,
        original_resume_text: str,
    ) -> None:
        """Programmatic safety post-processing check to prune hallucinated/unsupported skills."""
        orig_skills_norm = {normalize_skill(s).canonical.lower() for s in structured_resume.skills}
        orig_text_lower = original_resume_text.lower()

        filtered_skills = []
        for skill in optimized.content.skills:
            norm_s = normalize_skill(skill).canonical.lower()
            if norm_s in orig_skills_norm or skill.lower().strip() in orig_text_lower:
                filtered_skills.append(skill)
            else:
                logger.warning(
                    "Safety Filter: Removed hallucinated skill '%s' not present in original resume.",
                    skill
                )
        optimized.content.skills = filtered_skills

    async def optimize_single(
        self,
        resume_analysis: ResumeAnalysis,
        job_analyses: list[JobAnalysis],
        original_resume_text: str,
        structured_resume: StructuredResume | None = None,
        optimization_plan: OptimizationPlan | None = None,
    ) -> OptimizedResume:
        all_job_titles = ", ".join(ja.title for ja in job_analyses)
        all_keywords = sorted({kw for ja in job_analyses for kw in ja.ats_keywords})

        plan_desc = ""
        if optimization_plan:
            plan_desc = f"\n=== OPTIMIZATION PLAN ===\n{json.dumps(optimization_plan.model_dump(), ensure_ascii=False, indent=2)}\n"

        user_message = (
            f"Mode: single\n"
            f"Target roles: {all_job_titles}\n"
            f"Combined ATS keywords to prioritize: {', '.join(all_keywords[:40])}\n"
            f"{plan_desc}\n"
            f"=== ORIGINAL RESUME TEXT (ground truth — DO NOT INVENT facts/skills/companies) ===\n"
            f"{original_resume_text[:3000]}\n"
        )

        async with self.semaphore:
            raw = await self._invoke(user_message)
        raw["job_index"] = None

        try:
            optimized = OptimizedResume.model_validate(raw)
            if structured_resume:
                self._filter_hallucinated_skills(optimized, structured_resume, original_resume_text)
            return optimized
        except Exception as exc:
            logger.error("OptimizedResume single validation failed: %s", exc)
            raise AgentError(f"Optimization single schema validation failed: {exc}") from exc

    async def optimize_for_job(
        self,
        resume_analysis: ResumeAnalysis,
        job_analysis: JobAnalysis,
        original_resume_text: str,
        structured_resume: StructuredResume | None = None,
        optimization_plan: OptimizationPlan | None = None,
    ) -> OptimizedResume:
        plan_desc = ""
        if optimization_plan:
            plan_desc = f"\n=== OPTIMIZATION PLAN ===\n{json.dumps(optimization_plan.model_dump(), ensure_ascii=False, indent=2)}\n"

        user_message = (
            f"Mode: per_job\n"
            f"Target role: {job_analysis.title}\n"
            f"Job index: {job_analysis.job_index}\n"
            f"ATS keywords to incorporate: {', '.join(job_analysis.ats_keywords[:30])}\n"
            f"Required skills: {', '.join(job_analysis.required_skills[:20])}\n"
            f"{plan_desc}\n"
            f"=== ORIGINAL RESUME TEXT (ground truth — DO NOT INVENT facts/skills/companies) ===\n"
            f"{original_resume_text[:3000]}\n"
        )

        async with self.semaphore:
            raw = await self._invoke(user_message)
        raw["job_index"] = job_analysis.job_index

        try:
            optimized = OptimizedResume.model_validate(raw)
            if structured_resume:
                self._filter_hallucinated_skills(optimized, structured_resume, original_resume_text)
            return optimized
        except Exception as exc:
            logger.error("OptimizedResume job #%d validation failed: %s", job_analysis.job_index, exc)
            raise AgentError(f"Optimization for job #{job_analysis.job_index} validation failed: {exc}") from exc
