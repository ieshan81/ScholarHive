from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.profile import Profile
from app.schemas.profile import ProfileResponse, ProfileUpdate

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("", response_model=ProfileResponse)
def get_profile(db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.id == 1).first()
    if not profile:
        profile = Profile(id=1, major="Mechanical Engineering", international_student=True)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@router.put("", response_model=ProfileResponse)
def update_profile(data: ProfileUpdate, db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.id == 1).first()
    if not profile:
        profile = Profile(id=1)
        db.add(profile)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return profile
