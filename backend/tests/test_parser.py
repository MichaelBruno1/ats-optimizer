"""Unit tests for the document_parser service.

Tests cover:
- Plain text (.txt) extraction
- Unsupported format rejection
- File-too-large rejection
"""

import io
import pytest

from app.services.document_parser import (
    DocumentParseError,
    FileTooLargeError,
    UnsupportedFormatError,
    extract_text_from_bytes,
)


# ─────────────────────────────────────────────────────────────────────────────
# TXT extraction
# ─────────────────────────────────────────────────────────────────────────────


class TestExtractTxt:
    """Tests for plain text file extraction."""

    def test_extract_utf8_text(self) -> None:
        """Should extract and return clean UTF-8 text content."""
        content = "John Doe\nSoftware Engineer\n5 years experience".encode("utf-8")
        result = extract_text_from_bytes(content, "resume.txt")
        assert "John Doe" in result
        assert "Software Engineer" in result

    def test_extract_latin1_fallback(self) -> None:
        """Should fall back to latin-1 decoding when UTF-8 fails."""
        # ñ in latin-1 is 0xF1, which is invalid UTF-8
        content = "Candidato: Jos\xe9 Silva\nEngenheiro".encode("latin-1")
        result = extract_text_from_bytes(content, "resume.txt")
        assert "Silva" in result
        assert "Engenheiro" in result

    def test_empty_txt_raises_parse_error(self) -> None:
        """An empty TXT file should raise DocumentParseError."""
        with pytest.raises(DocumentParseError, match="empty"):
            extract_text_from_bytes(b"   \n  ", "resume.txt")

    def test_whitespace_only_raises_parse_error(self) -> None:
        """A whitespace-only TXT file should raise DocumentParseError."""
        with pytest.raises(DocumentParseError):
            extract_text_from_bytes(b"\t\n\r\n", "resume.txt")


# ─────────────────────────────────────────────────────────────────────────────
# Format validation
# ─────────────────────────────────────────────────────────────────────────────


class TestFormatValidation:
    """Tests for unsupported file format rejection."""

    def test_unsupported_extension_raises_error(self) -> None:
        """An unsupported extension (.odt) should raise UnsupportedFormatError."""
        content = b"some content"
        with pytest.raises(UnsupportedFormatError) as exc_info:
            extract_text_from_bytes(content, "resume.odt")
        assert ".odt" in str(exc_info.value)

    def test_exe_extension_raises_error(self) -> None:
        """A binary .exe extension should raise UnsupportedFormatError."""
        content = b"MZ\x90\x00"  # EXE magic bytes
        with pytest.raises(UnsupportedFormatError):
            extract_text_from_bytes(content, "malicious.exe")

    def test_no_extension_raises_error(self) -> None:
        """A file without an extension should raise UnsupportedFormatError."""
        with pytest.raises(UnsupportedFormatError):
            extract_text_from_bytes(b"data", "resume")

    def test_pdf_extension_accepted(self) -> None:
        """A .pdf extension should be accepted (may fail at parse, not format check)."""
        # This should raise DocumentParseError (bad PDF), not UnsupportedFormatError
        with pytest.raises((DocumentParseError, Exception)) as exc_info:
            extract_text_from_bytes(b"not a real pdf", "resume.pdf")
        assert not isinstance(exc_info.value, UnsupportedFormatError)

    def test_docx_extension_accepted(self) -> None:
        """A .docx extension should be accepted (may fail at parse, not format check)."""
        with pytest.raises((DocumentParseError, Exception)) as exc_info:
            extract_text_from_bytes(b"not a real docx", "resume.docx")
        assert not isinstance(exc_info.value, UnsupportedFormatError)


# ─────────────────────────────────────────────────────────────────────────────
# File size validation (uses async upload function via mock)
# ─────────────────────────────────────────────────────────────────────────────


class TestSizeValidation:
    """Tests for file size limits via the async upload interface."""

    @pytest.mark.asyncio
    async def test_oversized_file_raises_error(self) -> None:
        """A file exceeding MAX_FILE_SIZE_MB should raise FileTooLargeError."""
        from unittest.mock import AsyncMock, MagicMock

        from app.config import settings
        from app.services.document_parser import extract_text_from_upload

        oversized_bytes = b"x" * (settings.max_file_size_bytes + 1)

        mock_upload = MagicMock()
        mock_upload.filename = "big_resume.txt"
        mock_upload.read = AsyncMock(return_value=oversized_bytes)

        with pytest.raises(FileTooLargeError) as exc_info:
            await extract_text_from_upload(mock_upload)

        assert "MB" in str(exc_info.value)
        assert str(settings.max_file_size_mb) in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_valid_size_file_proceeds_to_extraction(self) -> None:
        """A file within size limits should proceed to text extraction."""
        from unittest.mock import AsyncMock, MagicMock

        from app.services.document_parser import extract_text_from_upload

        valid_bytes = b"John Doe\nSoftware Engineer"

        mock_upload = MagicMock()
        mock_upload.filename = "resume.txt"
        mock_upload.read = AsyncMock(return_value=valid_bytes)

        result = await extract_text_from_upload(mock_upload)
        assert "John Doe" in result
