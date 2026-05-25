from datetime import datetime
from pydantic import BaseModel, ConfigDict


class EssayBase(BaseModel):
    scholarship_id: int | None = None
    prompt: str | None = None
    draft_text: str | None = None
    final_text: str | None = None
    status: str = "draft"


class EssayGenerateRequest(BaseModel):
    scholarship_id: int


class EssayUpdate(BaseModel):
    draft_text: str | None = None
    final_text: str | None = None
    status: str | None = None


class EssayResponse(EssayBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    word_count: int = 0
    prompt_alignment_score: float = 0.0
    authenticity_score: float = 0.0
    missing_evidence: list | None = None
    unsupported_claims: list | None = None
    generic_language_flags: list | None = None
    review_suggestions: list | None = None
    is_demo: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class EssayReviewResponse(BaseModel):
    authenticity_score: float
    prompt_alignment_score: float
    generic_language_flags: list[str]
    unsupported_claims: list[str]
    missing_evidence: list[str]
    review_suggestions: list[str]
    message: str
