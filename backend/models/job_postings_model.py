from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base

class JobPosting(Base):
    __tablename__ = "job_postings"

    id = Column(Integer, primary_key=True, index=True)
    recruiter_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    description = Column(Text)
    embedding = Column(Text)  # can store as JSON string or vector data
    date_posted = Column(DateTime, default=datetime.utcnow)

    recruiter = relationship("User", back_populates="job_postings")
    matches = relationship("Match", back_populates="job_posting", cascade="all, delete")

