"""Job Analyst Agent.

Analyzes job descriptions and extracts structured metadata (StructuredJob & JobAnalysis).
"""

import json
import logging
from app.agents.base_agent import AgentError, BaseAgent
from app.api.schemas import JobAnalysis, JobInput
from app.domain.job import SeniorityLevel, StructuredJob

logger = logging.getLogger(__name__)


class JobAnalystAgent(BaseAgent):
    """Analyzes a job description and produces structured domain models."""

    system_prompt_file = "job_analysis.md"

    async def analyze(self, job: JobInput, job_index: int) -> tuple[StructuredJob, JobAnalysis]:
        company_line = f"Company: {job.company}" if job.company else "Company: Not specified"
        user_message = (
            f"Job Index: {job_index}\n"
            f"Job Title: {job.title}\n"
            f"{company_line}\n\n"
            f"Job Description:\n{job.description}"
        )

        logger.info("Analyzing job #%d: '%s'", job_index, job.title)
        raw = await self._invoke(user_message)
        raw["job_index"] = job_index
        if job.company and not raw.get("company"):
            raw["company"] = job.company

        try:
            job_analysis = JobAnalysis.model_validate(raw)
            
            # Map to domain StructuredJob
            seniority_str = raw.get("seniority_level", "mid").lower()
            seniority = SeniorityLevel.MID
            if seniority_str in (s.value for s in SeniorityLevel):
                seniority = SeniorityLevel(seniority_str)

            structured_job = StructuredJob(
                job_index=job_index,
                title=job.title,
                company=job.company,
                seniority_level=seniority,
                required_skills=job_analysis.required_skills,
                desired_skills=job_analysis.desired_skills,
                soft_skills=job_analysis.soft_skills,
                ats_keywords=job_analysis.ats_keywords,
                certifications_required=job_analysis.certifications_required,
                years_experience_required=job_analysis.years_experience_required,
                key_responsibilities=job_analysis.key_responsibilities,
                industry=job_analysis.industry,
                summary=job_analysis.summary,
                raw_description=job.description,
            )

            return structured_job, job_analysis

        except Exception as exc:
            logger.error(
                "Job analysis schema validation failed for job #%d: %s — raw: %s",
                job_index, exc, json.dumps(raw)[:400],
            )
            raise AgentError(f"Job analysis validation failed for job #{job_index}: {exc}") from exc
