"""Eligibility Service (Eliminatory Criteria vs Ranking).

Separates mandatory eligibility checking (PASS / FAIL / UNKNOWN) from score ranking.
"""

from app.domain.eligibility import EligibilityResult, EligibilityStatus
from app.domain.job import StructuredJob
from app.domain.matching import JobMatchResult, MatchStatus
from app.domain.resume import StructuredResume


class EligibilityService:
    """Evaluates whether candidate meets strict mandatory disqualification criteria."""

    @staticmethod
    def evaluate_eligibility(
        resume: StructuredResume,
        job: StructuredJob,
        match_result: JobMatchResult,
    ) -> EligibilityResult:
        passed_criteria: list[str] = []
        disqualifying_factors: list[str] = []
        reasons: list[str] = []

        # 1. Experience Check
        cand_years = resume.total_years_experience or 0
        req_years = job.years_experience_required or 0
        if req_years > 0:
            if cand_years >= req_years:
                passed_criteria.append(f"Experiência mínima de {req_years} ano(s) atendida ({cand_years} anos).")
            elif cand_years < (req_years // 2):
                disqualifying_factors.append(
                    f"Tempo de experiência significativamente inferior ao mínimo exigido ({cand_years} anos vs {req_years} anos exigidos)."
                )

        # 2. Critical Mandatory Skills Check
        missing_mandatory = []
        for match in match_result.skill_matches:
            if match.required_skill in job.required_skills:
                if match.status == MatchStatus.NOT_FOUND:
                    missing_mandatory.append(match.required_skill)
                else:
                    passed_criteria.append(f"Competência obrigatória '{match.required_skill}' identificada.")

        if len(missing_mandatory) > (len(job.required_skills) // 2) and len(job.required_skills) > 1:
            disqualifying_factors.append(
                f"Ausência da maioria das competências obrigatórias: {', '.join(missing_mandatory)}."
            )

        if disqualifying_factors:
            status = EligibilityStatus.FAIL
            reasons = disqualifying_factors
        else:
            status = EligibilityStatus.PASS
            reasons = passed_criteria

        return EligibilityResult(
            status=status,
            passed_criteria=passed_criteria,
            disqualifying_factors=disqualifying_factors,
            reasons=reasons,
        )
