"""Typed central state for the ATS optimization LangGraph pipeline."""

from typing import Any, Optional
from typing_extensions import TypedDict

from app.api.schemas import (
    JobAnalysis,
    JobInput,
    OptimizationResult,
    OptimizedResume,
    ResumeAnalysis,
)
from app.domain.eligibility import EligibilityResult
from app.domain.job import StructuredJob
from app.domain.matching import JobMatchResult
from app.domain.optimization import OptimizationPlan
from app.domain.resume import StructuredResume
from app.domain.scoring import ATSScoreResult
from app.domain.validation import ValidationResult


class GraphState(TypedDict, total=False):
    """Central state flowing through the LangGraph optimization multi-agent pipeline."""

    # ── Inputs ────────────────────────────────────────────────────────────
    session_id: str
    resume_text: str
    jobs: list[JobInput]
    output_mode: str  # "single" | "per_job"

    # ── SSE progress queue ────────────────────────────────────────────────
    queue: Any  # asyncio.Queue

    # ── Structured Domain Models ──────────────────────────────────────────
    structured_resume: Optional[StructuredResume]
    structured_jobs: Optional[list[StructuredJob]]

    # ── Matching, Scoring & Eligibility ──────────────────────────────────
    match_results: Optional[list[JobMatchResult]]
    ats_scores_before: Optional[list[ATSScoreResult]]
    eligibility_results: Optional[list[EligibilityResult]]

    # ── Strengths & Gaps ──────────────────────────────────────────────────
    strengths: Optional[list[str]]
    weaknesses: Optional[list[str]]
    gap_analysis_summary: Optional[str]

    # ── Legacy/API Compatible Models ──────────────────────────────────────
    resume_analysis: Optional[ResumeAnalysis]
    job_analyses: Optional[list[JobAnalysis]]

    # ── Optimization & Validation Loop ────────────────────────────────────
    optimization_plans: Optional[list[OptimizationPlan]]
    optimized_resumes: Optional[list[OptimizedResume]]
    ats_scores_after: Optional[list[ATSScoreResult]]
    validation_results: Optional[list[ValidationResult]]

    optimization_iteration: int
    score_history: list[int]
    approved: bool

    # ── Educational Experience Coach Examples ─────────────────────────────
    experience_examples: Optional[list[dict]]

    # ── Output ────────────────────────────────────────────────────────────
    optimization_results: Optional[list[OptimizationResult]]
    pdf_generated: bool

    # ── Error tracking ────────────────────────────────────────────────────
    error: Optional[str]
