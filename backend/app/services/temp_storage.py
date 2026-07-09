"""Temporary storage management for per-session files.

Each processing session gets an isolated directory under TEMP_DIR.
A background cleanup task periodically removes directories older than
TEMP_CLEANUP_MINUTES to prevent disk exhaustion.
"""

import asyncio
import logging
import shutil
import time
import uuid
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

# ── In-memory session-to-queue registry for SSE progress streaming ─────────
_progress_queues: dict[str, asyncio.Queue] = {}


# ─────────────────────────────────────────────────────────────────────────────
# Session directory helpers
# ─────────────────────────────────────────────────────────────────────────────


def create_session() -> str:
    """Create a new unique session ID and its temporary directory.

    Returns:
        The generated session ID (UUID4 hex string).
    """
    session_id = uuid.uuid4().hex
    session_dir = get_session_dir(session_id)
    session_dir.mkdir(parents=True, exist_ok=True)
    logger.debug("Created session directory: %s", session_dir)
    return session_id


def get_session_dir(session_id: str) -> Path:
    """Return the Path for a given session's temporary directory.

    Args:
        session_id: The session identifier returned by ``create_session``.

    Returns:
        Resolved Path object for the session directory.
    """
    return Path(settings.temp_dir) / session_id


def get_pdf_path(session_id: str, job_index: int) -> Path:
    """Return the expected Path for an optimized PDF file.

    Args:
        session_id: The session identifier.
        job_index: Index of the job (0-based) or -1 for single mode.

    Returns:
        Path where the PDF will be / was saved.
    """
    return get_session_dir(session_id) / f"resume_{job_index}.pdf"


def session_exists(session_id: str) -> bool:
    """Check whether a session directory currently exists on disk.

    Args:
        session_id: The session identifier to check.

    Returns:
        True if the directory exists, False otherwise.
    """
    return get_session_dir(session_id).is_dir()


def delete_session(session_id: str) -> None:
    """Immediately delete a session's temporary directory and deregister its queue.

    Args:
        session_id: The session identifier to clean up.
    """
    session_dir = get_session_dir(session_id)
    if session_dir.exists():
        shutil.rmtree(session_dir, ignore_errors=True)
        logger.debug("Deleted session directory: %s", session_dir)
    _progress_queues.pop(session_id, None)


# ─────────────────────────────────────────────────────────────────────────────
# SSE queue management
# ─────────────────────────────────────────────────────────────────────────────


def register_queue(session_id: str) -> asyncio.Queue:
    """Create and register an asyncio Queue for SSE progress events.

    Args:
        session_id: The session identifier.

    Returns:
        The newly created asyncio.Queue bound to this session.
    """
    queue: asyncio.Queue = asyncio.Queue()
    _progress_queues[session_id] = queue
    return queue


def get_queue(session_id: str) -> asyncio.Queue | None:
    """Retrieve the SSE progress queue for a session.

    Args:
        session_id: The session identifier.

    Returns:
        The asyncio.Queue if found, None otherwise.
    """
    return _progress_queues.get(session_id)


def deregister_queue(session_id: str) -> None:
    """Remove the SSE progress queue for a session.

    Args:
        session_id: The session identifier to deregister.
    """
    _progress_queues.pop(session_id, None)


# ─────────────────────────────────────────────────────────────────────────────
# Background cleanup task
# ─────────────────────────────────────────────────────────────────────────────


async def cleanup_old_sessions() -> None:
    """Periodically remove session directories older than TEMP_CLEANUP_MINUTES.

    This coroutine runs in a continuous loop and is intended to be launched
    as an asyncio background task during application startup.
    """
    base_dir = Path(settings.temp_dir)
    interval_seconds = max(settings.temp_cleanup_minutes * 60 // 2, 60)
    max_age_seconds = settings.temp_cleanup_minutes * 60

    logger.info(
        "Cleanup task started — interval=%ds, max_age=%ds",
        interval_seconds,
        max_age_seconds,
    )

    while True:
        await asyncio.sleep(interval_seconds)
        now = time.time()

        if not base_dir.exists():
            continue

        for session_dir in base_dir.iterdir():
            if not session_dir.is_dir():
                continue
            try:
                age = now - session_dir.stat().st_mtime
                if age > max_age_seconds:
                    shutil.rmtree(session_dir, ignore_errors=True)
                    logger.info("Cleaned up expired session: %s", session_dir.name)
            except OSError as exc:
                logger.warning("Failed to inspect/remove %s: %s", session_dir, exc)
