"""Integration tests for the ATS Optimizer API endpoints.

Uses FastAPI's TestClient (synchronous httpx) to exercise the API
without requiring a running server or a real LLM connection.

Tests:
- GET /api/v1/health
- GET /api/v1/config
- POST /api/v1/analyze with invalid file format (should return 422)
- POST /api/v1/analyze with missing fields (should return 422)
- GET /api/v1/download with non-existent session (should return 404)
"""

import io
import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)


# ─────────────────────────────────────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────────────────────────────────────


class TestHealth:
    """Tests for GET /api/v1/health."""

    def test_health_returns_200(self) -> None:
        """Health endpoint should return HTTP 200."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_health_contains_required_fields(self) -> None:
        """Health response should include status, llm_provider, and model."""
        response = client.get("/api/v1/health")
        body = response.json()
        assert body["status"] == "healthy"
        assert "llm_provider" in body
        assert "model" in body

    def test_health_status_is_healthy(self) -> None:
        """Health status field must be the string 'healthy'."""
        response = client.get("/api/v1/health")
        assert response.json()["status"] == "healthy"


# ─────────────────────────────────────────────────────────────────────────────
# Config endpoint
# ─────────────────────────────────────────────────────────────────────────────


class TestConfig:
    """Tests for GET /api/v1/config."""

    def test_config_returns_200(self) -> None:
        """Config endpoint should return HTTP 200."""
        response = client.get("/api/v1/config")
        assert response.status_code == 200

    def test_config_contains_accepted_formats(self) -> None:
        """Config response should list accepted file formats."""
        response = client.get("/api/v1/config")
        body = response.json()
        assert "accepted_formats" in body
        assert isinstance(body["accepted_formats"], list)
        assert ".pdf" in body["accepted_formats"]
        assert ".docx" in body["accepted_formats"]
        assert ".txt" in body["accepted_formats"]

    def test_config_contains_max_jobs(self) -> None:
        """Config response should include max_jobs as a positive integer."""
        response = client.get("/api/v1/config")
        body = response.json()
        assert "max_jobs" in body
        assert isinstance(body["max_jobs"], int)
        assert body["max_jobs"] > 0

    def test_config_contains_output_modes(self) -> None:
        """Config response should include output_modes list."""
        response = client.get("/api/v1/config")
        body = response.json()
        assert "output_modes" in body
        assert "single" in body["output_modes"]
        assert "per_job" in body["output_modes"]


# ─────────────────────────────────────────────────────────────────────────────
# Analyze endpoint — validation errors (no LLM needed)
# ─────────────────────────────────────────────────────────────────────────────


class TestAnalyzeValidation:
    """Tests for POST /api/v1/analyze focusing on input validation."""

    def _valid_jobs_payload(self) -> str:
        """Return a valid single-job JSON string."""
        return json.dumps([
            {"title": "Software Engineer", "description": "Python and FastAPI required."}
        ])

    def test_invalid_file_format_returns_422(self) -> None:
        """Uploading a .jpg file should be rejected with HTTP 422."""
        jobs_json = self._valid_jobs_payload()
        fake_jpg = io.BytesIO(b"\xff\xd8\xff" + b"x" * 100)  # JPEG magic bytes

        response = client.post(
            "/api/v1/analyze",
            files={"resume": ("photo.jpg", fake_jpg, "image/jpeg")},
            data={"jobs": jobs_json, "output_mode": "single"},
        )
        assert response.status_code == 422

    def test_missing_resume_field_returns_422(self) -> None:
        """Omitting the resume field should return HTTP 422."""
        response = client.post(
            "/api/v1/analyze",
            data={"jobs": self._valid_jobs_payload(), "output_mode": "single"},
        )
        assert response.status_code == 422

    def test_missing_jobs_field_returns_422(self) -> None:
        """Omitting the jobs field should return HTTP 422."""
        fake_txt = io.BytesIO(b"John Doe\nSoftware Engineer")
        response = client.post(
            "/api/v1/analyze",
            files={"resume": ("resume.txt", fake_txt, "text/plain")},
            data={"output_mode": "single"},
        )
        assert response.status_code == 422

    def test_invalid_jobs_json_returns_422(self) -> None:
        """Malformed JSON in the jobs field should return HTTP 422."""
        fake_txt = io.BytesIO(b"John Doe\nSoftware Engineer")
        response = client.post(
            "/api/v1/analyze",
            files={"resume": ("resume.txt", fake_txt, "text/plain")},
            data={"jobs": "this is not json", "output_mode": "single"},
        )
        assert response.status_code == 422

    def test_invalid_output_mode_returns_422(self) -> None:
        """An invalid output_mode value should return HTTP 422."""
        fake_txt = io.BytesIO(b"John Doe\nSoftware Engineer")
        response = client.post(
            "/api/v1/analyze",
            files={"resume": ("resume.txt", fake_txt, "text/plain")},
            data={
                "jobs": self._valid_jobs_payload(),
                "output_mode": "invalid_mode",
            },
        )
        assert response.status_code == 422

    def test_empty_jobs_array_returns_422(self) -> None:
        """An empty jobs array should return HTTP 422."""
        fake_txt = io.BytesIO(b"John Doe\nSoftware Engineer")
        response = client.post(
            "/api/v1/analyze",
            files={"resume": ("resume.txt", fake_txt, "text/plain")},
            data={"jobs": "[]", "output_mode": "single"},
        )
        assert response.status_code == 422

    def test_txt_resume_with_valid_data_returns_session_id(self) -> None:
        """A valid .txt resume with valid jobs should return a session_id.

        We mock the background pipeline so no LLM call is made.
        """
        with patch("app.api.router.asyncio.create_task") as mock_task:
            mock_task.return_value = None  # Suppress background task

            fake_txt = io.BytesIO(b"John Doe\nSoftware Engineer\nPython, FastAPI")
            response = client.post(
                "/api/v1/analyze",
                files={"resume": ("resume.txt", fake_txt, "text/plain")},
                data={"jobs": self._valid_jobs_payload(), "output_mode": "single"},
            )

        assert response.status_code == 200
        body = response.json()
        assert "session_id" in body
        assert len(body["session_id"]) == 32  # UUID4 hex


# ─────────────────────────────────────────────────────────────────────────────
# Download endpoint
# ─────────────────────────────────────────────────────────────────────────────


class TestDownload:
    """Tests for GET /api/v1/download/{session_id}/{job_index}."""

    def test_nonexistent_session_returns_404(self) -> None:
        """Requesting a download for an unknown session should return 404."""
        response = client.get("/api/v1/download/nonexistentsession12345678/0")
        assert response.status_code == 404

    def test_invalid_job_index_type_returns_422(self) -> None:
        """A non-integer job_index should return HTTP 422."""
        response = client.get("/api/v1/download/some_session/not_an_int")
        assert response.status_code == 422
