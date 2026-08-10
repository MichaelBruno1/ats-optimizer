"""Domain models for Deterministic ATS Scoring."""

from pydantic import BaseModel, Field


class ScoringWeights(BaseModel):
    """Configurable weights for the ATS scoring formula (must sum to 1.0)."""

    keyword_coverage: float = Field(0.25, ge=0.0, le=1.0)
    required_skills: float = Field(0.25, ge=0.0, le=1.0)
    experience_alignment: float = Field(0.20, ge=0.0, le=1.0)
    responsibilities: float = Field(0.15, ge=0.0, le=1.0)
    seniority: float = Field(0.10, ge=0.0, le=1.0)
    education: float = Field(0.05, ge=0.0, le=1.0)


class ScoreComponents(BaseModel):
    """Component breakdown of the calculated ATS score (values 0.0 to 1.0)."""

    keyword_coverage: float = 0.0
    required_skills: float = 0.0
    experience_alignment: float = 0.0
    responsibilities: float = 0.0
    seniority: float = 0.0
    education: float = 0.0


class ATSScoreResult(BaseModel):
    """Final calculated ATS score with component breakdown and delta."""

    score: int = Field(0, ge=0, le=100)
    components: ScoreComponents = Field(default_factory=ScoreComponents)
    weights: ScoringWeights = Field(default_factory=ScoringWeights)
    explanation: str = ""
