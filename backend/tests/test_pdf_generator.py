"""Unit tests for the PDF generator service."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.services.pdf_generator import _detect_language, generate_pdf
from app.api.schemas import OptimizedResume, ResumeAnalysis


def test_detect_language_heuristics() -> None:
    """Test that language detection heuristics work for pt, es, en."""
    assert _detect_language("Desenvolvedor sênior com experiência em tecnologia") == "pt"
    assert _detect_language("Minha educação e habilidades em sistemas") == "pt"
    assert _detect_language("Desarrollador senior con experiencia en tecnología") == "es"
    assert _detect_language("Mi educación y competencias en proyectos") == "es"
    assert _detect_language("Senior software developer with background in FastAPI") == "en"
    assert _detect_language("My educational credentials and professional summary") == "en"


def test_generate_pdf_real_rendering(sample_optimized_resume: OptimizedResume, temp_dir: Path) -> None:
    """Test that generate_pdf successfully renders a PDF/fallback file to disk without template syntax errors."""
    output_path = temp_dir / "resume_output.pdf"
    generate_pdf(sample_optimized_resume, output_path)
    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_generate_pdf_with_contact_info(
    sample_optimized_resume: OptimizedResume,
    sample_resume_analysis: ResumeAnalysis,
    temp_dir: Path
) -> None:
    """Test PDF generation with optional candidate contact info provided."""
    output_path = temp_dir / "resume_output_contact.pdf"
    generate_pdf(sample_optimized_resume, output_path, resume_analysis=sample_resume_analysis)
    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_generate_pdf_propagates_weasyprint_exceptions(
    sample_optimized_resume: OptimizedResume,
    temp_dir: Path
) -> None:
    """Test that non-library WeasyPrint exceptions are propagated correctly."""
    output_path = temp_dir / "resume_error.pdf"

    with patch("jinja2.Environment.get_template") as mock_template:
        mock_template.side_effect = RuntimeError("Template rendering error")
        with pytest.raises(RuntimeError, match="Template rendering error"):
            generate_pdf(sample_optimized_resume, output_path)
