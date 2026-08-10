"""Matching Engine Service.

Combines exact matching, alias matching, semantic/rule matching,
experience context, and evidence generation.

Explicit Statuses:
- MATCH: Direct or alias match with strong evidence.
- PARTIAL: Equivalent skill possessed or partial experience.
- NOT_FOUND: Skill not present in candidate profile.
- CONFLICT: Contradictory information detected.
- UNKNOWN: Ambiguous evidence.
"""

import logging
from app.domain.job import StructuredJob
from app.domain.matching import JobMatchResult, MatchStatus, SkillMatch
from app.domain.resume import StructuredResume
from app.services.skill_normalization import get_equivalent_skills, normalize_skill

logger = logging.getLogger(__name__)


def evaluate_skill_match(
    required_skill: str,
    resume: StructuredResume,
) -> SkillMatch:
    """Evaluate a single required skill against the candidate's structured resume."""
    norm_req = normalize_skill(required_skill)
    req_canonical = norm_req.canonical.lower()

    # Collect candidate skills in normalized form
    candidate_skills_norm = {
        normalize_skill(s).canonical.lower(): s for s in resume.skills
    }

    # Also search full resume text for context evidence
    full_text_lower = resume.raw_text.lower() if resume.raw_text else ""
    summary_lower = resume.professional_summary.lower()

    # 1. Exact or Alias Match in skills list
    if req_canonical in candidate_skills_norm:
        matched_orig = candidate_skills_norm[req_canonical]
        evidence = f"Skill '{matched_orig}' declarada explicitamente no perfil do candidato."
        return SkillMatch(
            required_skill=required_skill,
            normalized_skill=norm_req.canonical,
            status=MatchStatus.MATCH,
            confidence=1.0,
            matched_candidate_skill=matched_orig,
            evidence=evidence,
            reason="Match exato/alias na lista de habilidades.",
        )

    # 2. Check work experience descriptions for exact mention
    exp_evidences = []
    for exp in resume.experience:
        exp_text = f"{exp.role} {exp.description} {' '.join(exp.achievements)} {' '.join(exp.technologies)}".lower()
        if req_canonical in exp_text or norm_req.original.lower() in exp_text:
            exp_evidences.append(f"{exp.role} na empresa '{exp.company}'")

    if exp_evidences:
        evidence = f"Skill identificada no histórico de experiência: {', '.join(exp_evidences)}."
        return SkillMatch(
            required_skill=required_skill,
            normalized_skill=norm_req.canonical,
            status=MatchStatus.MATCH,
            confidence=0.9,
            matched_candidate_skill=norm_req.canonical,
            evidence=evidence,
            reason="Skill demonstrada em experiências profissionais.",
        )

    # 3. Partial / Transferable Skill Check
    equivalents = get_equivalent_skills(norm_req.canonical)
    for eq in equivalents:
        eq_lower = eq.lower()
        if eq_lower in candidate_skills_norm or eq_lower in full_text_lower:
            evidence = f"Experiência equivalente identificada com '{eq}', transferível para '{norm_req.canonical}'."
            return SkillMatch(
                required_skill=required_skill,
                normalized_skill=norm_req.canonical,
                status=MatchStatus.PARTIAL,
                confidence=0.65,
                matched_candidate_skill=eq,
                evidence=evidence,
                reason="Possui tecnologia equivalente/semelhante.",
            )

    # 4. Keyword present in text but not in skills or explicit experience
    if req_canonical in summary_lower or req_canonical in full_text_lower:
        evidence = f"Termo '{norm_req.canonical}' mencionado no texto do currículo, mas não estruturado como competência."
        return SkillMatch(
            required_skill=required_skill,
            normalized_skill=norm_req.canonical,
            status=MatchStatus.PARTIAL,
            confidence=0.5,
            matched_candidate_skill=norm_req.canonical,
            evidence=evidence,
            reason="Possui menção no texto sem detalhamento de experiência.",
        )

    # 5. Not Found
    return SkillMatch(
        required_skill=required_skill,
        normalized_skill=norm_req.canonical,
        status=MatchStatus.NOT_FOUND,
        confidence=0.0,
        matched_candidate_skill=None,
        evidence=None,
        reason="Nenhuma evidência ou skill equivalente identificada no currículo.",
    )


class MatchingEngine:
    """Engine executing deterministic candidate-to-job matching."""

    @staticmethod
    def match(resume: StructuredResume, job: StructuredJob) -> JobMatchResult:
        skill_matches: list[SkillMatch] = []
        matched_skills: list[str] = []
        partial_matches: list[str] = []
        missing_skills: list[str] = []

        all_target_skills = list(dict.fromkeys(job.required_skills + job.desired_skills))

        for req in all_target_skills:
            match_res = evaluate_skill_match(req, resume)
            skill_matches.append(match_res)

            if match_res.status == MatchStatus.MATCH:
                matched_skills.append(req)
            elif match_res.status == MatchStatus.PARTIAL:
                partial_matches.append(req)
            elif match_res.status == MatchStatus.NOT_FOUND:
                missing_skills.append(req)

        # Keyword Coverage Calculation
        matched_keywords = []
        missing_keywords = []
        full_text_lower = resume.raw_text.lower() if resume.raw_text else ""
        skills_text_lower = " ".join(resume.skills).lower()

        for kw in job.ats_keywords:
            kw_clean = kw.strip().lower()
            if kw_clean in full_text_lower or kw_clean in skills_text_lower:
                matched_keywords.append(kw)
            else:
                missing_keywords.append(kw)

        coverage_ratio = (
            len(matched_keywords) / len(job.ats_keywords) if job.ats_keywords else 1.0
        )

        return JobMatchResult(
            job_index=job.job_index,
            job_title=job.title,
            skill_matches=skill_matches,
            matched_skills=matched_skills,
            partial_matches=partial_matches,
            missing_skills=missing_skills,
            matched_keywords=matched_keywords,
            missing_keywords=missing_keywords,
            keyword_coverage_ratio=coverage_ratio,
        )
