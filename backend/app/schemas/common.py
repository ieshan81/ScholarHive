from datetime import datetime, date
from pydantic import BaseModel, ConfigDict


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    message: str
    detail: str | None = None


class ConfigStatus(BaseModel):
    configured: bool
    status: str
    message: str | None = None
