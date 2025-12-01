from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base

class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    filename = Column(String)
    text_content = Column(Text)
    embedding = Column(Text)  
    upload_date = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="resumes")
    matches = relationship("Match", back_populates="resume", cascade="all, delete")
