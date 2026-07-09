"""Pydantic v2 schemas for the ATS Optimizer API.

All request/response models are defined here to serve as the single
source of truth for the API contract.
"""

from typing import Optional, Any
from pydantic import BaseModel, Field, model_validator


class SafeBaseModel(BaseModel):
    """Pydantic model that automatically converts null/None values to empty defaults."""

    @model_validator(mode="before")
    @classmethod
    def clean_nulls(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for k, v in data.items():
                if v is None:
                    field_info = cls.model_fields.get(k)
                    if field_info:
                        annotation_str = str(field_info.annotation).lower()
                        if "list" in annotation_str:
                            data[k] = []
                        elif "int" in annotation_str or "float" in annotation_str:
                            data[k] = None
                        elif "dict" in annotation_str:
                            data[k] = {}
                        else:
                            data[k] = ""
        return data


# ─────────────────────────────────────────────────────────────────────────────
# Input schemas
# ─────────────────────────────────────────────────────────────────────────────


class JobInput(SafeBaseModel):
    """A single job description submitted for analysis."""

    title: str
    company: Optional[str] = None
    description: str = Field(..., max_length=5000)


# ─────────────────────────────────────────────────────────────────────────────
# Resume analysis schemas
# ─────────────────────────────────────────────────────────────────────────────


class ExperienceEntry(SafeBaseModel):
    """One position from the candidate's work history."""

    company: str = ""
    role: str = ""
    start_date: str = ""
    end_date: Optional[str] = None
    description: str = ""
    achievements: list[str] = []


class EducationEntry(SafeBaseModel):
    """A single educational qualification."""

    institution: str = ""
    degree: str = ""
    field: str = ""
    graduation_year: Optional[int] = None


class ResumeAnalysis(SafeBaseModel):
    """Structured output of the resume analyst agent."""

    candidate_name: Optional[str] = None
    contact_info: dict = {}
    professional_summary: Optional[str] = None
    skills: list[str] = []
    experience: list[ExperienceEntry] = []
    education: list[EducationEntry] = []
    certifications: list[str] = []
    languages: list[str] = []
    total_years_experience: Optional[int] = None
    formatting_issues: list[str] = []
    ats_readability_score: int = Field(0, ge=0, le=100)
    strengths: list[str] = []
    weaknesses: list[str] = []
    improvement_suggestions: list[str] = []


# ─────────────────────────────────────────────────────────────────────────────
# Job analysis schemas
# ─────────────────────────────────────────────────────────────────────────────


class JobAnalysis(SafeBaseModel):
    """Structured output of the job analyst agent for a single vacancy."""

    job_index: int
    title: str = ""
    company: Optional[str] = None
    seniority_level: str = "mid"
    required_skills: list[str] = []
    desired_skills: list[str] = []
    soft_skills: list[str] = []
    ats_keywords: list[str] = []
    certifications_required: list[str] = []
    years_experience_required: Optional[int] = None
    key_responsibilities: list[str] = []
    industry: str = ""
    summary: str = ""
    compatibility_score: int = Field(0, ge=0, le=100)
    gap_analysis: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Optimization schemas
# ─────────────────────────────────────────────────────────────────────────────


class OptimizedExperience(SafeBaseModel):
    """ATS-optimized version of an experience entry."""

    company: str = ""
    role: str = ""
    start_date: str = ""
    end_date: Optional[str] = None
    description: str = ""
    achievements: list[str] = []


class Section(SafeBaseModel):
    """An arbitrary additional resume section (e.g., Publications, Volunteer)."""

    title: str = ""
    content: str = ""


class ResumeContent(SafeBaseModel):
    """The full content of an optimized resume."""

    professional_summary: str = ""
    skills: list[str] = []
    experience: list[OptimizedExperience] = []
    education: list[EducationEntry] = []
    certifications: list[str] = []
    additional_sections: list[Section] = []


class OptimizedResume(SafeBaseModel):
    """Complete optimized resume document produced by the optimizer agent."""

    job_index: Optional[int] = None
    target_job_title: str = ""
    content: ResumeContent = Field(default_factory=ResumeContent)
    changes_made: list[str] = []
    keywords_added: list[str] = []
    estimated_ats_score: int = Field(0, ge=0, le=100)
    compatibility_score: int = Field(0, ge=0, le=100)


# ─────────────────────────────────────────────────────────────────────────────
# Response schemas
# ─────────────────────────────────────────────────────────────────────────────


class OptimizationResult(SafeBaseModel):
    """Summary of one optimization run, included in the analyze response."""

    job_index: Optional[int] = None
    download_url: str
    changes_summary: list[str] = []
    estimated_score_after: int = 0


class AnalyzeResponse(SafeBaseModel):
    """Top-level response for POST /api/v1/analyze."""

    session_id: str
    resume_analysis: ResumeAnalysis
    job_analyses: list[JobAnalysis] = []
    optimizations: list[OptimizationResult] = []


# ─────────────────────────────────────────────────────────────────────────────
# SSE event payloads (used internally, not enforced via FastAPI response model)
# ─────────────────────────────────────────────────────────────────────────────


class SSEProgress(SafeBaseModel):
    """Payload for the 'progress' SSE event."""

    step: str
    progress: int = Field(0, ge=0, le=100)
    message: str = ""


class SSEComplete(SafeBaseModel):
    """Payload for the 'complete' SSE event."""

    progress: int = 100
    message: str = ""
    session_id: str


class SSEError(SafeBaseModel):
    """Payload for the 'error' SSE event."""

    message: str = ""
