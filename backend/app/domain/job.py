"""Domain models for structured Job Description representation."""

from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, Field


class SeniorityLevel(str, Enum):
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    MANAGER = "manager"


class RequirementImportance(str, Enum):
    MANDATORY = "mandatory"
    DESIRABLE = "desirable"
    CONTEXTUAL = "contextual"
    RESPONSIBILITY = "responsibility"
    KEYWORD = "keyword"


class RequirementCategory(str, Enum):
    HARD_SKILL = "hard_skill"
    SOFT_SKILL = "soft_skill"
    TOOL = "tool"
    CERTIFICATION = "certification"
    EXPERIENCE = "experience"
    EDUCATION = "education"


class SkillRequirement(BaseModel):
    """Categorized and prioritized job requirement item."""

    name: str
    normalized_name: str = ""
    importance: RequirementImportance = RequirementImportance.MANDATORY
    category: RequirementCategory = RequirementCategory.HARD_SKILL


class StructuredJob(BaseModel):
    """Full semantically structured job description model."""

    job_index: int = 0
    title: str = ""
    company: Optional[str] = None
    seniority_level: SeniorityLevel = SeniorityLevel.MID
    required_skills: list[str] = Field(default_factory=list)
    desired_skills: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    ats_keywords: list[str] = Field(default_factory=list)
    certifications_required: list[str] = Field(default_factory=list)
    years_experience_required: Optional[int] = None
    key_responsibilities: list[str] = Field(default_factory=list)
    education_requirements: list[str] = Field(default_factory=list)
    industry: str = ""
    summary: str = ""
    raw_description: str = ""
