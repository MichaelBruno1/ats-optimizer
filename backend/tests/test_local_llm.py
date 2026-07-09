"""Unit tests for local LLM integration support and schema parsing resiliency."""

import pytest
from unittest.mock import patch

from app.api.schemas import ResumeAnalysis, OptimizedResume
from app.agents.base_agent import BaseAgent
from app.config import settings


def test_schema_parsing_resilience_missing_fields() -> None:
    """Should successfully parse incomplete JSON structures by falling back to schema default values."""
    # Mimic a local LLM output that only returns name and skills
    incomplete_resume_json = {
        "candidate_name": "Alice Johnson",
        "skills": ["Python", "FastAPI"]
    }
    
    analysis = ResumeAnalysis.model_validate(incomplete_resume_json)
    
    # Assert provided values are correct
    assert analysis.candidate_name == "Alice Johnson"
    assert analysis.skills == ["Python", "FastAPI"]
    
    # Assert missing fields fall back to defaults rather than causing validation failure
    assert analysis.contact_info == {}
    assert analysis.experience == []
    assert analysis.education == []
    assert analysis.ats_readability_score == 0
    assert analysis.strengths == []
    assert analysis.weaknesses == []
    assert analysis.improvement_suggestions == []


def test_optimized_resume_schema_resilience() -> None:
    """Should validate OptimizedResume with missing fields, falling back to defaults."""
    incomplete_opt_json = {
        "target_job_title": "Lead Software Engineer"
    }
    
    optimized = OptimizedResume.model_validate(incomplete_opt_json)
    assert optimized.target_job_title == "Lead Software Engineer"
    assert optimized.content.professional_summary == ""
    assert optimized.content.skills == []
    assert optimized.content.experience == []
    assert optimized.content.education == []
    assert optimized.changes_made == []
    assert optimized.estimated_ats_score == 0


class DummyAgent(BaseAgent):
    """Test subclass of BaseAgent."""
    system_prompt_file = "test_prompt.txt"


def test_base_agent_model_string_resolving() -> None:
    """Should build correct model strings based on settings."""
    with patch.object(settings, "llm_provider", "openai"), \
         patch.object(settings, "llm_model", "gpt-4o-mini"):
        agent = DummyAgent()
        assert agent.model == "openai/gpt-4o-mini"

    # Pre-prefixed model names should not be modified
    with patch.object(settings, "llm_provider", "openai"), \
         patch.object(settings, "llm_model", "ollama/llama3"):
        agent = DummyAgent()
        assert agent.model == "ollama/llama3"

    # Model names with slashes that are not known providers (e.g. custom huggingface models) should prepend configured provider
    with patch.object(settings, "llm_provider", "openai"), \
         patch.object(settings, "llm_model", "google/gemma-4-e4b"):
        agent = DummyAgent()
        assert agent.model == "openai/google/gemma-4-e4b"


def test_base_agent_local_llm_api_key_fallback() -> None:
    """Should supply a fallback 'local' API key if none is set and the provider is OpenAI/Ollama compatible."""
    # We will test _invoke logic indirectly by checking how extra_kwargs is built.
    # To do this, we patch litellm.acompletion to inspect kwargs.
    with patch.object(settings, "llm_provider", "openai"), \
         patch.object(settings, "llm_model", "my-local-model"), \
         patch.object(settings, "llm_api_key", ""), \
         patch.object(settings, "llm_api_base", "http://localhost:11434/v1"), \
         patch("app.agents.base_agent.litellm.acompletion") as mock_completion, \
         patch.object(BaseAgent, "system_prompt", "system prompt"):
        
        agent = DummyAgent()
        
        # Run _invoke asynchronously
        import asyncio
        try:
            asyncio.run(agent._invoke("user message"))
        except Exception:
            # We don't care if JSON parsing fails after call, we only want to inspect the call arguments
            pass
            
        mock_completion.assert_called_once()
        called_kwargs = mock_completion.call_args[1]
        
        # Check fallback api_key and passed api_base
        assert called_kwargs["api_key"] == "local"
        assert called_kwargs["api_base"] == "http://localhost:11434/v1"
