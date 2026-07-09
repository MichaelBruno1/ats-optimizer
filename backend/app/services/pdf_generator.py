"""PDF Generator Service.

Renders an OptimizedResume into a professionally formatted PDF using
WeasyPrint (HTML/CSS → PDF) and Jinja2 for templating.

The generated file is written directly to the path specified by the caller
(typically a session-scoped temp directory).
"""

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.api.schemas import OptimizedResume, ResumeAnalysis

logger = logging.getLogger(__name__)

# Resolve the templates directory relative to this file's location
_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
_TEMPLATE_NAME = "resume_template.html"


def _detect_language(text: str) -> str:
    """Detect if the text is Portuguese, Spanish, or English based on common keywords."""
    text_lower = text.lower()
    pt_words = {"experiência", "desenvolvedor", "resumo", "educação", "idiomas", "projetos", "habilidades"}
    es_words = {"experiencia", "desarrollador", "resumen", "educación", "idiomas", "proyectos", "competencias"}
    
    pt_count = sum(1 for w in pt_words if w in text_lower)
    es_count = sum(1 for w in es_words if w in text_lower)
    
    if pt_count > es_count and pt_count > 0:
        return "pt"
    elif es_count > pt_count and es_count > 0:
        return "es"
    return "en"


_TRANSLATIONS = {
    "pt": {
        "summary": "Resumo Profissional",
        "skills": "Habilidades",
        "experience": "Experiência Profissional",
        "present": "Atual",
        "education": "Formação Acadêmica",
        "certifications": "Certificações",
        "default_name": "Candidato",
    },
    "es": {
        "summary": "Resumen Profesional",
        "skills": "Habilidades",
        "experience": "Experiencia Profesional",
        "present": "Presente",
        "education": "Educación",
        "certifications": "Certificaciones",
        "default_name": "Candidato",
    },
    "en": {
        "summary": "Professional Summary",
        "skills": "Skills",
        "experience": "Professional Experience",
        "present": "Present",
        "education": "Education",
        "certifications": "Certifications",
        "default_name": "Candidate",
    }
}


def generate_pdf(
    optimized_resume: OptimizedResume,
    output_path: str | Path,
    resume_analysis: ResumeAnalysis | None = None,
) -> None:
    """Render an optimized resume to PDF at the specified path.

    Combines WeasyPrint for PDF rendering with Jinja2 for HTML templating.
    The HTML template receives the full serialized resume dict plus optional
    contact information extracted from the original resume analysis.

    Args:
        optimized_resume: The validated OptimizedResume produced by the optimizer agent.
        output_path: Absolute path where the PDF file should be written.
        resume_analysis: Optional original resume analysis used to populate
            the candidate name and contact information in the header.

    Raises:
        OSError: If the output path cannot be created or written to.
        Exception: Propagates WeasyPrint or Jinja2 errors with context.
    """
    # ── Resolve output path ───────────────────────────────────────────────────
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    # ── Template context ──────────────────────────────────────────────────────
    resume_dict = optimized_resume.model_dump()

    candidate_name: str | None = None
    contact_info: dict = {}
    if resume_analysis:
        candidate_name = resume_analysis.candidate_name
        contact_info = resume_analysis.contact_info or {}

    # Detect language using professional summary and target job title
    summary_text = (optimized_resume.content.professional_summary or "") + " " + (optimized_resume.target_job_title or "")
    lang = _detect_language(summary_text)
    labels = _TRANSLATIONS[lang]

    context = {
        "resume": resume_dict,
        "candidate_name": candidate_name,
        "contact_info": contact_info,
        "labels": labels,
    }

    # ── Jinja2 rendering ──────────────────────────────────────────────────────
    logger.debug("Loading Jinja2 template from: %s", _TEMPLATES_DIR)
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template(_TEMPLATE_NAME)
    html_content = template.render(**context)

    # ── WeasyPrint PDF generation ─────────────────────────────────────────────
    logger.info(
        "Generating PDF for job_index=%s → %s",
        optimized_resume.job_index,
        output,
    )
    try:
        from weasyprint import HTML  # lazy import — WeasyPrint has heavy startup

        HTML(string=html_content, base_url=str(_TEMPLATES_DIR)).write_pdf(str(output))
    except Exception as exc:
        logger.exception("WeasyPrint failed to generate PDF at '%s'", output)
        raise RuntimeError(
            f"PDF generation failed for job_index={optimized_resume.job_index}: {exc}"
        ) from exc

    logger.info("PDF written successfully (%d bytes)", output.stat().st_size)
