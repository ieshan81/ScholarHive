from datetime import datetime, date
from pydantic import BaseModel, ConfigDict, Field


class ScholarshipBase(BaseModel):
    name: str
    source_url: str | None = None
    source_type: str = "manual"
    award_amount: str | None = None
    deadline: date | None = None
    eligibility_notes: str | None = None
    required_documents: str | None = None
    essay_required: bool = False
    essay_prompt: str | None = None
    word_limit: int | None = None
    citizenship_requirement: str | None = None
    major_requirement: str | None = None
    education_level_requirement: str | None = None
    international_allowed: str = "unknown"
    trust_score: float = 50.0
    effort_score: float = 50.0
    status: str = "found"
    next_action: str | None = None


class ScholarshipCreate(ScholarshipBase):
    pass


class ScholarshipUpdate(BaseModel):
    name: str | None = None
    source_url: str | None = None
    source_type: str | None = None
    award_amount: str | None = None
    deadline: date | None = None
    eligibility_notes: str | None = None
    required_documents: str | None = None
    essay_required: bool | None = None
    essay_prompt: str | None = None
    word_limit: int | None = None
    citizenship_requirement: str | None = None
    major_requirement: str | None = None
    education_level_requirement: str | None = None
    international_allowed: str | None = None
    trust_score: float | None = None
    effort_score: float | None = None
    status: str | None = None
    next_action: str | None = None


class ScholarshipResponse(ScholarshipBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    eligibility_score: float = 0.0
    priority_score: float = 0.0
    eligibility_reasons: str | None = None
    eligibility_blockers: str | None = None
    missing_info: str | None = None
    is_demo: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ScholarshipMoveStatus(BaseModel):
    status: str
    next_action: str | None = None


class EligibilityResult(BaseModel):
    eligibility_score: float
    status_recommendation: str
    reasons: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
