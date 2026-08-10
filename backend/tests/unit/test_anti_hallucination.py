"""Unit tests for Anti-Hallucination and ATS Validator."""

from app.api.schemas import OptimizedResume, ResumeContent
from app.domain.resume import StructuredResume
from app.services.ats_validator_service import ATSValidatorService


def test_anti_hallucination_detects_unsupported_skill() -> None:
    original_resume = StructuredResume(skills=["Python", "FastAPI"])
    original_text = "Desenvolvedor Python focado em APIs com FastAPI."

    # Optimized resume attempts to introduce AWS which candidate does not have
    optimized = OptimizedResume(
        content=ResumeContent(
            skills=["Python", "FastAPI", "AWS Cloud Architect"],
            professional_summary="Desenvolvedor Python e FastAPI.",
        )
    )

    res = ATSValidatorService.validate(optimized, original_resume, original_text)

    assert res.approved is False
    assert res.hallucination_detected is True
    assert any("AWS" in err for err in res.validation_errors)
