from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.document import Document
from app.utils import exclude_demo

router = APIRouter(prefix="/api/documents", tags=["documents"])


class DocumentCreate(BaseModel):
    file_name: str
    file_type: str
    storage_url_or_path: str | None = None
    status: str = "missing"
    related_scholarship_id: int | None = None


class DocumentUpdate(BaseModel):
    file_name: str | None = None
    file_type: str | None = None
    storage_url_or_path: str | None = None
    status: str | None = None
    related_scholarship_id: int | None = None


@router.get("")
def list_documents(db: Session = Depends(get_db)):
    return exclude_demo(db.query(Document), Document).order_by(Document.updated_at.desc()).all()


@router.post("")
def create_document(data: DocumentCreate, db: Session = Depends(get_db)):
    doc = Document(**data.model_dump())
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.put("/{doc_id}")
def update_document(doc_id: int, data: DocumentUpdate, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(doc, key, value)
    db.commit()
    db.refresh(doc)
    return doc


@router.delete("/{doc_id}")
def delete_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    db.delete(doc)
    db.commit()
    return {"message": "Document deleted"}
