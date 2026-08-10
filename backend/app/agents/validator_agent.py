"""ATS Validator Agent.

Semantic validation agent evaluating optimized resumes against anti-hallucination rules and quality standards.
"""

import json
import logging
from app.agents.base_agent import BaseAgent
from app.api.schemas import OptimizedResume
from app.domain.resume import StructuredResume
from app.domain.validation import ValidationResult
from app.services.ats_validator_service import ATSValidatorService

logger = logging.getLogger(__name__)


class ATSValidatorAgent(BaseAgent):
    """Hybrid validator combining programmatic checks with LLM verification."""

    system_prompt_file = "ats_validator.md"

    async def validate(
        self,
        optimized: OptimizedResume,
        structured_resume: StructuredResume,
        original_text: str,
    ) -> ValidationResult:
        # 1. Programmatic validation
        prog_result = ATSValidatorService.validate(optimized, structured_resume, original_text)

        # If programmatic check found hallucination errors, return immediately without wasting LLM tokens
        if not prog_result.approved:
            logger.warning("Programmatic validation failed with %d error(s).", len(prog_result.validation_errors))
            return prog_result

        # 2. LLM semantic check for quality and natural phrasing
        user_message = (
            f"=== OPTIMIZED RESUME ===\n"
            f"{json.dumps(optimized.model_dump(), ensure_ascii=False, indent=2)}\n\n"
            f"=== ORIGINAL RESUME TEXT ===\n"
            f"{original_text[:2000]}\n"
        )

        try:
            raw = await self._invoke(user_message)
            llm_result = ValidationResult.model_validate(raw)
            # Combine programmatic issues with LLM issues
            combined_errors = list(dict.fromkeys(prog_result.validation_errors + llm_result.validation_errors))
            combined_warnings = list(dict.fromkeys(prog_result.validation_warnings + llm_result.validation_warnings))
            approved = prog_result.approved and llm_result.approved and len(combined_errors) == 0

            return ValidationResult(
                approved=approved,
                validation_score=min(prog_result.validation_score, llm_result.validation_score),
                issues=prog_result.issues + llm_result.issues,
                validation_errors=combined_errors,
                validation_warnings=combined_warnings,
                hallucination_detected=prog_result.hallucination_detected or llm_result.hallucination_detected,
            )
        except Exception as exc:
            logger.warning("LLM validation call failed (%s). Defaulting to programmatic result.", exc)
            return prog_result
