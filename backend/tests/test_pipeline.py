"""Integration tests for the full optimization pipeline and SSE progress streaming."""

import io
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.api.schemas import ResumeAnalysis, JobAnalysis, OptimizedResume
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
    """Test full pipeline execution: POST /analyze -> SSE progress stream -> GET /download."""
    # Patch temp_dir to use isolated temp directory
    monkeypatch.setattr(settings, "temp_dir", str(temp_dir))

    # Mock the LLM Agents
    with patch("app.api.router.ResumeAnalystAgent.analyze") as mock_resume_analyze, \
         patch("app.api.router.JobAnalystAgent.analyze") as mock_job_analyze, \
         patch("app.api.router.ResumeOptimizerAgent.optimize_single") as mock_optimize, \
         patch("app.api.router.generate_pdf") as mock_pdf_gen:

        mock_resume_analyze.return_value = sample_resume_analysis
        mock_job_analyze.return_value = sample_job_analysis
        mock_optimize.return_value = sample_optimized_resume
        
        # Mock pdf generator to write a dummy file
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
        
        # Connect to progress endpoint
        async with async_client.stream("GET", f"/api/v1/progress/{session_id}") as stream:
            assert stream.status_code == 200
            
            # Read lines from the SSE stream
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

        # Assert correct progress steps were streamed
        assert len(progress_events) > 0
        steps = [p["step"] for p in progress_events]
        assert "resume_analysis" in steps
        assert "job_analysis" in steps
        assert "optimization" in steps
        assert "pdf_generation" in steps

        # Assert completion event details
        assert complete_event is not None
        assert complete_event["progress"] == 100
        assert "result" in complete_event
        
        # Validate result.json was written to disk
        result_path = get_session_dir(session_id) / "result.json"
        assert result_path.exists()
        stored_result = json.loads(result_path.read_text(encoding="utf-8"))
        assert stored_result["session_id"] == session_id

        # 3. Check PDF download
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

    # Mock ResumeAnalystAgent to raise an exception
    with patch("app.api.router.ResumeAnalystAgent.analyze") as mock_resume_analyze:
        mock_resume_analyze.side_effect = Exception("LLM Agent analysis timeout")

        fake_txt = io.BytesIO(b"Candidate Profile Info")
        jobs_payload = json.dumps([
            {"title": "Developer", "description": "FastAPI"}
        ])

        # POST analyze
        response = await async_client.post(
            "/api/v1/analyze",
            files={"resume": ("resume.txt", fake_txt, "text/plain")},
            data={"jobs": jobs_payload, "output_mode": "single"},
        )
        session_id = response.json()["session_id"]

        # Read SSE Stream expecting an error event
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
