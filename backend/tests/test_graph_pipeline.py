"""Integration tests for the full compiled LangGraph pipeline."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.api.schemas import JobInput
from app.domain.job import SeniorityLevel, StructuredJob
from app.domain.resume import StructuredResume
from app.graph.pipeline import optimization_graph, run_graph_pipeline
from app.graph.state import GraphState


@pytest.mark.asyncio
async def test_full_graph_success(
    sample_resume_analysis,
    sample_job_analysis,
    sample_optimized_resume,
    temp_dir,
    monkeypatch,
):
    from app.config import settings
    monkeypatch.setattr(settings, "temp_dir", str(temp_dir))

    session_id = "test-pipeline-full"
    (temp_dir / session_id).mkdir(parents=True, exist_ok=True)
    queue = asyncio.Queue()

    initial_state: GraphState = {
        "session_id": session_id,
        "resume_text": "Sample candidate resume text with Python and FastAPI experience.",
        "jobs": [JobInput(title="Python Engineer", description="Backend developer role requiring Python and FastAPI.")],
        "output_mode": "single",
        "queue": queue,
        "optimization_iteration": 0,
        "approved": False,
    }

    mock_structured_resume = StructuredResume(
        candidate_name="Michael Bruno",
        skills=["Python", "FastAPI"],
        professional_summary="Desenvolvedor Python sênior.",
        raw_text="Sample candidate resume text with Python and FastAPI experience.",
    )
    mock_structured_job = StructuredJob(
        job_index=0,
        title="Python Engineer",
        required_skills=["Python", "FastAPI"],
        ats_keywords=["Python", "FastAPI"],
    )

    with patch("app.graph.nodes.cv_structurer_node.CVStructurerAgent") as MockCVStructurer, \
         patch("app.graph.nodes.job_analyzer_node.JobAnalystAgent") as MockJobAnalyst, \
         patch("app.graph.nodes.optimizer_node.ResumeOptimizerAgent") as MockOptimizer, \
         patch("app.graph.nodes.validator_node.ATSValidatorAgent") as MockValidator, \
         patch("app.graph.nodes.pdf_node.generate_pdf") as mock_generate_pdf:

        MockCVStructurer.return_value.structure_cv = AsyncMock(return_value=mock_structured_resume)
        MockJobAnalyst.return_value.analyze = AsyncMock(return_value=(mock_structured_job, sample_job_analysis))
        MockOptimizer.return_value.optimize_single = AsyncMock(return_value=sample_optimized_resume)
        
        mock_val_result = MagicMock()
        mock_val_result.approved = True
        mock_val_result.validation_score = 95
        mock_val_result.validation_errors = []
        mock_val_result.validation_warnings = []
        mock_val_result.issues = []
        mock_val_result.hallucination_detected = False
        MockValidator.return_value.validate = AsyncMock(return_value=mock_val_result)

        final_state = await optimization_graph.ainvoke(initial_state)

        assert final_state["structured_resume"] == mock_structured_resume
        assert len(final_state["structured_jobs"]) == 1
        assert len(final_state["optimized_resumes"]) == 1
        assert final_state["pdf_generated"] is True
        mock_generate_pdf.assert_called_once()


@pytest.mark.asyncio
async def test_run_graph_pipeline_publishes_done(
    sample_resume_analysis,
    sample_job_analysis,
    sample_optimized_resume,
    temp_dir,
    monkeypatch,
):
    from app.config import settings
    monkeypatch.setattr(settings, "temp_dir", str(temp_dir))

    session_id = "test-run-pipeline-done"
    (temp_dir / session_id).mkdir(parents=True, exist_ok=True)
    queue = asyncio.Queue()

    mock_structured_resume = StructuredResume(
        candidate_name="Michael Bruno",
        skills=["Python", "FastAPI"],
        professional_summary="Desenvolvedor Python.",
        raw_text="Resume text with Python",
    )
    mock_structured_job = StructuredJob(
        job_index=0,
        title="Dev",
        required_skills=["Python"],
    )

    with patch("app.graph.nodes.cv_structurer_node.CVStructurerAgent") as MockCVStructurer, \
         patch("app.graph.nodes.job_analyzer_node.JobAnalystAgent") as MockJobAnalyst, \
         patch("app.graph.nodes.optimizer_node.ResumeOptimizerAgent") as MockOptimizer, \
         patch("app.graph.nodes.validator_node.ATSValidatorAgent") as MockValidator, \
         patch("app.graph.nodes.pdf_node.generate_pdf"):

        MockCVStructurer.return_value.structure_cv = AsyncMock(return_value=mock_structured_resume)
        MockJobAnalyst.return_value.analyze = AsyncMock(return_value=(mock_structured_job, sample_job_analysis))
        MockOptimizer.return_value.optimize_single = AsyncMock(return_value=sample_optimized_resume)
        
        mock_val_result = MagicMock()
        mock_val_result.approved = True
        MockValidator.return_value.validate = AsyncMock(return_value=mock_val_result)

        await run_graph_pipeline(
            session_id=session_id,
            resume_text="Resume text with Python",
            jobs=[JobInput(title="Dev", description="Role description")],
            output_mode="single",
            queue=queue,
        )

        events = []
        while not queue.empty():
            events.append(await queue.get())

        assert events[-1] == "__DONE__"
        complete_events = [e for e in events if isinstance(e, tuple) and e[0] == "complete"]
        assert len(complete_events) == 1
        assert complete_events[0][1]["progress"] == 100
