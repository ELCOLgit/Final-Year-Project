from backend.database import SessionLocal
from backend.models.user_model import User, UserRole
from backend.models.job_postings_model import JobPosting
from backend.models.resume_model import Resume
from backend.models.match_model import Match
from datetime import datetime

# Create a database session
db = SessionLocal()

try:
    # 1️⃣ Create a recruiter
    recruiter = User(
        name="Recruiter John",
        email="recruiter@example.com",
        password_hash="hashedpassword123",
        role=UserRole.recruiter
    )
    db.add(recruiter)
    db.commit()
    db.refresh(recruiter)
    print(f"Created recruiter: {recruiter.name}")

    # 2️⃣ Create a job posting
    job_posting = JobPosting(
        recruiter_id=recruiter.id,
        title="Software Engineer Intern",
        description="Looking for a student with Python and FastAPI experience.",
        embedding="[]",
        date_posted=datetime.utcnow()
    )
    db.add(job_posting)
    db.commit()
    db.refresh(job_posting)
    print(f"Created job posting: {job_posting.title}")

    # 3️⃣ Create a job seeker
    job_seeker = User(
        name="Aileen Coliban",
        email="aileen@example.com",
        password_hash="hashedpassword456",
        role=UserRole.job_seeker
    )
    db.add(job_seeker)
    db.commit()
    db.refresh(job_seeker)
    print(f"Created job seeker: {job_seeker.name}")

    # 4️⃣ Add a resume for that job seeker
    resume = Resume(
        user_id=job_seeker.id,
        filename="Aileen_Resume.pdf",
        text_content="Python, FastAPI, NLP, and FAISS experience.",
        embedding="[]",
        upload_date=datetime.utcnow()
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    print(f"Created resume: {resume.filename}")

    # 5️⃣ Create a match record
    match = Match(
        user_id=job_seeker.id,
        resume_id=resume.id,
        job_posting_id=job_posting.id,
        match_score=0.85
    )
    db.add(match)
    db.commit()
    print(f"Created match with score: {match.match_score}")

finally:
    db.close()
