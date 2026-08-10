"""Domain models for Optimization Planning."""

from enum import Enum
from pydantic import BaseModel, Field


class PlanAction(str, Enum):
    REWRITE_SUMMARY = "rewrite_summary"
    REWRITE_BULLET = "rewrite_bullet"
    REORDER_SKILLS = "reorder_skills"
    HIGHLIGHT_KEYWORDS = "highlight_keywords"
    ADD_CONTEXT = "add_context"


class PlanItem(BaseModel):
    """Specific action recommendation in the optimization plan."""

    section: str  # summary, experience, skills, education
    action: PlanAction
    target_item: str = ""
    reason: str = ""
    keywords_to_incorporate: list[str] = Field(default_factory=list)


class OptimizationPlan(BaseModel):
    """Structured plan outlining changes before resume modification."""

    job_index: int = 0
    target_job_title: str = ""
    items: list[PlanItem] = Field(default_factory=list)
    summary_strategy: str = ""
    skills_reorder_strategy: str = ""
