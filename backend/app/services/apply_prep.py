"""Apply Preparation — gathers materials for human review; never auto-submits."""
from sqlalchemy.orm import Session
from app.models.scholarship import Scholarship
from app.models.essay import Essay
from app.models.profile import Profile
from app.models.document import Document


def prepare_application(db: Session, scholarship_id: int) -> dict:
    sch = db.query(Scholarship).filter(Scholarship.id == scholarship_id).first()
    if not sch:
        return {"error": "Scholarship not found"}

    profile = db.query(Profile).filter(Profile.id == 1).first()
    essay = (
        db.query(Essay)
        .filter(Essay.scholarship_id == scholarship_id)
        .order_by(Essay.updated_at.desc())
        .first()
    )
    docs = db.query(Document).filter(Document.related_scholarship_id == scholarship_id).all()

    warnings = [
        "Human approval required before any submission",
        "ScholarHive AI does not auto-submit applications",
    ]
    manual_steps = []
    if sch.status in ("manual_step_needed",) or "portal" in (sch.source_url or "").lower():
        manual_steps.append("Portal may require login, CAPTCHA, or signature — complete manually")
    if sch.essay_required and (not essay or essay.status != "approved"):
        warnings.append("Essay not approved — review in Essay Studio first")
    if not profile:
        warnings.append("Profile Vault incomplete")

    return {
        "scholarship_id": sch.id,
        "scholarship_name": sch.name,
        "source_url": sch.source_url,
        "status": sch.status,
        "profile_summary": {
            "university": profile.university if profile else None,
            "major": profile.major if profile else None,
            "gpa": profile.gpa if profile else None,
        },
        "essay_final_text": (essay.final_text or essay.draft_text) if essay else None,
        "essay_status": essay.status if essay else None,
        "required_documents": sch.required_documents,
        "documents_checklist": [
            {"file_name": d.file_name, "file_type": d.file_type, "status": d.status}
            for d in docs
        ],
        "eligibility_score": sch.eligibility_score,
        "notes": sch.eligibility_notes,
        "manual_steps_required": manual_steps,
        "warnings": warnings,
        "human_approval_required": True,
    }
