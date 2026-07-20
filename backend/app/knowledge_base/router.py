from __future__ import annotations

import io
import uuid
from pathlib import Path

from app.database import get_session
from app.knowledge_base.manager import IngestionRejectedError, KnowledgeBaseManager
from app.models import User
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/knowledge-base", tags=["Knowledge Base"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".md", ".txt"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024


def extract_document_text(file_name: str, content: bytes) -> str:
    extension = Path(file_name).suffix.lower()

    if extension in {".md", ".txt"}:
        try:
            return content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("Text files must use UTF-8 encoding.") from exc

    if extension == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)

    if extension == ".docx":
        from docx import Document

        document = Document(io.BytesIO(content))
        return "\n\n".join(paragraph.text for paragraph in document.paragraphs)

    raise ValueError("Unsupported document type.")


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_knowledge_base(
    business_id: uuid.UUID,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    file_name = file.filename or ""
    safe_file_name = Path(file_name).name
    extension = Path(safe_file_name).suffix.lower()

    if not safe_file_name or safe_file_name != file_name:
        raise HTTPException(
            status_code=400, detail="Upload a file with a valid filename."
        )
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415, detail="Only PDF, DOCX, MD, and TXT files are supported."
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413, detail="Knowledge-base files must be 10 MB or smaller."
        )

    business_exists = await session.scalar(
        select(User.id).where(User.id == business_id)
    )
    if business_exists is None:
        raise HTTPException(status_code=404, detail="Business not found.")

    try:
        extracted_text = extract_document_text(safe_file_name, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail="The document could not be read."
        ) from exc

    if not extracted_text.strip():
        raise HTTPException(
            status_code=400, detail="The document contains no readable text."
        )

    manager = KnowledgeBaseManager(session)
    document_path = manager.resolver.resolve_within_tenant(business_id, safe_file_name)
    previous_text = (
        document_path.read_text(encoding="utf-8") if document_path.exists() else None
    )
    document_path.write_text(extracted_text, encoding="utf-8")

    try:
        chunks = await manager.ingest_document(business_id, safe_file_name)
        await session.commit()
    except IngestionRejectedError as exc:
        await session.rollback()
        _restore_document(document_path, previous_text)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        await session.rollback()
        _restore_document(document_path, previous_text)
        raise

    return {
        "message": f"{safe_file_name} uploaded and indexed successfully.",
        "file_name": safe_file_name,
        "chunks_indexed": len(chunks),
    }


def _restore_document(path: Path, previous_text: str | None) -> None:
    if previous_text is None:
        path.unlink(missing_ok=True)
    else:
        path.write_text(previous_text, encoding="utf-8")
