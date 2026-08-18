"""Unit tests for ResumeCacheService."""

import time
from pathlib import Path
import pytest

from app.api.schemas import ResumeAnalysis
from app.config import settings
from app.domain.resume import StructuredResume
from app.services.resume_cache import ResumeCacheService


def test_resume_cache_hit_and_miss(temp_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "temp_dir", str(temp_dir))

    resume_text = "Sample candidate resume text for caching."
    structured = StructuredResume(
        candidate_name="Michael Bruno",
        skills=["Python", "FastAPI"],
        professional_summary="Desenvolvedor Python sênior.",
        raw_text=resume_text,
    )
    analysis = ResumeAnalysis(
        candidate_name="Michael Bruno",
        skills=["Python", "FastAPI"],
        ats_readability_score=90,
    )

    # Miss before setting
    assert ResumeCacheService.get(resume_text) is None

    # Set cache
    ResumeCacheService.set(resume_text, structured, analysis)

    # Hit after setting
    cached = ResumeCacheService.get(resume_text)
    assert cached is not None
    cached_struct, cached_analysis = cached
    assert cached_struct.candidate_name == "Michael Bruno"
    assert cached_analysis.ats_readability_score == 90


def test_resume_cache_ttl_expiration(temp_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "temp_dir", str(temp_dir))
    monkeypatch.setattr(settings, "cache_ttl_hours", 0)  # Immediate expiration

    resume_text = "Expiring candidate resume."
    structured = StructuredResume(candidate_name="Expiring User")
    analysis = ResumeAnalysis(candidate_name="Expiring User")

    ResumeCacheService.set(resume_text, structured, analysis)
    
    # Wait a fraction of a second to exceed 0 TTL
    time.sleep(0.05)
    assert ResumeCacheService.get(resume_text) is None
