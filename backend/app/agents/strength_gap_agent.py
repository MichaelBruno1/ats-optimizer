"""Strength and Gap Analysis Agent.

Synthesizes matching engine results into contextual candidate strengths & gaps with evidence.
"""

import json
import logging
from app.agents.base_agent import BaseAgent
from app.domain.job import StructuredJob
from app.domain.matching import JobMatchResult
from app.domain.resume import StructuredResume

logger = logging.getLogger(__name__)


class StrengthGapAnalystAgent(BaseAgent):
    """Synthesizes strengths and gaps with concrete evidence from matching results."""

    system_prompt_file = "strength_gap_prompts.md"

    async def analyze_strengths_and_gaps(
        self,
        resume: StructuredResume,
        job: StructuredJob,
        match_result: JobMatchResult,
    ) -> tuple[list[str], list[str], str]:
        # Formulate deterministic fallback + LLM contextual refinement
        strengths = []
        for m in match_result.skill_matches:
            if m.status.value == "MATCH" and m.evidence:
                strengths.append(f"{m.required_skill}: {m.evidence}")

        weaknesses = []
        for m in match_result.skill_matches:
            if m.status.value == "NOT_FOUND":
                weaknesses.append(f"Competência '{m.required_skill}' não encontrada no currículo.")
            elif m.status.value == "PARTIAL" and m.evidence:
                weaknesses.append(f"Competência '{m.required_skill}' parcialmente identificada ({m.evidence}).")

        gap_analysis_summary = (
            f"Gaps identificados: {len(match_result.missing_skills)} competência(s) ausente(s) "
            f"({', '.join(match_result.missing_skills[:5]) if match_result.missing_skills else 'Nenhuma'}). "
            f"Palavras-chave ausentes: {len(match_result.missing_keywords)}."
        )

        return strengths[:5], weaknesses[:5], gap_analysis_summary
