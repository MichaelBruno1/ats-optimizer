"""pytest configurations and shared fixtures for the ATS Optimizer test suite."""

import pytest
import pytest_asyncio
import shutil
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.api.schemas import (
    ResumeAnalysis,
    JobAnalysis,
    OptimizedResume,
    ResumeContent,
    OptimizedExperience,
    EducationEntry,
)
from app.config import settings


@pytest.fixture
def client() -> TestClient:
    """Return a FastAPI TestClient."""
    return TestClient(app, raise_server_exceptions=False)


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Return an asynchronous httpx client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac


@pytest.fixture
def clean_sessions() -> Generator[None, None, None]:
    """Clean the global progress queues in temp_storage before and after tests."""
    from app.services import temp_storage
    temp_storage._progress_queues.clear()
    yield
    temp_storage._progress_queues.clear()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing filesystem operations."""
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield Path(tmpdirname)


@pytest.fixture
def sample_resume_text() -> str:
    """Return a standard sample resume text."""
    return """
    Michael Bruno Antunes da Silva
    E-mail: michaelbruno1@hotmail.com
    Telefone: (21) 98911-5730
    
    Resumo Profissional:
    Desenvolvedor Python sênior com 6 anos de experiência em desenvolvimento backend,
    arquitetura de microsserviços, FastAPI e integrações de banco de dados.
    
    Habilidades:
    Python, FastAPI, Django, PostgreSQL, Docker, Git.
    
    Experiência:
    Empresa Tech - Desenvolvedor Backend
    2020 - Atual
    - Desenvolvimento e manutenção de APIs robustas usando FastAPI e Django.
    - Otimização de consultas SQL reduzindo tempo de resposta em 40%.
    
    Educação:
    Universidade Estácio de Sá - Bacharel em Sistemas de Informação (2018)
    """


@pytest.fixture
def sample_resume_analysis() -> ResumeAnalysis:
    """Return a pre-populated ResumeAnalysis object."""
    return ResumeAnalysis(
        candidate_name="Michael Bruno Antunes da Silva",
        contact_info={
            "email": "michaelbruno1@hotmail.com",
            "phone": "(21) 98911-5730",
            "location": "Rio de Janeiro, Brasil",
            "linkedin": "https://linkedin.com/in/michaelbruno",
        },
        professional_summary="Desenvolvedor Python sênior com 6 anos de experiência em backend.",
        skills=["Python", "FastAPI", "Django", "PostgreSQL", "Docker", "Git"],
        experience=[
            {
                "company": "Empresa Tech",
                "role": "Desenvolvedor Backend",
                "start_date": "2020",
                "end_date": "Atual",
                "description": "Desenvolvimento de APIs robustas usando FastAPI.",
                "achievements": ["Redução do tempo de resposta SQL em 40%."],
            }
        ],
        education=[
            {
                "institution": "Universidade Estácio de Sá",
                "degree": "Bacharelado",
                "field": "Sistemas de Informação",
                "graduation_year": 2018,
            }
        ],
        certifications=["AWS Certified Developer"],
        languages=["Português", "Inglês"],
        total_years_experience=6,
        formatting_issues=[],
        ats_readability_score=85,
        strengths=["Forte experiência com Python e FastAPI", "Resultados quantificáveis"],
        weaknesses=["Falta de certificação Docker oficial"],
        improvement_suggestions=["Adicionar certificações de Cloud"],
    )


@pytest.fixture
def sample_job_analysis() -> JobAnalysis:
    """Return a pre-populated JobAnalysis object."""
    return JobAnalysis(
        job_index=0,
        title="Desenvolvedor Backend Sênior",
        company="Tech Solutions",
        seniority_level="Senior",
        required_skills=["Python", "FastAPI", "PostgreSQL"],
        desired_skills=["Docker", "AWS"],
        soft_skills=["Comunicação", "Liderança"],
        ats_keywords=["Python", "FastAPI", "PostgreSQL", "APIs Restful", "Git"],
        certifications_required=[],
        years_experience_required=5,
        key_responsibilities=["Projetar APIs escaláveis", "Otimizar consultas de banco de dados"],
        industry="Technology",
        summary="Responsável pelo desenvolvimento backend usando Python e FastAPI.",
        compatibility_score=90,
        gap_analysis="Falta de experiência demonstrada com Cloud AWS.",
    )


@pytest.fixture
def sample_optimized_resume() -> OptimizedResume:
    """Return a pre-populated OptimizedResume object."""
    content = ResumeContent(
        professional_summary="Desenvolvedor Python Sênior focado em construção de APIs escaláveis com FastAPI.",
        skills=["Python", "FastAPI", "PostgreSQL", "Docker", "Git", "AWS"],
        experience=[
            OptimizedExperience(
                company="Empresa Tech",
                role="Desenvolvedor Backend",
                start_date="2020",
                end_date=None,
                description="Desenvolvimento e otimização de APIs robustas usando FastAPI e PostgreSQL.",
                achievements=["Otimização de consultas SQL reduzindo tempo de resposta em 40%."],
            )
        ],
        education=[
            EducationEntry(
                institution="Universidade Estácio de Sá",
                degree="Bacharel",
                field="Sistemas de Informação",
                graduation_year=2018,
            )
        ],
        certifications=["AWS Certified Developer"],
        additional_sections=[],
    )
    return OptimizedResume(
        job_index=0,
        target_job_title="Desenvolvedor Backend Sênior",
        content=content,
        changes_made=["Reestruturação de conquistas profissionais.", "Adicionada palavra-chave PostgreSQL."],
        keywords_added=["FastAPI", "PostgreSQL"],
        estimated_ats_score=92,
        compatibility_score=90,
    )
