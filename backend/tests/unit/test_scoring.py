"""Unit tests for Scoring service (Deterministic Score Calculation)."""

from app.domain.job import StructuredJob
from app.domain.resume import StructuredResume
from app.services.matching_engine import MatchingEngine
from app.services.scoring import ScoringService


def test_scoring_deterministic_calculation() -> None:
    resume = StructuredResume(
        skills=["Python", "FastAPI", "PostgreSQL"],
        total_years_experience=6,
        raw_text="Desenvolvedor Python sênior com 6 anos de experiência em APIs e PostgreSQL.",
    )
    job = StructuredJob(
        title="Desenvolvedor Python Sênior",
        required_skills=["Python", "FastAPI", "PostgreSQL"],
        ats_keywords=["Python", "FastAPI", "PostgreSQL", "APIs"],
        years_experience_required=5,
    )

    match_res = MatchingEngine.match(resume, job)
    scoring = ScoringService()
    score_res = scoring.calculate_score(resume, job, match_res)

    assert 80 <= score_res.score <= 100
    assert score_res.components.keyword_coverage == 1.0
    assert score_res.components.required_skills == 1.0
    assert score_res.components.seniority == 1.0
    assert "Score ATS calculado via código" in score_res.explanation
