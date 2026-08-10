"""Unit tests for conditional edge routing functions in the ATS optimization graph."""

from app.graph.edges import should_generate, should_optimize
from app.graph.state import GraphState


def test_should_optimize_both_ok(sample_resume_analysis, sample_job_analysis):
    state: GraphState = {
        "resume_analysis": sample_resume_analysis,
        "job_analyses": [sample_job_analysis],
    }
    assert should_optimize(state) == "optimize"


def test_should_optimize_missing_resume(sample_job_analysis):
    state: GraphState = {
        "resume_analysis": None,
        "job_analyses": [sample_job_analysis],
    }
    assert should_optimize(state) == "end"


def test_should_optimize_missing_jobs(sample_resume_analysis):
    state: GraphState = {
        "resume_analysis": sample_resume_analysis,
        "job_analyses": None,
    }
    assert should_optimize(state) == "end"


def test_should_optimize_with_error(sample_resume_analysis, sample_job_analysis):
    state: GraphState = {
        "resume_analysis": sample_resume_analysis,
        "job_analyses": [sample_job_analysis],
        "error": "LLM failed during resume analysis",
    }
    assert should_optimize(state) == "end"


def test_should_generate_ok(sample_optimized_resume):
    state: GraphState = {
        "optimized_resumes": [sample_optimized_resume],
    }
    assert should_generate(state) == "generate_pdfs"


def test_should_generate_no_resumes():
    state: GraphState = {
        "optimized_resumes": None,
    }
    assert should_generate(state) == "end"


def test_should_generate_with_error(sample_optimized_resume):
    state: GraphState = {
        "optimized_resumes": [sample_optimized_resume],
        "error": "Optimization schema validation failed",
    }
    assert should_generate(state) == "end"
