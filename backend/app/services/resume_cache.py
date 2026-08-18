"""Resume Cache Service.

Provides deterministic SHA-256 caching for structured resume analysis.
Stores both the raw text (ground truth) and parsed structured domain models
to eliminate redundant LLM parsing calls when a user evaluates multiple job vacancies.
"""

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Optional, Tuple

from app.api.schemas import ResumeAnalysis
from app.config import settings
from app.domain.resume import StructuredResume

logger = logging.getLogger(__name__)


class ResumeCacheService:
    """Manages disk-backed caching of structured resume extractions."""

    @staticmethod
    def _get_cache_dir() -> Path:
        cache_dir = Path(settings.temp_dir) / ".cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    @staticmethod
    def compute_hash(resume_text: str) -> str:
        """Calculate SHA-256 hex digest of normalized resume text."""
        normalized = " ".join(resume_text.strip().split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @classmethod
    def get(cls, resume_text: str) -> Optional[Tuple[StructuredResume, ResumeAnalysis]]:
        """Retrieve cached structured resume and analysis by resume content hash.

        Returns None on cache miss or expired TTL.
        """
        if not resume_text or not resume_text.strip():
            return None

        h = cls.compute_hash(resume_text)
        cache_file = cls._get_cache_dir() / f"{h}.json"

        if not cache_file.exists():
            return None

        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            created_at = data.get("created_at", 0)
            ttl_seconds = settings.cache_ttl_hours * 3600

            if time.time() - created_at > ttl_seconds:
                logger.info("Resume cache expired for hash %s (age > %d hours)", h[:10], settings.cache_ttl_hours)
                cache_file.unlink(missing_ok=True)
                return None

            structured_resume = StructuredResume.model_validate(data["structured_resume"])
            resume_analysis = ResumeAnalysis.model_validate(data["resume_analysis"])

            logger.info("Resume cache HIT for hash %s", h[:10])
            return structured_resume, resume_analysis
        except Exception as exc:
            logger.warning("Failed to read resume cache file %s: %s", cache_file, exc)
            return None

    @classmethod
    def set(
        cls,
        resume_text: str,
        structured_resume: StructuredResume,
        resume_analysis: ResumeAnalysis,
    ) -> None:
        """Store raw text, structured resume, and analysis in cache."""
        if not resume_text or not resume_text.strip():
            return

        h = cls.compute_hash(resume_text)
        cache_file = cls._get_cache_dir() / f"{h}.json"

        payload = {
            "hash": h,
            "created_at": time.time(),
            "original_text": resume_text,
            "structured_resume": structured_resume.model_dump(),
            "resume_analysis": resume_analysis.model_dump(),
        }

        try:
            cache_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info("Resume stored in cache with hash %s", h[:10])
        except Exception as exc:
            logger.warning("Failed to write resume cache file %s: %s", cache_file, exc)

    @classmethod
    def cleanup_expired(cls) -> int:
        """Remove cache files older than CACHE_TTL_HOURS."""
        cache_dir = cls._get_cache_dir()
        if not cache_dir.exists():
            return 0

        now = time.time()
        ttl_seconds = settings.cache_ttl_hours * 3600
        removed = 0

        for f in cache_dir.glob("*.json"):
            try:
                if now - f.stat().st_mtime > ttl_seconds:
                    f.unlink(missing_ok=True)
                    removed += 1
            except Exception:
                pass

        if removed > 0:
            logger.info("Cleaned up %d expired resume cache entries.", removed)
        return removed
