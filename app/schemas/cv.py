from datetime import datetime

from pydantic import BaseModel, Field


class CVProfileCreate(BaseModel):
    raw_text: str = Field(min_length=1)


class CVProfileResponse(BaseModel):
    id: int
    user_id: int
    raw_text: str
    created_at: datetime

    class Config:
        from_attributes = True