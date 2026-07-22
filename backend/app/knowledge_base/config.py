"""
Centralized Knowledge Base upload configuration.

This module is the single authoritative source for upload limits and
supported document formats. Every upload endpoint (create/replace) validates
against these values, and `/api/knowledge-base/config` exposes them so the
frontend never has to hardcode or duplicate them.
"""

from __future__ import annotations

from app.config import settings
from fastapi import HTTPException

# Lowercase extensions without the leading dot — this is also the exact
# shape returned by the `/config` endpoint's `supported_formats` field.
SUPPORTED_FORMATS: tuple[str, ...] = ("pdf", "docx", "md", "txt")
SUPPORTED_FORMATS_LABEL = "PDF, DOCX, Markdown, TXT"

ALLOWED_EXTENSIONS = {f".{extension}" for extension in SUPPORTED_FORMATS}

MAX_UPLOAD_MB = settings.KNOWLEDGE_BASE_MAX_UPLOAD_MB
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024


def validate_upload(
    safe_file_name: str, file_name: str, extension: str, content: bytes
) -> None:
    """Validates an uploaded file against the shared Knowledge Base rules.

    Raises `HTTPException` with a clear, business-friendly message on the
    first rule that fails. Shared by both the create and replace endpoints
    so validation never drifts between the two.
    """
    if not safe_file_name or safe_file_name != file_name:
        raise HTTPException(
            status_code=400, detail="Upload a file with a valid filename."
        )
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=(
                "This file type isn't supported. "
                "Please upload a PDF, DOCX, Markdown, or TXT file."
            ),
        )
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"The selected file exceeds the {MAX_UPLOAD_MB} MB upload limit.",
        )
