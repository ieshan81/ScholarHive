from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.essay import Essay
from app.models.scholarship import Scholarship
from app.models.profile import Profile
from app.models.story import Story
from app.models.missing_info import MissingInfoRequest
from app.schemas.essay import (
    EssayResponse,
    EssayUpdate,
    EssayGenerateRequest,
    EssayReviewResponse,
)
from app.services.gemini import generate_essay_draft
from app.services.authenticity import review_essay, rewrite_essay_section
from app.utils import exclude_demo

router = APIRouter(prefix="/api/essays", tags=["essays"])


def _profile_text(profile: Profile | None) -> str:
    if not profile:
        return ""
    parts = [
        profile.personal_details, profile.education, profile.university,
        profile.major, profile.achievements, profile.projects, profile.career_goals,
    ]
    return "\n".join(p for p in parts if p)


def _stories_text(db: Session) -> str:
    stories = exclude_demo(
        db.query(Story).filter(Story.verified_by_user.is_(True)),
        Story,
    ).all()
    return "\n\n".join(f"{s.title}: {s.summary or s.full_story}" for s in stories)


@router.get("", response_model=list[EssayResponse])
def list_essays(db: Session = Depends(get_db)):
    return exclude_demo(db.query(Essay), Essay).order_by(Essay.updated_at.desc()).all()


@router.post("/generate", response_model=EssayResponse)
async def generate_essay(data: EssayGenerateRequest, db: Session = Depends(get_db)):
    sch = db.query(Scholarship).filter(Scholarship.id == data.scholarship_id).first()
    if not sch:
        raise HTTPException(404, "Scholarship not found")
    profile = db.query(Profile).filter(Profile.id == 1).first()
    result = await generate_essay_draft(
        sch.name,
        sch.essay_prompt or "Describe your goals and qualifications.",
        _profile_text(profile),
        _stories_text(db),
    )
    if not result.get("configured"):
        raise HTTPException(503, result.get("message", "Gemini not configured"))

    essay = Essay(
        scholarship_id=sch.id,
        prompt=sch.essay_prompt,
        draft_text=result.get("draft_text") or "[Draft unavailable — add content manually]",
        status="needs_info" if result.get("missing_topics") else "draft",
        missing_evidence=result.get("missing_topics"),
        word_count=len((result.get("draft_text") or "").split()),
    )
    db.add(essay)
    for topic in result.get("missing_topics") or []:
        db.add(MissingInfoRequest(
            scholarship_id=sch.id,
            essay_id=None,
            question=f"Please provide: {topic}",
            reason="Missing information flagged — do not fabricate in essay",
            status="pending",
        ))
    db.commit()
    db.refresh(essay)
    if essay.scholarship_id:
        sch.status = "draft_ready"
        sch.next_action = "Review essay in Essay Studio"
        db.commit()
    return essay


@router.post("/{essay_id}/review", response_model=EssayReviewResponse)
def review_essay_endpoint(essay_id: int, db: Session = Depends(get_db)):
    essay = db.query(Essay).filter(Essay.id == essay_id).first()
    if not essay:
        raise HTTPException(404, "Essay not found")
    profile = db.query(Profile).filter(Profile.id == 1).first()
    text = essay.final_text or essay.draft_text
    result = review_essay(text, essay.prompt, _profile_text(profile), _stories_text(db))
    essay.authenticity_score = result["authenticity_score"]
    essay.prompt_alignment_score = result["prompt_alignment_score"]
    essay.generic_language_flags = result["generic_language_flags"]
    essay.unsupported_claims = result["unsupported_claims"]
    essay.missing_evidence = result["missing_evidence"]
    essay.review_suggestions = result["review_suggestions"]
    essay.status = "needs_review"
    db.commit()
    for item in result.get("missing_evidence") or []:
        db.add(MissingInfoRequest(
            scholarship_id=essay.scholarship_id,
            essay_id=essay.id,
            question=f"Essay review: {item}",
            reason="Personal Voice Review — provide real evidence",
            status="pending",
        ))
    db.commit()
    return EssayReviewResponse(**{k: v for k, v in result.items() if k != "rewrite_modes_available"})


class RewriteRequest(BaseModel):
    mode: str


@router.post("/{essay_id}/rewrite")
async def rewrite_endpoint(essay_id: int, body: RewriteRequest, db: Session = Depends(get_db)):
    essay = db.query(Essay).filter(Essay.id == essay_id).first()
    if not essay:
        raise HTTPException(404, "Essay not found")
    profile = db.query(Profile).filter(Profile.id == 1).first()
    text = essay.final_text or essay.draft_text or ""
    result = await rewrite_essay_section(
        text, body.mode, essay.prompt, _profile_text(profile), _stories_text(db)
    )
    if result.get("revised_text"):
        essay.draft_text = result["revised_text"]
        essay.word_count = len(result["revised_text"].split())
        essay.status = "needs_review"
        db.commit()
    for item in result.get("missing_info") or []:
        db.add(MissingInfoRequest(
            scholarship_id=essay.scholarship_id,
            essay_id=essay.id,
            question=str(item),
            reason="Rewrite flagged missing evidence",
            status="pending",
        ))
        db.commit()
    return result


@router.put("/{essay_id}", response_model=EssayResponse)
def update_essay(essay_id: int, data: EssayUpdate, db: Session = Depends(get_db)):
    essay = db.query(Essay).filter(Essay.id == essay_id).first()
    if not essay:
        raise HTTPException(404, "Essay not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(essay, key, value)
    if essay.draft_text or essay.final_text:
        essay.word_count = len((essay.final_text or essay.draft_text or "").split())
    db.commit()
    db.refresh(essay)
    return essay


@router.post("/{essay_id}/approve", response_model=EssayResponse)
def approve_essay(essay_id: int, db: Session = Depends(get_db)):
    essay = db.query(Essay).filter(Essay.id == essay_id).first()
    if not essay:
        raise HTTPException(404, "Essay not found")
    essay.status = "approved"
    if not essay.final_text:
        essay.final_text = essay.draft_text
    db.commit()
    db.refresh(essay)
    return essay
