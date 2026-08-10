"""CV Structurer Agent.

Parses plain text resumes into structured Pydantic domain models (StructuredResume).
Enforces zero hallucination and strict schema validation.
"""

import json
import logging
from app.agents.base_agent import AgentError, BaseAgent
from app.domain.resume import StructuredResume

logger = logging.getLogger(__name__)


class CVStructurerAgent(BaseAgent):
    """Transforms raw resume plain text into a structured StructuredResume domain model."""

    system_prompt_file = "resume_analysis.md"

    async def structure_cv(self, resume_text: str) -> StructuredResume:
        if not resume_text.strip():
            raise AgentError("Resume text is empty — cannot structure.")

        user_message = f"Please analyze and structure the following resume text:\n\n{resume_text}"
        logger.info("Structuring resume text (%d chars)...", len(resume_text))
        raw = await self._invoke(user_message)
        raw["raw_text"] = resume_text

        try:
            return StructuredResume.model_validate(raw)
        except Exception as exc:
            logger.error("StructuredResume validation failed: %s — raw: %s", exc, json.dumps(raw)[:400])
            raise AgentError(f"Resume structuring schema validation failed: {exc}") from exc
