"""Domain models for ATS & Anti-Hallucination Validation."""

from enum import Enum
from pydantic import BaseModel, Field


class IssueSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class IssueCategory(str, Enum):
    ANTI_HALLUCINATION = "anti_hallucination"
    ATS_FORMAT = "ats_format"
    KEYWORD_STUFFING = "keyword_stuffing"
    CONTENT_QUALITY = "content_quality"


class ValidationIssue(BaseModel):
    """Detailed validation issue identified by the ATS Validator."""

    severity: IssueSeverity
    category: IssueCategory
    message: str
    field_affected: str = ""


class ValidationResult(BaseModel):
    """Consolidated result of resume validation after optimization."""

    approved: bool = False
    validation_score: int = Field(0, ge=0, le=100)
    issues: list[ValidationIssue] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)
    validation_warnings: list[str] = Field(default_factory=list)
    hallucination_detected: bool = False
