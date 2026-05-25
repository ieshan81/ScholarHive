from datetime import datetime
from pydantic import BaseModel, ConfigDict


class StoryBase(BaseModel):
    title: str
    category: str
    tags: str | None = None
    summary: str | None = None
    full_story: str | None = None
    verified_by_user: bool = False


class StoryCreate(StoryBase):
    pass


class StoryUpdate(BaseModel):
    title: str | None = None
    category: str | None = None
    tags: str | None = None
    summary: str | None = None
    full_story: str | None = None
    verified_by_user: bool | None = None


class StoryResponse(StoryBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    used_in_essays_count: int = 0
    is_demo: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None
