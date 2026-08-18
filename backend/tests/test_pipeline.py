"""Integration tests for the full optimization pipeline, on-demand PDF generation, and SSE progress streaming."""

import io
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from app.api.schemas import ResumeAnalysis, JobAnalysis, OptimizedResume
from app.domain.job import SeniorityLevel, StructuredJob
from app.domain.resume import StructuredResume
from app.config import settings
from app.services.temp_storage import get_session_dir, get_pdf_path


@pytest.mark.asyncio
async def test_full_pipeline_integration_success(
    async_client,
    clean_sessions,
    temp_dir: Path,
    sample_resume_analysis: ResumeAnalysis,
    sample_job_analysis: JobAnalysis,
    sample_optimized_resume: OptimizedResume,
    monkeypatch
) -> None:
    """Test full pipeline execution: POST /analyze -> SSE progress stream -> POST /generate-pdf -> GET /download."""
    monkeypatch.setattr(settings, "temp_dir", str(temp_dir))

    mock_structured_resume = StructuredResume(
        candidate_name="Michael Bruno",
        skills=["Python", "FastAPI"],
        professional_summary="Desenvolvedor Python.",
        raw_text="Candidate Profile Info",
    )
    mock_structured_job = StructuredJob(
        job_index=0,
        title="Desenvolvedor Backend Sênior",
        required_skills=["Python", "FastAPI"],
        ats_keywords=["Python", "FastAPI"],
    )

    with patch("app.graph.nodes.cv_structurer_node.CVStructurerAgent.structure_cv", new_callable=AsyncMock) as mock_cv_struct, \
         patch("app.graph.nodes.job_analyzer_node.JobAnalystAgent.analyze", new_callable=AsyncMock) as mock_job_analyze, \
         patch("app.graph.nodes.optimizer_node.ResumeOptimizerAgent.optimize_single", new_callable=AsyncMock) as mock_optimize, \
         patch("app.graph.nodes.validator_node.ATSValidatorAgent.validate", new_callable=AsyncMock) as mock_validate, \
         patch("app.api.router.generate_pdf") as mock_pdf_gen:

        mock_cv_struct.return_value = mock_structured_resume
        mock_job_analyze.return_value = (mock_structured_job, sample_job_analysis)
        mock_optimize.return_value = sample_optimized_resume
        
        mock_val_result = MagicMock()
        mock_val_result.approved = True
        mock_validate.return_value = mock_val_result

        def fake_pdf_gen(optimized, pdf_path, resume_analysis):
            Path(pdf_path).write_bytes(b"%PDF-1.4 Mock PDF Content")
        mock_pdf_gen.side_effect = fake_pdf_gen

        # 1. Trigger /analyze POST request
        fake_txt = io.BytesIO(b"Candidate Profile Info")
        jobs_payload = json.dumps([
            {"title": "Desenvolvedor Backend Sênior", "description": "Python, FastAPI"}
        ])
        
        response = await async_client.post(
            "/api/v1/analyze",
            files={"resume": ("resume.txt", fake_txt, "text/plain")},
            data={"jobs": jobs_payload, "output_mode": "single"},
        )
        assert response.status_code == 200
        session_id = response.json()["session_id"]
        assert len(session_id) == 32

        # 2. Connect to GET /progress/{session_id} and read SSE stream
        progress_events = []
        complete_event = None
        
        async with async_client.stream("GET", f"/api/v1/progress/{session_id}") as stream:
            assert stream.status_code == 200
            
            event_type = None
            async for line in stream.aiter_lines():
                line = line.strip()
                if line.startswith("event:"):
                    event_type = line.split(":", 1)[1].strip()
                elif line.startswith("data:") and event_type:
                    data_json = json.loads(line.split(":", 1)[1].strip())
                    
                    if event_type == "progress":
                        progress_events.append(data_json)
                    elif event_type == "complete":
                        complete_event = data_json
                        break
                    elif event_type == "error":
                        pytest.fail(f"Pipeline returned error event: {data_json}")

        assert len(progress_events) > 0
        steps = [p["step"] for p in progress_events]
        assert "resume_analysis" in steps
        assert "job_analysis" in steps
        assert "optimization" in steps
        assert "validation" in steps

        assert complete_event is not None
        assert complete_event["progress"] == 100
        assert "result" in complete_event
        
        result_path = get_session_dir(session_id) / "result.json"
        assert result_path.exists()
        stored_result = json.loads(result_path.read_text(encoding="utf-8"))
        assert stored_result["session_id"] == session_id
        assert "experience_examples" in stored_result

        # 3. Test on-demand PDF generation endpoint
        gen_response = await async_client.post(f"/api/v1/generate-pdf/{session_id}/0")
        assert gen_response.status_code == 200
        assert gen_response.json()["status"] == "ready"

        # 4. Check PDF download
        pdf_response = await async_client.get(f"/api/v1/download/{session_id}/0")
        assert pdf_response.status_code == 200
        assert pdf_response.content == b"%PDF-1.4 Mock PDF Content"
        assert pdf_response.headers["content-type"] == "application/pdf"


@pytest.mark.asyncio
async def test_pipeline_integration_failure_propagation(
    async_client,
    clean_sessions,
    temp_dir: Path,
    monkeypatch
) -> None:
    """Test that agent exceptions are caught and correctly streamed as error events over SSE."""
    monkeypatch.setattr(settings, "temp_dir", str(temp_dir))

    with patch("app.graph.nodes.cv_structurer_node.CVStructurerAgent.structure_cv", new_callable=AsyncMock) as mock_cv_struct:
        mock_cv_struct.side_effect = Exception("LLM Agent analysis timeout")

        fake_txt = io.BytesIO(b"Candidate Profile Info")
        jobs_payload = json.dumps([
            {"title": "Developer", "description": "FastAPI"}
        ])

        response = await async_client.post(
            "/api/v1/analyze",
            files={"resume": ("resume.txt", fake_txt, "text/plain")},
            data={"jobs": jobs_payload, "output_mode": "single"},
        )
        session_id = response.json()["session_id"]

        error_event = None
        async with async_client.stream("GET", f"/api/v1/progress/{session_id}") as stream:
            assert stream.status_code == 200
            
            event_type = None
            async for line in stream.aiter_lines():
                line = line.strip()
                if line.startswith("event:"):
                    event_type = line.split(":", 1)[1].strip()
                elif line.startswith("data:") and event_type:
                    data_json = json.loads(line.split(":", 1)[1].strip())
                    if event_type == "error":
                        error_event = data_json
                        break

        assert error_event is not None
        assert "Falha no processamento" in error_event["message"]
        assert "LLM Agent analysis timeout" in error_event["message"]
