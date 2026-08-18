"""Unit tests for ExperienceCoachAgent."""

import pytest
from unittest.mock import AsyncMock, patch

from app.agents.experience_coach_agent import ExperienceCoachAgent
from app.domain.job import StructuredJob
from app.domain.resume import ExperienceItem, StructuredResume


@pytest.mark.asyncio
async def test_experience_coach_agent_generation() -> None:
    agent = ExperienceCoachAgent()

    resume = StructuredResume(
        candidate_name="Michael Bruno",
        experience=[
            ExperienceItem(
                company="TechCorp",
                role="Python Dev",
                description="Desenvolveu APIs internas.",
                achievements=["Criou endpoints de cadastro."],
            )
        ],
    )
    jobs = [
        StructuredJob(
            job_index=0,
            title="Senior Python Engineer",
            required_skills=["Python", "FastAPI"],
            ats_keywords=["Python", "FastAPI", "REST API"],
        )
    ]

    mock_llm_response = {
        "examples": [
            {
                "company": "TechCorp",
                "role": "Python Dev",
                "original_description": "Desenvolveu APIs internas.",
                "suggested_description": "Projetou e implementou APIs RESTful de alta performance utilizando Python e FastAPI.",
                "suggested_bullet_points": [
                    "Desenvolveu microsserviços reduzindo latência em 25%.",
                ],
                "reasoning": "Emprega verbos de ação assertivos e contexto técnico alinhado à vaga.",
                "key_keywords_highlighted": ["Python", "FastAPI"],
            }
        ]
    }

    with patch.object(agent, "_invoke", new_callable=AsyncMock) as mock_invoke:
        mock_invoke.return_value = mock_llm_response

        suggestions = await agent.generate_suggestions(resume, jobs)

        assert len(suggestions) == 1
        assert suggestions[0].company == "TechCorp"
        assert "FastAPI" in suggestions[0].suggested_description
