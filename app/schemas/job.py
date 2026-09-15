from pydantic import BaseModel
from datetime import datetime

class JobCreate(BaseModel):
    title: str
    company: str
    description: str | None = None

class JobStatusUpdate(BaseModel):
    status: str  # "Discovered", "Review", "Applied", "Rejected"

class JobResponse(BaseModel):
    id: int
    title: str
    company: str
    description: str | None
    status: str
    match_score: int | None
    created_at: datetime

    class Config:
        from_attributes = True