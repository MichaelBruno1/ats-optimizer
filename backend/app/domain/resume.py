"""Domain models for structured Resume representation."""

from typing import Optional
from pydantic import BaseModel, Field


class CandidateContact(BaseModel):
    """Contact information extracted from the candidate's resume."""

    email: str = ""
    phone: str = ""
    linkedin: str = ""
    location: str = ""


class ExperienceItem(BaseModel):
    """Work experience entry in candidate history."""

    company: str = ""
    role: str = ""
    start_date: str = ""
    end_date: Optional[str] = None
    description: str = ""
    achievements: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)


class EducationItem(BaseModel):
    """Academic qualification entry."""

    institution: str = ""
    degree: str = ""
    field: str = ""
    graduation_year: Optional[int] = None


class StructuredResume(BaseModel):
    """Full semantically structured CV model."""

    detected_language: str = "pt"
    candidate_name: Optional[str] = None
    contact_info: CandidateContact = Field(default_factory=CandidateContact)
    professional_summary: str = ""
    skills: list[str] = Field(default_factory=list)
    experience: list[ExperienceItem] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    total_years_experience: Optional[int] = None
    formatting_issues: list[str] = Field(default_factory=list)
    raw_text: str = ""


# Aliases for cross-module compatibility
ContactInfo = CandidateContact
ExperienceEntry = ExperienceItem
EducationEntry = EducationItem
