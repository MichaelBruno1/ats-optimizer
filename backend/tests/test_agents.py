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


@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_base_agent_self_healing_retry(
    mock_acompletion: MagicMock,
    sample_job_analysis: JobAnalysis
) -> None:
    """Test that base agent automatically retries with lower max_tokens upon failure."""
    # First call raises BadRequestError, second call succeeds
    mock_acompletion.side_effect = [
        Exception("Context size has been exceeded (400)"),
        mock_llm_response(sample_job_analysis.model_dump_json())
    ]

    job_input = JobInput(
        title="Python Developer",
        company="Tech Solutions",
        description="FastAPI role"
    )

    agent = JobAnalystAgent(max_tokens=2000)
    result = await agent.analyze(job_input, job_index=0)

    # It should successfully recover and return JobAnalysis
    assert isinstance(result, JobAnalysis)
    assert result.job_index == 0
    assert result.title == "Desenvolvedor Backend Sênior"
    
    # Verify that acompletion was called twice
    assert mock_acompletion.call_count == 2
    # Verify that the second call was made with max_tokens reduced (2000 * 0.65 = 1300)
    args_call1, kwargs_call1 = mock_acompletion.call_args_list[0]
    args_call2, kwargs_call2 = mock_acompletion.call_args_list[1]
    assert kwargs_call1["max_tokens"] == 2000
    assert kwargs_call2["max_tokens"] == 1300


@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_resume_optimizer_hallucination_filter(
    mock_acompletion: MagicMock,
    sample_resume_analysis: ResumeAnalysis,
    sample_job_analysis: JobAnalysis,
    sample_optimized_resume: OptimizedResume
) -> None:
    """Test that OptimizedResume agent filters out hallucinated skills programmatically."""
    # Modify original resume analysis to only have "Python" and "FastAPI"
    sample_resume_analysis.skills = ["Python", "FastAPI"]
    
    # Original raw text contains "FastAPI" and "SQL" (SQL is in raw text but not in parsed skills list)
    original_text = "FastAPI developer with SQL experience."
    
    # Mock optimized resume output with: "Python" (valid), "SQL" (valid from raw text), and "COBOL" (hallucinated)
    optimized_dump = sample_optimized_resume.model_copy(deep=True)
    optimized_dump.content.skills = ["Python", "SQL", "COBOL"]
    
    mock_acompletion.return_value = mock_llm_response(optimized_dump.model_dump_json())

    agent = ResumeOptimizerAgent()
    result = await agent.optimize_for_job(
        resume_analysis=sample_resume_analysis,
        job_analysis=sample_job_analysis,
        original_resume_text=original_text
    )

    # It should preserve Python and SQL, but prune COBOL
    assert "Python" in result.content.skills
    assert "SQL" in result.content.skills
    assert "COBOL" not in result.content.skills
    assert len(result.content.skills) == 2


@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_base_agent_empty_response_retry(mock_acompletion: MagicMock) -> None:
    """Test that empty response content triggers the retry loop."""
    # First response is empty, second is a valid JSON for ResumeAnalysis
    first_res = mock_llm_response("")
    second_res = mock_llm_response(
        json.dumps({
            "candidate_name": "Test Candidate",
            "ats_readability_score": 85,
            "skills": ["Python"]
        })
    )
    mock_acompletion.side_effect = [first_res, second_res]

    agent = ResumeAnalystAgent(max_tokens=2000)
    result = await agent.analyze("Raw resume text")

    # It should successfully retry on empty response and parse the second one
    assert isinstance(result, ResumeAnalysis)
    assert result.candidate_name == "Test Candidate"
    assert mock_acompletion.call_count == 2
    # Verify the second call reduced max_tokens
    args_call1, kwargs_call1 = mock_acompletion.call_args_list[0]
    args_call2, kwargs_call2 = mock_acompletion.call_args_list[1]
    assert kwargs_call1["max_tokens"] == 2000
    assert kwargs_call2["max_tokens"] == 1300


@pytest.mark.asyncio
@patch("litellm.acompletion")
async def test_base_agent_dynamic_prompt_truncation_on_retry(mock_acompletion: MagicMock) -> None:
    """Test that dynamic prompt truncation is applied to long messages on retry."""
    # First response is empty, second is valid
    first_res = mock_llm_response("")
    second_res = mock_llm_response(
        json.dumps({
            "candidate_name": "Test Candidate",
            "ats_readability_score": 85,
            "skills": ["Python"]
        })
    )
    mock_acompletion.side_effect = [first_res, second_res]

    agent = ResumeAnalystAgent(max_tokens=2000)
    # 4000 characters (exceeds 3000 chars limit for retry truncation)
    long_raw_resume = "X" * 4000
    result = await agent.analyze(long_raw_resume)

    assert isinstance(result, ResumeAnalysis)
    assert mock_acompletion.call_count == 2

    # Verify the first call contains the original 4000 characters of the resume
    args_call1, kwargs_call1 = mock_acompletion.call_args_list[0]
    first_content = kwargs_call1["messages"][1]["content"]
    assert "X" * 4000 in first_content

    # Verify the second call prompt was truncated
    args_call2, kwargs_call2 = mock_acompletion.call_args_list[1]
    truncated_content = kwargs_call2["messages"][1]["content"]
    assert "X" * 4000 not in truncated_content
    assert "truncado" in truncated_content

