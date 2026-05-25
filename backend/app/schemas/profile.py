from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ProfileBase(BaseModel):
    personal_details: str | None = None
    education: str | None = None
    university: str | None = None
    major: str | None = None
    international_student: bool = True
    visa_status: str | None = None
    gpa: float | None = None
    financial_need: str | None = None
    projects: str | None = None
    achievements: str | None = None
    leadership: str | None = None
    volunteering: str | None = None
    career_goals: str | None = None
    personal_statements: str | None = None
    scholarship_preferences: str | None = None


class ProfileUpdate(ProfileBase):
    pass


class ProfileResponse(ProfileBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
