"""Resume Analyst Agent.

Analyses a resume's plain-text content and produces a structured evaluation
including skills, experience, ATS score, and improvement suggestions.
"""

import json
import logging

from app.agents.base_agent import AgentError, BaseAgent
from app.api.schemas import ResumeAnalysis

logger = logging.getLogger(__name__)


class ResumeAnalystAgent(BaseAgent):
    """Extracts and evaluates all information from a plain-text resume.

    The agent is stateless; each call to ``analyze`` is independent.
    """

    system_prompt_file = "resume_analysis.txt"

    async def analyze(self, resume_text: str) -> ResumeAnalysis:
        """Run resume analysis on the extracted plain text.

        Args:
            resume_text: The full plain-text content of the candidate's resume.

        Returns:
            A validated ResumeAnalysis Pydantic model.

        Raises:
            AgentError: If the LLM call fails or the response cannot be validated.
        """
        if not resume_text.strip():
            raise AgentError("Resume text is empty — cannot analyze.")

        user_message = f"Please analyze the following resume:\n\n{resume_text}"

        logger.info(
            "Analyzing resume (%d characters)…", len(resume_text)
        )
        raw = await self._invoke(user_message)

        try:
            return ResumeAnalysis.model_validate(raw)
        except Exception as exc:
            logger.error(
                "ResumeAnalysis validation failed: %s — raw: %s",
                exc,
                json.dumps(raw)[:400],
            )
            raise AgentError(
                f"Resume analysis response failed schema validation: {exc}"
            ) from exc
