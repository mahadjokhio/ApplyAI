from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.database import Base

class CVProfile(Base):
    __tablename__ = "cv_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    raw_text = Column(Text, nullable=False)      # extracted CV text
    skills = Column(Text, nullable=True)          # comma-separated or JSON string for now
    file_path = Column(String, nullable=True)     # where the uploaded CV file is stored
    created_at = Column(DateTime(timezone=True), server_default=func.now())