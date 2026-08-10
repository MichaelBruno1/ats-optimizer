"""Domain models for Skill Matching and Evidence Tracking."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class MatchStatus(str, Enum):
    MATCH = "MATCH"
    PARTIAL = "PARTIAL"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    UNKNOWN = "UNKNOWN"


class SkillMatch(BaseModel):
    """Detailed evaluation of a single required skill against candidate profile."""

    required_skill: str
    normalized_skill: str
    status: MatchStatus = MatchStatus.UNKNOWN
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    matched_candidate_skill: Optional[str] = None
    evidence: Optional[str] = None
    reason: Optional[str] = None


class JobMatchResult(BaseModel):
    """Consolidated matching evaluation for a candidate vs single job."""

    job_index: int = 0
    job_title: str = ""
    skill_matches: list[SkillMatch] = Field(default_factory=list)
    matched_skills: list[str] = Field(default_factory=list)
    partial_matches: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    matched_keywords: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    keyword_coverage_ratio: float = 0.0
    seniority_aligned: bool = True
