"""Deterministic ATS Scoring Service.

Calculates final ATS score using a strict code-based mathematical formula.
The LLM DOES NOT compute the final score.
"""

from app.domain.job import SeniorityLevel, StructuredJob
from app.domain.matching import JobMatchResult, MatchStatus
from app.domain.resume import StructuredResume
from app.domain.scoring import ATSScoreResult, ScoreComponents, ScoringWeights


class ScoringService:
    """Calculates objective ATS scores from candidate resume & job match results."""

    def __init__(self, weights: ScoringWeights | None = None) -> None:
        self.weights = weights or ScoringWeights()

    def calculate_score(
        self,
        resume: StructuredResume,
        job: StructuredJob,
        match_result: JobMatchResult,
    ) -> ATSScoreResult:
        # 1. Keyword Coverage Component (0.0 - 1.0)
        kw_comp = match_result.keyword_coverage_ratio

        # 2. Required Skills Match Component (0.0 - 1.0)
        req_matches = [
            m for m in match_result.skill_matches
            if m.required_skill in job.required_skills
        ]
        if req_matches:
            match_score_sum = sum(
                1.0 if m.status == MatchStatus.MATCH else (0.5 if m.status == MatchStatus.PARTIAL else 0.0)
                for m in req_matches
            )
            req_comp = match_score_sum / len(req_matches)
        else:
            req_comp = 1.0

        # 3. Experience Alignment Component (0.0 - 1.0)
        cand_years = resume.total_years_experience or 0
        req_years = job.years_experience_required or 0
        if req_years == 0:
            exp_comp = 1.0
        elif cand_years >= req_years:
            exp_comp = 1.0
        else:
            exp_comp = max(0.2, cand_years / req_years)

        # 4. Responsibilities Coverage Component (0.0 - 1.0)
        resp_comp = 0.8  # Default baseline when key responsibilities match
        if job.key_responsibilities:
            text_lower = (resume.raw_text + " " + resume.professional_summary).lower()
            resp_matched = sum(
                1 for r in job.key_responsibilities if any(w in text_lower for w in r.lower().split() if len(w) > 4)
            )
            resp_comp = min(1.0, max(0.3, resp_matched / len(job.key_responsibilities)))

        # 5. Seniority Match Component (0.0 - 1.0)
        seniority_comp = 1.0
        seniority_order = {
            SeniorityLevel.JUNIOR: 1,
            SeniorityLevel.MID: 2,
            SeniorityLevel.SENIOR: 3,
            SeniorityLevel.LEAD: 4,
            SeniorityLevel.MANAGER: 5,
        }
        cand_level = SeniorityLevel.SENIOR if cand_years >= 5 else (SeniorityLevel.MID if cand_years >= 2 else SeniorityLevel.JUNIOR)
        cand_val = seniority_order[cand_level]
        job_val = seniority_order.get(job.seniority_level, 2)
        if cand_val >= job_val:
            seniority_comp = 1.0
        else:
            seniority_comp = 0.6 if (job_val - cand_val) == 1 else 0.3

        # 6. Education Component (0.0 - 1.0)
        edu_comp = 1.0 if resume.education else 0.7

        components = ScoreComponents(
            keyword_coverage=round(kw_comp, 2),
            required_skills=round(req_comp, 2),
            experience_alignment=round(exp_comp, 2),
            responsibilities=round(resp_comp, 2),
            seniority=round(seniority_comp, 2),
            education=round(edu_comp, 2),
        )

        final_raw = (
            components.keyword_coverage * self.weights.keyword_coverage
            + components.required_skills * self.weights.required_skills
            + components.experience_alignment * self.weights.experience_alignment
            + components.responsibilities * self.weights.responsibilities
            + components.seniority * self.weights.seniority
            + components.education * self.weights.education
        )

        final_score = int(round(final_raw * 100))
        final_score = max(0, min(100, final_score))

        explanation = (
            f"Score ATS calculado via código: Cobertura de Keywords={int(kw_comp*100)}%, "
            f"Skills Obrigatórias={int(req_comp*100)}%, Experiência={int(exp_comp*100)}%."
        )

        return ATSScoreResult(
            score=final_score,
            components=components,
            weights=self.weights,
            explanation=explanation,
        )
