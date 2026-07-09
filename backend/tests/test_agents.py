"""Unit tests for the multi-LLM agents (ResumeAnalyst, JobAnalyst, ResumeOptimizer)."""

import pytest
import json
from unittest.mock import patch, MagicMock

from app.agents.base_agent import AgentError
from app.agents.resume_analyst import ResumeAnalystAgent
from app.agents.job_analyst import JobAnalystAgent
from app.agents.resume_optimizer import ResumeOptimizerAgent
from app.api.schemas import ResumeAnalysis, JobAnalysis, JobInput, OptimizedResume


# Helper to build mock acompletion response
def mock_llm_response(content: str) -> MagicMock:
    mock_resp = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = content
    mock_resp.choices = [mock_choice]
    return mock_resp


# ─────────────────────────────────────────────────────────────────────────────
# Resume Analyst Agent Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_resume_analyst_success(
    mock_acompletion: MagicMock,
    sample_resume_analysis: ResumeAnalysis
) -> None:
    """Test successful resume analysis with mock LLM response."""
    raw_response = sample_resume_analysis.model_dump_json()
    mock_acompletion.return_value = mock_llm_response(raw_response)

    agent = ResumeAnalystAgent()
    result = await agent.analyze("Some candidate resume content")

    assert isinstance(result, ResumeAnalysis)
    assert result.candidate_name == sample_resume_analysis.candidate_name
    assert result.ats_readability_score == sample_resume_analysis.ats_readability_score
    mock_acompletion.assert_called_once()


@pytest.mark.asyncio
async def test_resume_analyst_empty_input() -> None:
    """Test that resume analyst raises AgentError for empty input."""
    agent = ResumeAnalystAgent()
    with pytest.raises(AgentError, match="Resume text is empty"):
        await agent.analyze("   ")


@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_resume_analyst_llm_failure(mock_acompletion: MagicMock) -> None:
    """Test that agent propagates AgentError on LLM call exception."""
    mock_acompletion.side_effect = Exception("API connection timeout")
    
    agent = ResumeAnalystAgent()
    with pytest.raises(AgentError, match="LLM invocation failed"):
        await agent.analyze("Valid resume text")


@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_resume_analyst_invalid_json(mock_acompletion: MagicMock) -> None:
    """Test that agent raises AgentError when LLM returns invalid JSON."""
    mock_acompletion.return_value = mock_llm_response("Not a JSON response")

    agent = ResumeAnalystAgent()
    with pytest.raises(AgentError, match="non-JSON content"):
        await agent.analyze("Valid resume text")


# ─────────────────────────────────────────────────────────────────────────────
# Job Analyst Agent Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_job_analyst_success(
    mock_acompletion: MagicMock,
    sample_job_analysis: JobAnalysis
) -> None:
    """Test successful job description analysis with mock LLM response."""
    raw_response = sample_job_analysis.model_dump_json()
    mock_acompletion.return_value = mock_llm_response(raw_response)

    job_input = JobInput(
        title="Desenvolvedor Backend Sênior",
        company="Tech Solutions",
        description="Requisitos: Python, FastAPI e PostgreSQL"
    )

    agent = JobAnalystAgent()
    result = await agent.analyze(job_input, job_index=0)

    assert isinstance(result, JobAnalysis)
    assert result.job_index == 0
    assert result.title == "Desenvolvedor Backend Sênior"
    assert result.compatibility_score == 90
    mock_acompletion.assert_called_once()


# ─────────────────────────────────────────────────────────────────────────────
# Resume Optimizer Agent Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_resume_optimizer_single_mode(
    mock_acompletion: MagicMock,
    sample_resume_analysis: ResumeAnalysis,
    sample_job_analysis: JobAnalysis,
    sample_optimized_resume: OptimizedResume
) -> None:
    """Test resume optimization in 'single' mode."""
    # Ensure job_index is set to None in expected single mode output
    expected_resume = sample_optimized_resume.model_copy()
    expected_resume.job_index = None
    
    raw_response = expected_resume.model_dump_json()
    mock_acompletion.return_value = mock_llm_response(raw_response)

    agent = ResumeOptimizerAgent()
    result = await agent.optimize_single(
        resume_analysis=sample_resume_analysis,
        job_analyses=[sample_job_analysis],
        original_resume_text="Original raw text"
    )

    assert isinstance(result, OptimizedResume)
    assert result.job_index is None
    assert result.estimated_ats_score == 92
    assert "FastAPI" in result.keywords_added
    mock_acompletion.assert_called_once()


@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_resume_optimizer_per_job_mode(
    mock_acompletion: MagicMock,
    sample_resume_analysis: ResumeAnalysis,
    sample_job_analysis: JobAnalysis,
    sample_optimized_resume: OptimizedResume
) -> None:
    """Test resume optimization in 'per_job' mode."""
    raw_response = sample_optimized_resume.model_dump_json()
    mock_acompletion.return_value = mock_llm_response(raw_response)

    agent = ResumeOptimizerAgent()
    result = await agent.optimize_for_job(
        resume_analysis=sample_resume_analysis,
        job_analysis=sample_job_analysis,
        original_resume_text="Original raw text"
    )

    assert isinstance(result, OptimizedResume)
    assert result.job_index == 0
    assert result.target_job_title == "Desenvolvedor Backend Sênior"
    mock_acompletion.assert_called_once()


@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_job_analyst_truncated_json_repair(
    mock_acompletion: MagicMock,
    sample_job_analysis: JobAnalysis
) -> None:
    """Test that agent successfully repairs and validates truncated JSON."""
    raw_truncated = (
        '{\n  "job_index": 0,\n  "title": "Pessoa Desenvolvedora Back-end Java Sênior",\n'
        '  "company": "FCamara",\n  "seniority_level": "senior",\n  "required_skills": [\n'
        '    "Java",\n    "Desenvolvimento de software"\n  ],\n  "compatibility_score": 85,\n'
        '  "gap_analysis": "Embora o JD seja detalhado sobre metodologias ('
    )
    mock_acompletion.return_value = mock_llm_response(raw_truncated)

    job_input = JobInput(
        title="Desenvolvedor Java",
        company="FCamara",
        description="Java Developer description..."
    )

    agent = JobAnalystAgent()
    result = await agent.analyze(job_input, job_index=0)

    # It should successfully repair the JSON and validate the model
    assert isinstance(result, JobAnalysis)
    assert result.job_index == 0
    assert result.title == "Pessoa Desenvolvedora Back-end Java Sênior"
    assert result.compatibility_score == 85
    # The truncated field "gap_analysis" should be partially recovered up to the truncation point
    assert "Embora o JD seja detalhado" in result.gap_analysis

