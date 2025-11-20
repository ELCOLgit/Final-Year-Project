from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models.resume_model import Resume
from backend.models.job_postings_model import JobPosting
from backend.models.match_model import Match
from backend.utils.similarity_utils import calculate_similarity
from datetime import datetime

router = APIRouter(
    prefix="/generate",
    tags=["Match Generation"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/matches/")
def generate_matches(db: Session = Depends(get_db)):
    resumes = db.query(Resume).all()
    jobs = db.query(JobPosting).all()
    if not resumes or not jobs:
        return {"message": "No resumes or job postings found."}

    created_matches = []
    for resume in resumes:
        for job in jobs:
            # Check if match already exists
            existing_match = (
                db.query(Match)
                .filter(
                    Match.resume_id == resume.id,
                    Match.job_posting_id == job.id
                )
                .first()
            )
            if existing_match:
                # Update score if already exists
                existing_match.match_score = calculate_similarity(resume.text_content, job.description)
                db.commit()
                db.refresh(existing_match)
                created_matches.append({
                    "resume": resume.filename,
                    "job": job.title,
                    "match_score": existing_match.match_score,
                    "status": "updated"
                })
            else:
                # Create new match if it doesn't exist
                score = calculate_similarity(resume.text_content, job.description)
                match = Match(
                    user_id=resume.user_id,
                    resume_id=resume.id,
                    job_posting_id=job.id,
                    match_score=score,
                    created_at=datetime.utcnow()
                )
                db.add(match)
                db.commit()
                db.refresh(match)
                created_matches.append({
                    "resume": resume.filename,
                    "job": job.title,
                    "match_score": score,
                    "status": "created"
                })
    return {"generated_matches": created_matches}
