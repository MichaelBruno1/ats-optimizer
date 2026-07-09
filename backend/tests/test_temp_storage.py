"""Unit tests for the temporary storage and session cleanup service."""

import os
import time
import asyncio
import pytest
from pathlib import Path
from unittest.mock import patch

from app.config import settings
from app.services.temp_storage import (
    create_session,
    get_session_dir,
    get_pdf_path,
    session_exists,
    delete_session,
    register_queue,
    get_queue,
    deregister_queue,
    cleanup_old_sessions,
)


def test_session_lifecycle(temp_dir: Path, monkeypatch) -> None:
    """Test session creation, retrieval, and deletion lifecycle."""
    monkeypatch.setattr(settings, "temp_dir", str(temp_dir))

    # Create session
    session_id = create_session()
    assert len(session_id) == 32
    assert session_exists(session_id)

    # Get directory path and check PDF naming
    session_dir = get_session_dir(session_id)
    assert session_dir.exists()
    assert get_pdf_path(session_id, 0) == session_dir / "resume_0.pdf"

    # Delete session
    delete_session(session_id)
    assert not session_exists(session_id)
    assert not session_dir.exists()


def test_queue_registry() -> None:
    """Test queue registration, retrieval, and deregistration."""
    session_id = "test_queue_session"
    
    queue = register_queue(session_id)
    assert isinstance(queue, asyncio.Queue)
    
    assert get_queue(session_id) is queue
    
    deregister_queue(session_id)
    assert get_queue(session_id) is None


@pytest.mark.asyncio
async def test_cleanup_old_sessions(temp_dir: Path, monkeypatch) -> None:
    """Test that cleanup task removes expired session folders but keeps fresh ones."""
    monkeypatch.setattr(settings, "temp_dir", str(temp_dir))
    monkeypatch.setattr(settings, "temp_cleanup_minutes", 10)  # 10 minutes = 600s

    # Create two session directories
    old_dir = temp_dir / "old_expired_session"
    old_dir.mkdir()
    new_dir = temp_dir / "new_active_session"
    new_dir.mkdir()

    # Modify modification timestamps
    now = time.time()
    # Expired 20 minutes ago (1200 seconds)
    os.utime(old_dir, (now - 1200, now - 1200))
    # Fresh (current time)
    os.utime(new_dir, (now, now))

    # Execute cleanup old sessions loop once by letting sleep succeed once, then raise CancelledError
    with patch("app.services.temp_storage.asyncio.sleep") as mock_sleep:
        mock_sleep.side_effect = [None, asyncio.CancelledError("Exiting loop")]
        
        with pytest.raises(asyncio.CancelledError, match="Exiting loop"):
            await cleanup_old_sessions()

    # Verify results
    assert not old_dir.exists(), "Expired session folder was not cleaned up."
    assert new_dir.exists(), "Active session folder was incorrectly cleaned up."
