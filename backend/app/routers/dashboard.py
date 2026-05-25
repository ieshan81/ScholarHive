from datetime import date, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db, check_database_connection
from app.models.scholarship import Scholarship
from app.models.essay import Essay
from app.models.missing_info import MissingInfoRequest

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    scholarships = db.query(Scholarship).all()
    essays = db.query(Essay).all()
    missing = db.query(MissingInfoRequest).filter(MissingInfoRequest.status == "pending").all()
    week_ago = date.today() - timedelta(days=7)

    return {
        "database_connected": check_database_connection(),
        "new_opportunities": len([s for s in scholarships if s.status == "found"]),
        "eligible_opportunities": len([s for s in scholarships if s.status == "eligible"]),
        "drafts_ready": len([s for s in scholarships if s.status == "draft_ready"]),
        "missing_info_requests": len(missing),
        "applications_needs_review": len([s for s in scholarships if s.status == "needs_review"]),
        "submitted_this_week": len([
            s for s in scholarships
            if s.status == "submitted" and s.updated_at and s.updated_at.date() >= week_ago
        ]),
        "won_count": len([s for s in scholarships if s.status == "won"]),
        "upcoming_deadlines": [
            {"id": s.id, "name": s.name, "deadline": str(s.deadline)}
            for s in scholarships
            if s.deadline and s.deadline >= date.today()
        ][:5],
        "essay_count": len(essays),
        "total_scholarships": len(scholarships),
    }
