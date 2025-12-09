from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models.resume_model import Resume
from backend.models.job_postings_model import JobPosting
from backend.models.match_model import Match
from backend.utils.similarity_utils import compute_similarity_matrix
from backend.utils.dependencies import require_recruiter
from datetime import datetime

router = APIRouter(prefix="/generate", tags=["Match Generation"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

SIM_THRESHOLD = 0.10

@router.post("/matches/")
def generate_all_matches(
    current_user = Depends(require_recruiter),   # <-- PROTECT ENDPOINT
    db: Session = Depends(get_db)
):

    resumes = db.query(Resume).all()
    jobs = db.query(JobPosting).all()

    if not resumes or not jobs:
        return {"message": "No resumes or job postings available."}

    resume_texts = [r.text_content for r in resumes]
    job_texts = [j.description for j in jobs]

    sim_matrix = compute_similarity_matrix(resume_texts, job_texts)

    new_matches = 0
    updated_matches = 0
    removed_low = 0

    for m in db.query(Match).all():
        if m.match_score < SIM_THRESHOLD:
            db.delete(m)
            removed_low += 1
    db.commit()

    for r_i, resume in enumerate(resumes):
        for j_i, job in enumerate(jobs):

            score = float(sim_matrix[r_i][j_i])
            if score < SIM_THRESHOLD:
                continue

            existing = (
                db.query(Match)
                .filter(Match.resume_id == resume.id,
                        Match.job_posting_id == job.id)
                .first()
            )

            if existing:
                existing.match_score = score
                existing.generated_at = datetime.utcnow()
                updated_matches += 1
            else:
                match = Match(
                    user_id=resume.user_id,        # <-- CRITICAL FIX
                    resume_id=resume.id,
                    job_posting_id=job.id,
                    match_score=score,
                    created_at=datetime.utcnow(),
                    generated_at=datetime.utcnow(),
                )
                db.add(match)
                new_matches += 1

    db.commit()

    return {
        "processed_resumes": len(resumes),
        "processed_jobs": len(jobs),
        "new_matches": new_matches,
        "updated_matches": updated_matches,
        "removed_low_matches": removed_low,
        "threshold": SIM_THRESHOLD,
        "status": "success"
    }
