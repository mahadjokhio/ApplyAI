from pydantic import BaseModel

class UserCreate(BaseModel):
    email: str
    full_name: str | None = None

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str | None

    class Config:
        from_attributes = True