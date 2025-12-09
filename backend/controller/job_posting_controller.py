from fastapi import APIRouter, Depends, Form
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models.job_postings_model import JobPosting
from backend.models.user_model import User, UserRole
from datetime import datetime
from backend.utils.dependencies import require_recruiter
from fastapi import Depends

router = APIRouter(
    prefix="/jobs",
    tags=["Job Postings"]
)

# Dependency: get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# === Upload job posting (for recruiters) ===
@router.post("/upload/", dependencies=[Depends(require_recruiter)])
async def upload_job_posting(
    title: str = Form(...),
    description: str = Form(...),
    db: Session = Depends(get_db)
):
    # Create or get demo recruiter user
    recruiter = db.query(User).filter(User.id == 2).first()
    if not recruiter:
        recruiter = User(
            name="Demo Recruiter",
            email="recruiter@example.com",
            password_hash="123",
            role=UserRole.recruiter
        )
        db.add(recruiter)
        db.commit()
        db.refresh(recruiter)

    # Add the job posting
    job = JobPosting(
        recruiter_id=recruiter.id,
        title=title,
        description=description,
        embedding="[]",
        date_posted=datetime.utcnow()
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return {
        "message": "Job posting uploaded successfully",
        "job_id": job.id,
        "title": job.title,
        "description_preview": description[:200] + "..." if len(description) > 200 else description
    }

# === Optional: View all job postings ===
@router.get("/")
def list_job_postings(db: Session = Depends(get_db)):
    jobs = db.query(JobPosting).all()
    return [
        {
            "id": j.id,
            "title": j.title,
            "recruiter_id": j.recruiter_id,
            "date_posted": j.date_posted
        }
        for j in jobs
    ]

@router.get("/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(JobPosting).filter(JobPosting.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "id": job.id,
        "title": job.title,
        "description": job.description
    }
