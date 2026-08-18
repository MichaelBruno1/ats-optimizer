"""Unit tests for LangGraph node functions."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.api.schemas import ExperienceExample, JobInput
from app.domain.job import SeniorityLevel, StructuredJob
from app.domain.resume import StructuredResume
from app.graph.nodes.cv_structurer_node import cv_structurer_node
from app.graph.nodes.experience_coach_node import experience_coach_node
from app.graph.nodes.finalize_node import finalize_node
from app.graph.nodes.job_analyzer_node import job_analyzer_node
from app.graph.nodes.optimizer_node import optimizer_node
from app.graph.nodes.pdf_node import generate_pdfs_node
from app.graph.state import GraphState


@pytest.mark.asyncio
async def test_cv_structurer_node_success(sample_resume_analysis):
    queue = asyncio.Queue()
    state: GraphState = {
        "resume_text": "Experienced Python Developer with 5 years experience.",
        "queue": queue,
    }

    mock_structured = StructuredResume(
        candidate_name="Michael Bruno",
        skills=["Python", "FastAPI"],
        professional_summary="Experienced Python Developer.",
    )

    with patch("app.graph.nodes.cv_structurer_node.ResumeCacheService.get", return_value=None), \
         patch("app.graph.nodes.cv_structurer_node.CVStructurerAgent") as MockAgent:
        mock_instance = MagicMock()
        mock_instance.structure_cv = AsyncMock(return_value=mock_structured)
        MockAgent.return_value = mock_instance

        result = await cv_structurer_node(state)

        assert "structured_resume" in result
        assert result["structured_resume"].candidate_name == "Michael Bruno"
        assert queue.qsize() == 2


@pytest.mark.asyncio
async def test_cv_structurer_node_cache_hit(sample_resume_analysis):
    queue = asyncio.Queue()
    state: GraphState = {
        "resume_text": "Cached candidate resume.",
        "queue": queue,
    }

    mock_structured = StructuredResume(candidate_name="Cached Candidate")

    with patch("app.graph.nodes.cv_structurer_node.ResumeCacheService.get", return_value=(mock_structured, sample_resume_analysis)):
        result = await cv_structurer_node(state)

        assert result["structured_resume"].candidate_name == "Cached Candidate"
        assert queue.qsize() == 1


@pytest.mark.asyncio
async def test_job_analyzer_node_success(sample_job_analysis):
    queue = asyncio.Queue()
    state: GraphState = {
        "jobs": [
            JobInput(title="Senior Dev", description="Python specialist role"),
        ],
        "queue": queue,
    }

    mock_structured_job = StructuredJob(
        job_index=0,
        title="Senior Dev",
        seniority_level=SeniorityLevel.SENIOR,
        required_skills=["Python"],
    )

    with patch("app.graph.nodes.job_analyzer_node.JobAnalystAgent") as MockAgent:
        mock_instance = MagicMock()
        mock_instance.analyze = AsyncMock(return_value=(mock_structured_job, sample_job_analysis))
        MockAgent.return_value = mock_instance

        result = await job_analyzer_node(state)

        assert "structured_jobs" in result
        assert len(result["structured_jobs"]) == 1
        assert result["structured_jobs"][0].title == "Senior Dev"


@pytest.mark.asyncio
async def test_experience_coach_node_success():
    queue = asyncio.Queue()
    mock_structured_resume = StructuredResume(candidate_name="Dev")
    mock_structured_job = StructuredJob(job_index=0, title="Dev")

    state: GraphState = {
        "structured_resume": mock_structured_resume,
        "structured_jobs": [mock_structured_job],
        "queue": queue,
    }

    mock_example = ExperienceExample(
        company="TechCorp",
        role="Dev",
        original_description="Code APIs",
        suggested_description="Designed scalable APIs with FastAPI",
    )

    with patch("app.graph.nodes.experience_coach_node.ExperienceCoachAgent") as MockAgent:
        MockAgent.return_value.generate_suggestions = AsyncMock(return_value=[mock_example])

        result = await experience_coach_node(state)

        assert "experience_examples" in result
        assert len(result["experience_examples"]) == 1
        assert result["experience_examples"][0]["company"] == "TechCorp"


@pytest.mark.asyncio
async def test_optimize_node_single_mode(sample_resume_analysis, sample_job_analysis, sample_optimized_resume):
    queue = asyncio.Queue()
    state: GraphState = {
        "output_mode": "single",
        "resume_analysis": sample_resume_analysis,
        "job_analyses": [sample_job_analysis],
        "resume_text": "Sample resume text",
        "queue": queue,
    }

    with patch("app.graph.nodes.optimizer_node.ResumeOptimizerAgent") as MockAgent:
        mock_instance = MagicMock()
        mock_instance.optimize_single = AsyncMock(return_value=sample_optimized_resume)
        MockAgent.return_value = mock_instance

        result = await optimizer_node(state)

        assert "optimized_resumes" in result
        assert len(result["optimized_resumes"]) == 1


@pytest.mark.asyncio
async def test_generate_pdfs_node_success(sample_resume_analysis, sample_optimized_resume, temp_dir, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "temp_dir", str(temp_dir))

    queue = asyncio.Queue()
    session_id = "test-pdf-session"
    (temp_dir / session_id).mkdir(parents=True, exist_ok=True)

    state: GraphState = {
        "session_id": session_id,
        "resume_analysis": sample_resume_analysis,
        "optimized_resumes": [sample_optimized_resume],
        "queue": queue,
    }

    with patch("app.graph.nodes.pdf_node.generate_pdf") as mock_generate_pdf:
        result = await generate_pdfs_node(state)

        assert "optimization_results" in result
        assert result["pdf_generated"] is True
        assert len(result["optimization_results"]) == 1
        mock_generate_pdf.assert_called_once()
