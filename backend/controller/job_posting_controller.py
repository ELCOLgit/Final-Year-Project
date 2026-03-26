import json

from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models.job_postings_model import JobPosting
from backend.models.user_model import User, UserRole
from datetime import datetime
from backend.utils.dependencies import require_recruiter
from fastapi import Path
from backend.nlp.preprocessing import preprocess_text
from backend.utils.embedding_utils import generate_embedding
from backend.vectorStore.faiss_index import add_vector
from urllib.parse import unquote

router = APIRouter(
    prefix="/jobs",
    tags=["Job Postings"]
)

# dependency: get db session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# upload job posting for recruiters
@router.post("/upload/", dependencies=[Depends(require_recruiter)])
async def upload_job_posting(
    title: str = Form(...),
    description: str = Form(...),
    db: Session = Depends(get_db)
):
    # create or get demo recruiter user
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

    # preprocess the job description first
    cleaned_description = preprocess_text(description)

    # create the embedding from the cleaned text
    embedding = generate_embedding(cleaned_description)
    embedding_json = json.dumps(embedding)

    # save the job posting with the embedding stored as json
    job = JobPosting(
        recruiter_id=recruiter.id,
        title=title,
        description=cleaned_description,
        embedding=embedding_json,
        date_posted=datetime.utcnow()
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    # add the saved job embedding into faiss using the job id
    add_vector(embedding, {"job_id": job.id})

    return {
        "message": "Job posting uploaded successfully",
        "job_id": job.id,
        "title": job.title,
        "description_preview": job.description[:200] + "..." if len(job.description) > 200 else job.description
    }

# view all job postings
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

@router.get("/get-by-title/{title}")
def get_job_by_title(title: str = Path(...), db: Session = Depends(get_db)):
    title = unquote(title)
    job = db.query(JobPosting).filter(JobPosting.title == title).first()

    if not job:
        return {"description": "", "title": title}  # prevents crashes

    return {
        "id": job.id,
        "title": job.title,
        "description": job.description,
        "date_posted": job.date_posted
    }

