from datetime import datetime
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base

class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    job_posting_id = Column(Integer, ForeignKey("job_postings.id"), nullable=False)
    match_score = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="job_matches")
    resume = relationship("Resume", back_populates="matches")
    job_posting = relationship("JobPosting", back_populates="matches")

from backend.models.user_model import User
from backend.models.resume_model import Resume
from backend.models.job_postings_model import JobPosting
