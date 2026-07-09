"""Application configuration using Pydantic BaseSettings.

Settings are loaded from environment variables or a .env file.
All field aliases correspond to the expected environment variable names.
"""

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    """Central configuration object for the ATS Optimizer backend."""

    # ── LLM ──────────────────────────────────────────────────────────────────
    llm_provider: str = Field(default="openai", alias="LLM_PROVIDER")
    llm_model: str = Field(default="gpt-4o-mini", alias="LLM_MODEL")
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_api_base: str = Field(default="", alias="LLM_API_BASE")
    llm_temperature: float = Field(default=0.3, alias="LLM_TEMPERATURE")
    llm_max_tokens: int = Field(default=2000, alias="LLM_MAX_TOKENS")

    # ── App ───────────────────────────────────────────────────────────────────
    max_file_size_mb: int = Field(default=5, alias="MAX_FILE_SIZE_MB")
    max_jobs: int = Field(default=3, alias="MAX_JOBS")
    temp_dir: str = Field(default="/tmp/ats_optimizer", alias="TEMP_DIR")
    temp_cleanup_minutes: int = Field(default=30, alias="TEMP_CLEANUP_MINUTES")
    cors_origins: str = Field(
        default="http://localhost:8000", alias="CORS_ORIGINS"
    )

    model_config = {"env_file": ".env", "populate_by_name": True}

    @model_validator(mode="after")
    def adjust_api_base_for_docker(self) -> "Settings":
        """If running inside Docker, automatically map localhost/127.0.0.1 to host.docker.internal."""
        is_docker = os.path.exists("/.dockerenv") or os.environ.get("RUNNING_IN_DOCKER") == "true"
        if self.llm_api_base and is_docker:
            for host in ("localhost", "127.0.0.1"):
                if host in self.llm_api_base:
                    new_base = self.llm_api_base.replace(host, "host.docker.internal")
                    print(
                        f"Docker detected: Automatically rewriting LLM_API_BASE from {self.llm_api_base} to {new_base}",
                        flush=True
                    )
                    self.llm_api_base = new_base
                    break
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        """Return CORS origins as a list, supporting comma-separated values."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_file_size_bytes(self) -> int:
        """Return the maximum file size in bytes."""
        return self.max_file_size_mb * 1024 * 1024


settings = Settings()
