"""Ieshan Memory Vault — unified profile intelligence API."""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.document import Document
from app.models.profile import Profile
from app.models.profile_graph import ProfileGraphNode
from app.models.story import Story
from app.services.document_extract import extract_text_from_file
from app.services.memory_vault import (
    approved_memories_text,
    bulk_approve_high_confidence,
    memory_overview,
    process_document,
)

router = APIRouter(prefix="/api/memory-vault", tags=["memory-vault"])


class PasteBody(BaseModel):
    text: str
    title: str = "Pasted content"
    source_type: str = "notes"


@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    settings = get_settings()
    return {
        **memory_overview(db),
        "storage": {
            "writable": settings.storage_writable,
            "path": settings.upload_storage_path,
            "warning": None if settings.storage_writable else "File uploads may fail — Railway volume not writable. Pasted text still works.",
        },
    }


@router.get("/documents")
def list_documents(db: Session = Depends(get_db)):
    return memory_overview(db)["documents"]


@router.get("/documents/{doc_id}")
def get_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    return {
        "id": doc.id,
        "file_name": doc.file_name,
        "original_filename": doc.original_filename,
        "file_type": doc.file_type,
        "source_type": doc.source_type,
        "extracted_text": doc.extracted_text,
        "extraction_status": doc.extraction_status,
        "processing_status": doc.processing_status,
        "extraction_error": doc.extraction_error,
        "storage_path": doc.storage_path,
    }


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    source_type: str = Form("other"),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    if not settings.storage_writable:
        raise HTTPException(
            503,
            "Storage not writable. Configure Railway volume at /data/uploads or use Paste text.",
        )

    original = file.filename or "upload"
    ext = (original.rsplit(".", 1)[-1] if "." in original else "txt").lower()
    if ext not in ("pdf", "txt", "docx", "md"):
        raise HTTPException(400, f"Unsupported file type: {ext}")

    content = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(400, f"File too large (max {settings.max_upload_mb}MB)")

    upload_dir = Path(settings.upload_storage_path)
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}.{ext}"
    dest = upload_dir / safe_name
    dest.write_bytes(content)

    text, err = extract_text_from_file(dest, ext)
    doc = Document(
        file_name=original,
        original_filename=original,
        file_type=ext,
        storage_path=str(dest),
        storage_url_or_path=str(dest),
        extracted_text=text if not err else None,
        extraction_status="completed" if text else "failed",
        extraction_error=err,
        processing_status="uploaded",
        source_type=source_type,
        status="uploaded",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    if text:
        result = await process_document(db, doc.id)
        return {"document_id": doc.id, "upload": "ok", "extraction": doc.extraction_status, "memory": result}

    return {
        "document_id": doc.id,
        "upload": "ok",
        "extraction": doc.extraction_status,
        "error": err,
        "message": err or "Uploaded — no text extracted",
    }


@router.post("/paste")
async def paste_text(body: PasteBody, db: Session = Depends(get_db)):
    if len(body.text.strip()) < 40:
        raise HTTPException(400, "Paste at least 40 characters of content")

    doc = Document(
        file_name=body.title[:500],
        original_filename=body.title[:500],
        file_type="txt",
        extracted_text=body.text[:200000],
        extraction_status="completed",
        processing_status="uploaded",
        source_type=body.source_type,
        status="uploaded",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    result = await process_document(db, doc.id)
    return {"document_id": doc.id, "memory": result}


@router.post("/documents/{doc_id}/process")
async def process_doc(doc_id: int, db: Session = Depends(get_db)):
    return await process_document(db, doc_id)


@router.post("/documents/{doc_id}/reprocess")
async def reprocess_doc(doc_id: int, db: Session = Depends(get_db)):
    return await process_document(db, doc_id)


@router.get("/clusters")
def clusters(db: Session = Depends(get_db)):
    return memory_overview(db)["clusters"]


@router.get("/conflicts")
def conflicts(db: Session = Depends(get_db)):
    rows = db.query(ProfileGraphNode).filter(
        (ProfileGraphNode.status == "conflict") | (ProfileGraphNode.conflict_flag.isnot(None))
    ).all()
    return [{"id": n.id, "title": n.title, "conflict_flag": n.conflict_flag, "status": n.status} for n in rows]


@router.post("/nodes/{node_id}/confirm")
def confirm_node(node_id: int, db: Session = Depends(get_db)):
    node = db.query(ProfileGraphNode).filter(ProfileGraphNode.id == node_id).first()
    if not node:
        raise HTTPException(404, "Not found")
    node.status = "user_confirmed"
    node.approved_by_user = True
    node.conflict_flag = None
    db.commit()
    return {"message": "Confirmed"}


@router.post("/nodes/{node_id}/reject")
def reject_node(node_id: int, db: Session = Depends(get_db)):
    node = db.query(ProfileGraphNode).filter(ProfileGraphNode.id == node_id).first()
    if not node:
        raise HTTPException(404, "Not found")
    node.status = "rejected"
    db.commit()
    return {"message": "Rejected"}


@router.post("/bulk-approve-high-confidence")
def bulk_approve(db: Session = Depends(get_db)):
    return bulk_approve_high_confidence(db)


@router.get("/approved-text")
def approved_text(db: Session = Depends(get_db)):
    return {"text": approved_memories_text(db)}


@router.get("/basic-profile")
def basic_profile(db: Session = Depends(get_db)):
    p = db.query(Profile).filter(Profile.id == 1).first()
    if not p:
        return {}
    return {
        "university": p.university,
        "major": p.major,
        "gpa": p.gpa,
        "international_student": p.international_student,
        "personal_details": p.personal_details,
        "education": p.education,
        "achievements": p.achievements,
        "projects": p.projects,
        "career_goals": p.career_goals,
    }


@router.post("/sync-legacy")
def sync_legacy(db: Session = Depends(get_db)):
    """Import Story Bank entries into memory nodes (one-time friendly)."""
    from app.services.memory_extraction import make_canonical_key
    from app.services.memory_vault import ingest_memory_items

    stories = db.query(Story).filter(Story.is_demo.is_(False)).all()
    items = []
    for s in stories:
        items.append({
            "node_type": "personal_story",
            "title": s.title,
            "summary": s.summary or (s.full_story or "")[:500],
            "details": s.full_story,
            "source_excerpt": (s.summary or s.full_story or "")[:800],
            "confidence": 0.9 if s.verified_by_user else 0.7,
            "canonical_key": make_canonical_key("personal_story", s.title, s.summary or ""),
            "sensitive": False,
            "needs_review": not s.verified_by_user,
        })
    stats = ingest_memory_items(db, items, None)
    return {"message": f"Synced {len(stories)} stories", **stats}
