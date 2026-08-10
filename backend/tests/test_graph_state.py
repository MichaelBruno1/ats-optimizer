"""Unit tests for GraphState definition."""

import pytest
from asyncio import Queue
from app.graph.state import GraphState
from app.api.schemas import (
    JobAnalysis,
    JobInput,
    OptimizationResult,
    OptimizedResume,
    ResumeAnalysis,
)


def test_graph_state_minimal_creation():
    """Verify state initialization with minimal required keys."""
    state: GraphState = {
        "session_id": "test-session-123",
        "resume_text": "Sample resume text content",
        "jobs": [JobInput(title="Software Engineer", description="Python dev role")],
        "output_mode": "single",
        "queue": Queue(),
    }
    assert state["session_id"] == "test-session-123"
    assert len(state["jobs"]) == 1
    assert state["output_mode"] == "single"
    assert "resume_analysis" not in state


def test_graph_state_full_creation(sample_resume_analysis, sample_job_analysis, sample_optimized_resume):
    """Verify state initialization with all optional intermediate results."""
    state: GraphState = {
        "session_id": "test-session-456",
        "resume_text": "Sample resume text",
        "jobs": [JobInput(title="Python Developer", description="Backend engineer")],
        "output_mode": "per_job",
        "queue": Queue(),
        "resume_analysis": sample_resume_analysis,
        "job_analyses": [sample_job_analysis],
        "optimized_resumes": [sample_optimized_resume],
        "optimization_results": [
            OptimizationResult(
                job_index=0,
                download_url="/api/v1/download/test-session-456/0",
                changes_summary=["Updated summary"],
                estimated_score_after=85,
            )
        ],
        "pdf_generated": True,
        "error": None,
    }
    assert state["resume_analysis"].ats_readability_score == 85
    assert len(state["job_analyses"]) == 1
    assert state["pdf_generated"] is True
    assert state["error"] is None


def test_graph_state_compatible_with_pydantic_models(sample_resume_analysis, sample_job_analysis):
    """Verify GraphState fields correctly store Pydantic model types."""
    state: GraphState = {
        "resume_analysis": sample_resume_analysis,
        "job_analyses": [sample_job_analysis],
    }
    assert isinstance(state["resume_analysis"], ResumeAnalysis)
    assert isinstance(state["job_analyses"][0], JobAnalysis)
