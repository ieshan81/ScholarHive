from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.profile import Profile
from app.models.scholarship import Scholarship
from app.schemas.scholarship import (
    ScholarshipCreate,
    ScholarshipUpdate,
    ScholarshipResponse,
    ScholarshipMoveStatus,
    EligibilityResult,
)
from app.services.eligibility import evaluate_eligibility, apply_eligibility_to_scholarship
from app.services.apply_prep import prepare_application
from app.utils import exclude_demo, filter_radar_scholarships
from app.services.discovery_classifier import classify_candidate
import re

router = APIRouter(prefix="/api/scholarships", tags=["scholarships"])

FILTERS = {
    "eligible": ["eligible"],
    "maybe_eligible": ["maybe_eligible"],
    "not_eligible": ["not_eligible"],
    "deadline_soon": None,
    "mechanical_engineering": None,
    "international_students": None,
    "no_essay": None,
    "high_award": None,
    "low_effort": None,
}


@router.get("", response_model=list[ScholarshipResponse])
def list_scholarships(
    filter: str | None = Query(None, alias="filter"),
    include_leads: bool = Query(False),
    review_only: bool = Query(False),
    db: Session = Depends(get_db),
):
    q = filter_radar_scholarships(
        exclude_demo(db.query(Scholarship), Scholarship),
        include_leads=include_leads,
        review_only=review_only,
    ).order_by(Scholarship.priority_score.desc())
    items = q.all()
    if not filter:
        return items
    if filter == "eligible":
        return [s for s in items if s.status == "eligible"]
    if filter == "maybe_eligible":
        return [s for s in items if s.status == "maybe_eligible"]
    if filter == "not_eligible":
        return [s for s in items if s.status == "not_eligible"]
    if filter == "deadline_soon":
        soon = date.today() + timedelta(days=30)
        return [s for s in items if s.deadline and s.deadline <= soon]
    if filter == "mechanical_engineering":
        return [s for s in items if s.major_requirement and "mechanical" in s.major_requirement.lower()]
    if filter == "international_students":
        return [s for s in items if s.international_allowed in ("yes", "unknown")]
    if filter == "no_essay":
        return [s for s in items if not s.essay_required]
    if filter == "high_award":
        return [s for s in items if s.award_amount and any(c in (s.award_amount or "") for c in ["$5", "$10", "000"])]
    if filter == "low_effort":
        return [s for s in items if s.effort_score <= 40]
    return items


@router.post("", response_model=ScholarshipResponse)
def create_scholarship(data: ScholarshipCreate, db: Session = Depends(get_db)):
    sch = Scholarship(**data.model_dump())
    db.add(sch)
    db.commit()
    db.refresh(sch)
    return sch


@router.get("/{scholarship_id}", response_model=ScholarshipResponse)
def get_scholarship(scholarship_id: int, db: Session = Depends(get_db)):
    sch = db.query(Scholarship).filter(Scholarship.id == scholarship_id).first()
    if not sch:
        raise HTTPException(404, "Scholarship not found")
    return sch


@router.put("/{scholarship_id}", response_model=ScholarshipResponse)
def update_scholarship(scholarship_id: int, data: ScholarshipUpdate, db: Session = Depends(get_db)):
    sch = db.query(Scholarship).filter(Scholarship.id == scholarship_id).first()
    if not sch:
        raise HTTPException(404, "Scholarship not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(sch, key, value)
    sch.user_edited = True
    db.commit()
    db.refresh(sch)
    return sch


@router.post("/{scholarship_id}/evaluate", response_model=EligibilityResult)
def evaluate_scholarship(scholarship_id: int, db: Session = Depends(get_db)):
    sch = db.query(Scholarship).filter(Scholarship.id == scholarship_id).first()
    if not sch:
        raise HTTPException(404, "Scholarship not found")
    profile = db.query(Profile).filter(Profile.id == 1).first()
    result = evaluate_eligibility(profile, sch)
    apply_eligibility_to_scholarship(sch, result)
    sch.next_action = "Review eligibility" if result["status_recommendation"] != "not_eligible" else "Archive or skip"
    db.commit()
    return EligibilityResult(**result)


@router.post("/{scholarship_id}/move-status", response_model=ScholarshipResponse)
def move_status(scholarship_id: int, data: ScholarshipMoveStatus, db: Session = Depends(get_db)):
    sch = db.query(Scholarship).filter(Scholarship.id == scholarship_id).first()
    if not sch:
        raise HTTPException(404, "Scholarship not found")
    sch.status = data.status
    if data.next_action:
        sch.next_action = data.next_action
    db.commit()
    db.refresh(sch)
    return sch


@router.get("/{scholarship_id}/apply-prep")
def apply_preparation(scholarship_id: int, db: Session = Depends(get_db)):
    return prepare_application(db, scholarship_id)


class RejectBody(BaseModel):
    reason: str = "Manually rejected"
    status: str = "rejected"


@router.post("/{scholarship_id}/reject")
def reject_scholarship(scholarship_id: int, body: RejectBody, db: Session = Depends(get_db)):
    sch = db.query(Scholarship).filter(Scholarship.id == scholarship_id).first()
    if not sch:
        raise HTTPException(404, "Scholarship not found")
    sch.status = body.status
    sch.reject_reason = body.reason
    db.commit()
    return {"message": "Rejected", "id": sch.id}


@router.post("/mark-suspects-review")
def mark_suspects_review(db: Session = Depends(get_db)):
    """Flag likely bad imports (listicles, Gmail junk) for user review — does not delete."""
    items = exclude_demo(db.query(Scholarship), Scholarship).all()
    marked = 0
    for sch in items:
        cls, _, reason = classify_candidate(sch.name, sch.eligibility_notes or "")
        if cls in ("scholarship_database_page", "irrelevant", "loan", "spam") or "[Gmail]" in (sch.name or ""):
            if sch.status not in ("rejected", "submitted", "won"):
                sch.status = "needs_review"
                sch.reject_reason = reason or "Suspect import — review required"
                sch.classification = cls
                marked += 1
        elif re.search(r"\b\d{2,4}\+?\s+scholarships\b", sch.name or "", re.I):
            sch.status = "needs_review"
            sch.reject_reason = "List/database style title"
            sch.classification = "scholarship_database_page"
            marked += 1
    db.commit()
    return {"message": f"Marked {marked} records for review", "marked": marked}
