"""Background jobs — MVP uses manual triggers only."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.profile import Profile
from app.models.scholarship import Scholarship
from app.services.eligibility import evaluate_eligibility, apply_eligibility_to_scholarship
from app.services import gmail as gmail_service

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("/recalculate-eligibility")
def recalculate_eligibility(db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.id == 1).first()
    from app.utils import exclude_demo
    scholarships = exclude_demo(db.query(Scholarship), Scholarship).all()
    count = 0
    for sch in scholarships:
        result = evaluate_eligibility(profile, sch)
        apply_eligibility_to_scholarship(sch, result)
        count += 1
    db.commit()
    return {"message": f"Recalculated eligibility for {count} scholarships"}


@router.post("/scan-gmail")
async def job_scan_gmail(db: Session = Depends(get_db)):
    return await gmail_service.scan_gmail(db)
