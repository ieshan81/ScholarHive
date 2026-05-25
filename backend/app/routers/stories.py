from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.story import Story
from app.schemas.story import StoryCreate, StoryUpdate, StoryResponse

router = APIRouter(prefix="/api/stories", tags=["stories"])


@router.get("", response_model=list[StoryResponse])
def list_stories(db: Session = Depends(get_db)):
    return db.query(Story).order_by(Story.updated_at.desc()).all()


@router.post("", response_model=StoryResponse)
def create_story(data: StoryCreate, db: Session = Depends(get_db)):
    story = Story(**data.model_dump())
    db.add(story)
    db.commit()
    db.refresh(story)
    return story


@router.put("/{story_id}", response_model=StoryResponse)
def update_story(story_id: int, data: StoryUpdate, db: Session = Depends(get_db)):
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(404, "Story not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(story, key, value)
    db.commit()
    db.refresh(story)
    return story


@router.delete("/{story_id}")
def delete_story(story_id: int, db: Session = Depends(get_db)):
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(404, "Story not found")
    db.delete(story)
    db.commit()
    return {"message": "Story deleted"}
