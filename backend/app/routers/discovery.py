from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.discovery import DiscoveryRun, DiscoveryCandidate
from app.services.discovery_pipeline import process_candidate

router = APIRouter(prefix="/api/discovery", tags=["discovery"])


@router.get("/runs")
def list_runs(db: Session = Depends(get_db), limit: int = 20):
    runs = db.query(DiscoveryRun).order_by(DiscoveryRun.started_at.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "source_type": r.source_type,
            "query_or_label": r.query_or_label,
            "status": r.status,
            "total_candidates": r.total_candidates,
            "opportunities_saved": r.opportunities_saved,
            "duplicates_skipped": r.duplicates_skipped,
            "rejected_count": r.rejected_count,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
        }
        for r in runs
    ]


@router.get("/candidates")
def list_candidates(db: Session = Depends(get_db), run_id: int | None = None, limit: int = 50):
    q = db.query(DiscoveryCandidate).order_by(DiscoveryCandidate.created_at.desc())
    if run_id:
        q = q.filter(DiscoveryCandidate.run_id == run_id)
    rows = q.limit(limit).all()
    return [
        {
            "id": c.id,
            "run_id": c.run_id,
            "source_type": c.source_type,
            "title": c.title,
            "source_url": c.source_url,
            "domain": c.domain,
            "classification": c.classification,
            "classification_confidence": c.classification_confidence,
            "classification_reason": c.classification_reason,
            "extraction_status": c.extraction_status,
            "reject_reason": c.reject_reason,
            "linked_scholarship_id": c.linked_scholarship_id,
        }
        for c in rows
    ]


@router.post("/candidates/{candidate_id}/reject")
async def reject_candidate(candidate_id: int, db: Session = Depends(get_db)):
    cand = db.query(DiscoveryCandidate).filter(DiscoveryCandidate.id == candidate_id).first()
    if not cand:
        return {"message": "Not found"}
    cand.extraction_status = "rejected"
    cand.reject_reason = "Manually rejected"
    db.commit()
    return {"message": "Rejected"}
