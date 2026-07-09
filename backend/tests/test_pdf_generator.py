"""Unit tests for the PDF generator service."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.services.pdf_generator import _detect_language, generate_pdf
from app.api.schemas import OptimizedResume, ResumeAnalysis


def test_detect_language_heuristics() -> None:
    """Test that language detection heuristics work for pt, es, en."""
    # Portuguese text samples
    assert _detect_language("Desenvolvedor sênior com experiência em tecnologia") == "pt"
    assert _detect_language("Minha educação e habilidades em sistemas") == "pt"

    # Spanish text samples
    assert _detect_language("Desarrollador senior con experiencia en tecnología") == "es"
    assert _detect_language("Mi educación y competencias en proyectos") == "es"

    # English/Default text samples
    assert _detect_language("Senior software developer with background in FastAPI") == "en"
    assert _detect_language("My educational credentials and professional summary") == "en"


def test_generate_pdf_real_rendering(sample_optimized_resume: OptimizedResume, temp_dir: Path) -> None:
    """Test that generate_pdf successfully renders a PDF file to disk without template syntax errors."""
    output_path = temp_dir / "resume_output.pdf"
    
    # We should run a real PDF generation to catch any Jinja2 or WeasyPrint compile issues
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


@patch("weasyprint.HTML")
def test_generate_pdf_propagates_weasyprint_exceptions(
    mock_html_class: MagicMock,
    sample_optimized_resume: OptimizedResume,
    temp_dir: Path
) -> None:
    """Test that WeasyPrint exceptions are propagated correctly."""
    mock_html_instance = MagicMock()
    mock_html_instance.write_pdf.side_effect = Exception("WeasyPrint internal error")
    mock_html_class.return_value = mock_html_instance

    output_path = temp_dir / "resume_error.pdf"

    with pytest.raises(Exception, match="WeasyPrint internal error"):
        generate_pdf(sample_optimized_resume, output_path)
