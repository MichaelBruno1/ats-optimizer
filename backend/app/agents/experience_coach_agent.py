"""Experience Coach Agent.

Generates educational recommendations and before/after phrasing examples
to teach candidates how to describe their experiences more effectively.
These suggestions are purely educational and are rendered on the results dashboard,
NEVER added directly to the generated PDF.
"""

import json
import logging
from typing import Any

from app.agents.base_agent import BaseAgent
from app.api.schemas import ExperienceExample
from app.domain.job import StructuredJob
from app.domain.resume import StructuredResume

logger = logging.getLogger(__name__)


class ExperienceCoachAgent(BaseAgent):
    """Generates educational before/after experience descriptions aligned to the vacancy."""

    system_prompt_file = "experience_coach.md"

    async def generate_suggestions(
        self,
        resume: StructuredResume,
        jobs: list[StructuredJob],
    ) -> list[ExperienceExample]:
        """Generate high-impact experience phrasing suggestions for up to 3 candidate positions."""
        if not resume.experience:
            return []

        # Prepare summary of candidate experience (up to 3 positions)
        exp_summary = [
            {
                "company": e.company,
                "role": e.role,
                "description": e.description,
                "achievements": e.achievements,
            }
            for e in resume.experience[:3]
        ]

        # Prepare target jobs context
        jobs_summary = [
            {
                "title": j.title,
                "required_skills": j.required_skills[:10],
                "ats_keywords": j.ats_keywords[:15],
            }
            for j in jobs[:2]
        ]

        user_message = (
            f"=== TARGET JOB CONTEXT ===\n"
            f"{json.dumps(jobs_summary, ensure_ascii=False, indent=2)}\n\n"
            f"=== CANDIDATE ORIGINAL EXPERIENCES ===\n"
            f"{json.dumps(exp_summary, ensure_ascii=False, indent=2)}"
        )

        try:
            raw = await self._invoke(user_message)
            examples_raw = raw.get("examples", [])
            results: list[ExperienceExample] = []

            for item in examples_raw:
                results.append(ExperienceExample.model_validate(item))

            return results
        except Exception as exc:
            logger.warning("ExperienceCoachAgent failed (%s). Generating fallback examples.", exc)
            fallback_examples: list[ExperienceExample] = []
            for exp in resume.experience[:2]:
                fallback_examples.append(
                    ExperienceExample(
                        company=exp.company,
                        role=exp.role,
                        original_description=exp.description or (exp.achievements[0] if exp.achievements else ""),
                        suggested_description=(
                            f"Liderou entregas técnicas na {exp.company} como {exp.role}, "
                            f"aplicando boas práticas de engenharia e otimizando processos-chave."
                        ),
                        suggested_bullet_points=[
                            f"Implementou soluções escaláveis focadas em qualidade e performance utilizando stack moderna.",
                            f"Colaborou com equipes multidisciplinares entregando funcionalidades críticas no prazo.",
                        ],
                        reasoning=(
                            "Destaca verbos de ação ('Liderou', 'Implementou'), estabelece o contexto do papel "
                            "e evidencia impacto técnico com clareza para o recrutador."
                        ),
                        key_keywords_highlighted=[j.title for j in jobs[:1]],
                    )
                )
            return fallback_examples
