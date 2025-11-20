from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models.match_model import Match
from backend.models.resume_model import Resume
from backend.models.job_postings_model import JobPosting


router = APIRouter(
    prefix="/matches",
    tags=["Matches"]
)

# Dependency: get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/")
def get_all_matches(db: Session = Depends(get_db)):
    matches = db.query(Match).all()
    results = []

    for m in matches:
        results.append({
            "match_id": m.id,
            "job_seeker": m.user.name if m.user else None,
            "resume": m.resume.filename if m.resume else None,
            "job_posting": m.job_posting.title if m.job_posting else None,
            "match_score": m.match_score
        })

    return {"matches": results}

@router.get("/top/")
def get_top_matches(db: Session = Depends(get_db)):
    # group by resume and get highest score
    subquery = (
        db.query(
            Match.resume_id,
            Match.job_posting_id,
            Match.match_score
        )
        .order_by(Match.resume_id, Match.match_score.desc())
        .all()
    )

    seen = set()
    top_matches = []
    for r in subquery:
        if r.resume_id not in seen:
            seen.add(r.resume_id)
            top_matches.append(r)

    results = []
    for m in top_matches:
        resume = db.query(Resume).filter(Resume.id == m.resume_id).first()
        job = db.query(JobPosting).filter(JobPosting.id == m.job_posting_id).first()
        results.append({
            "resume": resume.filename if resume else "N/A",
            "job_title": job.title if job else "N/A",
            "match_score": m.match_score
        })

    return {"top_matches": results}

@router.get("/filter/")
def filter_matches(
    job_title: str = None,
    min_score: float = 0.0,
    db: Session = Depends(get_db)
):
    query = db.query(Match)

    # Filter by score
    query = query.filter(Match.match_score >= min_score)

    results = []
    for m in query.all():
        resume = db.query(Resume).filter(Resume.id == m.resume_id).first()
        job = db.query(JobPosting).filter(JobPosting.id == m.job_posting_id).first()

        if job_title and job and job_title.lower() not in job.title.lower():
            continue

        results.append({
            "resume": resume.filename if resume else "N/A",
            "job_title": job.title if job else "N/A",
            "match_score": m.match_score
        })

    return {"filtered_matches": results}
