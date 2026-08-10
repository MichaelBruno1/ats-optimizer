"""Unit tests for Matching Engine service."""

from app.domain.job import StructuredJob
from app.domain.matching import MatchStatus
from app.domain.resume import ExperienceItem, StructuredResume
from app.services.matching_engine import MatchingEngine, evaluate_skill_match


def test_match_case1_exact() -> None:
    resume = StructuredResume(skills=["Python", "FastAPI"])
    result = evaluate_skill_match("Python", resume)
    assert result.status == MatchStatus.MATCH
    assert result.confidence == 1.0


def test_match_case2_alias() -> None:
    resume = StructuredResume(skills=["Amazon Web Services"])
    result = evaluate_skill_match("AWS", resume)
    assert result.status == MatchStatus.MATCH
    assert result.confidence == 1.0
    assert result.matched_candidate_skill == "Amazon Web Services"


def test_match_case3_not_found() -> None:
    resume = StructuredResume(skills=["Python"])
    result = evaluate_skill_match("Kubernetes", resume)
    assert result.status == MatchStatus.NOT_FOUND
    assert result.confidence == 0.0


def test_match_case4_equivalent_partial() -> None:
    resume = StructuredResume(skills=["Flask"])
    result = evaluate_skill_match("FastAPI", resume)
    assert result.status == MatchStatus.PARTIAL
    assert result.matched_candidate_skill == "Flask"


def test_matching_engine_full_job() -> None:
    resume = StructuredResume(
        skills=["Python", "PostgreSQL"],
        raw_text="Desenvolvimento de APIs REST com Python e PostgreSQL.",
    )
    job = StructuredJob(
        title="Python Developer",
        required_skills=["Python", "PostgreSQL", "Docker"],
        ats_keywords=["Python", "PostgreSQL", "APIs"],
    )
    res = MatchingEngine.match(resume, job)

    assert "Python" in res.matched_skills
    assert "PostgreSQL" in res.matched_skills
    assert "Docker" in res.missing_skills
    assert res.keyword_coverage_ratio > 0.5
