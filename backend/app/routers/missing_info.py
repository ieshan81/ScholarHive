from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.missing_info import MissingInfoRequest
from app.utils import exclude_demo

router = APIRouter(prefix="/api/missing-info", tags=["missing-info"])


class AnswerBody(BaseModel):
    user_reply: str


@router.get("")
def list_missing_info(db: Session = Depends(get_db)):
    return exclude_demo(db.query(MissingInfoRequest), MissingInfoRequest).order_by(
        MissingInfoRequest.created_at.desc()
    ).all()


@router.post("/{request_id}/answer")
def record_answer(request_id: int, body: AnswerBody, db: Session = Depends(get_db)):
    req = db.query(MissingInfoRequest).filter(MissingInfoRequest.id == request_id).first()
    if not req:
        raise HTTPException(404, "Request not found")
    req.user_reply = body.user_reply
    req.status = "answered"
    req.answered_at = datetime.utcnow()
    db.commit()
    return req


@router.post("/{request_id}/save")
def save_to_vault(request_id: int, db: Session = Depends(get_db)):
    req = db.query(MissingInfoRequest).filter(MissingInfoRequest.id == request_id).first()
    if not req:
        raise HTTPException(404, "Request not found")
    req.status = "saved"
    db.commit()
    return {"message": "Marked saved — manually copy to Profile Vault or Story Bank", "request": req}


@router.post("/{request_id}/dismiss")
def dismiss(request_id: int, db: Session = Depends(get_db)):
    req = db.query(MissingInfoRequest).filter(MissingInfoRequest.id == request_id).first()
    if not req:
        raise HTTPException(404, "Request not found")
    req.status = "dismissed"
    db.commit()
    return {"message": "Dismissed"}
