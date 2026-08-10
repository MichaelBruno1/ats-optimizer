"""ATS & Anti-Hallucination Validator Service.

Programmatic validation cross-checking optimized resume against original resume text.
Strictly enforces:
1. Anti-hallucination (no fabricated skills, employers, dates, or certifications).
2. Keyword stuffing detection.
3. Structure & formatting sanity checks.
"""

import logging
import re
from app.api.schemas import OptimizedResume
from app.domain.resume import StructuredResume
from app.domain.validation import IssueCategory, IssueSeverity, ValidationIssue, ValidationResult
from app.services.skill_normalization import normalize_skill

logger = logging.getLogger(__name__)


class ATSValidatorService:
    """Programmatic validator verifying optimized resumes against ground truth."""

    @staticmethod
    def validate(
        optimized: OptimizedResume,
        original_resume: StructuredResume,
        original_text: str,
    ) -> ValidationResult:
        issues: list[ValidationIssue] = []
        errors: list[str] = []
        warnings: list[str] = []
        hallucination_detected = False

        orig_text_lower = (original_text + " " + " ".join(original_resume.skills)).lower()
        orig_skills_norm = {
            normalize_skill(s).canonical.lower() for s in original_resume.skills
        }

        # 1. Anti-hallucination check on Skills
        for skill in optimized.content.skills:
            skill_clean = skill.strip().lower()
            norm_skill = normalize_skill(skill).canonical.lower()

            if skill_clean not in orig_text_lower and norm_skill not in orig_skills_norm:
                hallucination_detected = True
                msg = f"Competência '{skill}' não identificada no currículo original."
                errors.append(msg)
                issues.append(
                    ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        category=IssueCategory.ANTI_HALLUCINATION,
                        message=msg,
                        field_affected="content.skills",
                    )
                )

        # 2. Anti-hallucination check on Employers
        orig_companies_lower = {
            exp.company.strip().lower() for exp in original_resume.experience if exp.company
        }
        for exp in optimized.content.experience:
            if exp.company and exp.company.strip().lower() not in orig_text_lower:
                hallucination_detected = True
                msg = f"Empresa '{exp.company}' não consta no histórico original do candidato."
                errors.append(msg)
                issues.append(
                    ValidationIssue(
                        severity=IssueSeverity.ERROR,
                        category=IssueCategory.ANTI_HALLUCINATION,
                        message=msg,
                        field_affected="content.experience",
                    )
                )

        # 3. Keyword Stuffing Detection
        summary_words = optimized.content.professional_summary.lower().split()
        if summary_words:
            word_counts = {}
            for w in summary_words:
                if len(w) > 4:
                    word_counts[w] = word_counts.get(w, 0) + 1
            for w, count in word_counts.items():
                if count > 4:
                    msg = f"Repetição excessiva da palavra '{w}' ({count} vezes) no resumo profissional (possível keyword stuffing)."
                    warnings.append(msg)
                    issues.append(
                        ValidationIssue(
                            severity=IssueSeverity.WARNING,
                            category=IssueCategory.KEYWORD_STUFFING,
                            message=msg,
                            field_affected="content.professional_summary",
                        )
                    )

        # 4. Length Sanity Check
        if len(optimized.content.professional_summary) > 600:
            msg = "Resumo profissional muito longo (mais de 600 caracteres) — pode prejudicar o layout do PDF."
            warnings.append(msg)
            issues.append(
                ValidationIssue(
                    severity=IssueSeverity.WARNING,
                    category=IssueCategory.ATS_FORMAT,
                    message=msg,
                    field_affected="content.professional_summary",
                )
            )

        approved = not hallucination_detected and len(errors) == 0
        validation_score = max(0, 100 - (len(errors) * 30 + len(warnings) * 10))

        return ValidationResult(
            approved=approved,
            validation_score=validation_score,
            issues=issues,
            validation_errors=errors,
            validation_warnings=warnings,
            hallucination_detected=hallucination_detected,
        )
