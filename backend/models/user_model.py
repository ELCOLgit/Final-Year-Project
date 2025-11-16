import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Enum, DateTime
from sqlalchemy.orm import relationship
from backend.database import Base

class UserRole(enum.Enum):
    job_seeker = "job_seeker"
    recruiter = "recruiter"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(Enum(UserRole))
    created_at = Column(DateTime, default=datetime.utcnow)

    resumes = relationship("Resume", back_populates="user", cascade="all, delete")
    job_matches = relationship("Match", back_populates="user", cascade="all, delete")
    job_postings = relationship("JobPosting", back_populates="recruiter", cascade="all, delete")

