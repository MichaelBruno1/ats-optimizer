"""Unit and integration tests for independent subgraphs."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.api.schemas import JobInput
from app.domain.job import SeniorityLevel, StructuredJob
from app.domain.resume import StructuredResume
from app.graph.pipeline import (
    job_analysis_subgraph,
    optimization_subgraph,
    resume_analysis_subgraph,
)
from app.graph.state import GraphState


@pytest.mark.asyncio
async def test_resume_analysis_subgraph_success(sample_resume_analysis):
    queue = asyncio.Queue()
    state: GraphState = {
        "resume_text": "Experienced Python Software Developer",
        "queue": queue,
    }

    mock_structured = StructuredResume(
        candidate_name="Michael Bruno",
        skills=["Python"],
        professional_summary="Experienced Python Developer.",
    )

    with patch("app.graph.nodes.cv_structurer_node.CVStructurerAgent") as MockAgent:
        MockAgent.return_value.structure_cv = AsyncMock(return_value=mock_structured)

        result = await resume_analysis_subgraph.ainvoke(state)

        assert "structured_resume" in result
        assert result["structured_resume"].candidate_name == "Michael Bruno"


@pytest.mark.asyncio
async def test_job_analysis_subgraph_success(sample_job_analysis):
    queue = asyncio.Queue()
    state: GraphState = {
        "jobs": [JobInput(title="Backend Dev", description="Python and FastAPI job")],
        "queue": queue,
    }

    mock_structured_job = StructuredJob(
        job_index=0,
        title="Backend Dev",
        seniority_level=SeniorityLevel.MID,
    )

    with patch("app.graph.nodes.job_analyzer_node.JobAnalystAgent") as MockAgent:
        MockAgent.return_value.analyze = AsyncMock(return_value=(mock_structured_job, sample_job_analysis))

        result = await job_analysis_subgraph.ainvoke(state)

        assert "structured_jobs" in result
        assert len(result["structured_jobs"]) == 1


@pytest.mark.asyncio
async def test_optimization_subgraph_success(
    sample_resume_analysis,
    sample_job_analysis,
    sample_optimized_resume,
    temp_dir,
    monkeypatch,
):
    from app.config import settings
    monkeypatch.setattr(settings, "temp_dir", str(temp_dir))

    session_id = "test-subgraph-opt"
    (temp_dir / session_id).mkdir(parents=True, exist_ok=True)
    queue = asyncio.Queue()

    state: GraphState = {
        "session_id": session_id,
        "resume_text": "Sample resume text",
        "resume_analysis": sample_resume_analysis,
        "job_analyses": [sample_job_analysis],
        "output_mode": "single",
        "queue": queue,
    }

    with patch("app.graph.nodes.optimizer_node.ResumeOptimizerAgent") as MockOptimizer, \
         patch("app.graph.nodes.pdf_node.generate_pdf") as mock_generate_pdf:

        MockOptimizer.return_value.optimize_single = AsyncMock(return_value=sample_optimized_resume)

        result = await optimization_subgraph.ainvoke(state)

        assert len(result["optimized_resumes"]) == 1
        assert result["pdf_generated"] is True
        mock_generate_pdf.assert_called_once()
