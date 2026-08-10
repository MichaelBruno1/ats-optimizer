"""Domain models for Hard Qualification Eligibility (Pass/Fail)."""

from enum import Enum
from pydantic import BaseModel, Field


class EligibilityStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class EligibilityResult(BaseModel):
    """Evaluates whether candidate meets strict mandatory disqualification criteria."""

    status: EligibilityStatus = EligibilityStatus.UNKNOWN
    passed_criteria: list[str] = Field(default_factory=list)
    disqualifying_factors: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
