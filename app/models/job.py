from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.database import Base

class JobApplication(Base):
    __tablename__ = "job_applications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, default="Discovered")  # Discovered, Review, Applied, Rejected
    match_score = Column(Integer, nullable=True)    # filled in Phase 4
    created_at = Column(DateTime(timezone=True), server_default=func.now())