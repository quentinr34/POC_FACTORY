from datetime import datetime

from pydantic import BaseModel, Field


class Subscores(BaseModel):
    clarity: int = Field(ge=0, le=100)
    budget: int = Field(ge=0, le=100)
    urgency: int = Field(ge=0, le=100)
    offer_fit: int = Field(ge=0, le=100)


class BriefRequest(BaseModel):
    brief: str = Field(min_length=1)


class ClaudeAnalysis(BaseModel):
    summary: str
    subscores: Subscores
    questions: list[str]


class Qualification(BaseModel):
    id: str | None = None
    created_at: datetime | None = None
    brief_raw: str
    summary: str
    subscores: Subscores
    score: int = Field(ge=0, le=100)
    questions: list[str]
    model: str
