"""Optimization Planner Agent.

Generates an explicit OptimizationPlan before altering the resume.
"""

import json
import logging
from app.agents.base_agent import BaseAgent
from app.domain.job import StructuredJob
from app.domain.matching import JobMatchResult
from app.domain.optimization import OptimizationPlan, PlanAction, PlanItem
from app.domain.resume import StructuredResume

logger = logging.getLogger(__name__)


class OptimizationPlannerAgent(BaseAgent):
    """Creates a strategic optimization plan prior to resume rewriting."""

    system_prompt_file = "optimization_planner.md"

    async def create_plan(
        self,
        resume: StructuredResume,
        job: StructuredJob,
        match_result: JobMatchResult,
    ) -> OptimizationPlan:
        items: list[PlanItem] = []

        # 1. Summary rewrite action
        items.append(
            PlanItem(
                section="summary",
                action=PlanAction.REWRITE_SUMMARY,
                target_item="professional_summary",
                reason=f"Alinhar resumo com o cargo alvo '{job.title}' incorporando principais keywords.",
                keywords_to_incorporate=job.ats_keywords[:5],
            )
        )

        # 2. Skills reordering action
        items.append(
            PlanItem(
                section="skills",
                action=PlanAction.REORDER_SKILLS,
                target_item="skills",
                reason="Priorizar competências mais relevantes para a vaga no topo da lista.",
                keywords_to_incorporate=match_result.matched_skills[:10],
            )
        )

        # 3. Bullet rewrite action for experience
        if resume.experience:
            items.append(
                PlanItem(
                    section="experience",
                    action=PlanAction.REWRITE_BULLET,
                    target_item="experience[0].achievements",
                    reason="Reformular conquistas no formato XYZ destacando resultados quantificáveis.",
                    keywords_to_incorporate=match_result.missing_keywords[:5],
                )
            )

        return OptimizationPlan(
            job_index=job.job_index,
            target_job_title=job.title,
            items=items,
            summary_strategy=f"Destacar experiência relevante para {job.title}.",
            skills_reorder_strategy="Reorganizar habilidades por ordem de relevância para a vaga.",
        )
