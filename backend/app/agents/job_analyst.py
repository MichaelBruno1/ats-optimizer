"""Job Analyst Agent.

Analyzes job descriptions and extracts structured ATS-relevant metadata
including required/desired skills, keywords, responsibilities, and more.
"""

import json
import logging

from app.agents.base_agent import AgentError, BaseAgent
from app.api.schemas import JobAnalysis, JobInput

logger = logging.getLogger(__name__)


class JobAnalystAgent(BaseAgent):
    """Analyzes a single job description and returns a structured JobAnalysis.

    The agent is stateless; each call to ``analyze`` is independent.
    """

    system_prompt_file = "job_analysis.txt"

    async def analyze(self, job: JobInput, job_index: int) -> JobAnalysis:
        """Run job description analysis for a single vacancy.

        Args:
            job: The job input containing title, optional company, and description.
            job_index: Zero-based index of this job in the submitted list.

        Returns:
            A validated JobAnalysis Pydantic model.

        Raises:
            AgentError: If the LLM call fails or the response cannot be parsed.
        """
        company_line = f"Company: {job.company}" if job.company else "Company: Not specified"
        user_message = (
            f"Job Index: {job_index}\n"
            f"Job Title: {job.title}\n"
            f"{company_line}\n\n"
            f"Job Description:\n{job.description}"
        )

        logger.info("Analyzing job #%d: '%s'", job_index, job.title)
        raw = await self._invoke(user_message)

        # Ensure job_index is set correctly regardless of what the LLM returned
        raw["job_index"] = job_index
        if job.company and not raw.get("company"):
            raw["company"] = job.company

        try:
            return JobAnalysis.model_validate(raw)
        except Exception as exc:
            logger.error(
                "JobAnalysis validation failed for job #%d: %s — raw: %s",
                job_index,
                exc,
                json.dumps(raw)[:400],
            )
            raise AgentError(
                f"Job analysis response failed schema validation for job #{job_index}: {exc}"
            ) from exc
