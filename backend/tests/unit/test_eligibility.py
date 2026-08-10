"""Unit tests for Eligibility service."""

from app.domain.eligibility import EligibilityStatus
from app.domain.job import StructuredJob
from app.domain.resume import StructuredResume
from app.services.eligibility import EligibilityService
from app.services.matching_engine import MatchingEngine


def test_eligibility_pass() -> None:
    resume = StructuredResume(skills=["Python", "FastAPI"], total_years_experience=5)
    job = StructuredJob(required_skills=["Python"], years_experience_required=3)
    match_res = MatchingEngine.match(resume, job)

    res = EligibilityService.evaluate_eligibility(resume, job, match_res)
    assert res.status == EligibilityStatus.PASS
    assert len(res.disqualifying_factors) == 0


def test_eligibility_fail_experience() -> None:
    resume = StructuredResume(skills=["Python"], total_years_experience=1)
    job = StructuredJob(required_skills=["Python"], years_experience_required=8)
    match_res = MatchingEngine.match(resume, job)

    res = EligibilityService.evaluate_eligibility(resume, job, match_res)
    assert res.status == EligibilityStatus.FAIL
    assert any("insuficiente" in d.lower() or "inferior" in d.lower() for d in res.disqualifying_factors)
