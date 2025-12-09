from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models.match_model import Match
from backend.models.resume_model import Resume
from backend.models.job_postings_model import JobPosting

router = APIRouter(prefix="/matches", tags=["Matches"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/")
def get_all_matches(db: Session = Depends(get_db)):
    matches = db.query(Match).order_by(Match.match_score.desc()).all()

    return [
        {
            "id": m.id,
            "resume": m.resume.filename,
            "job_title": m.job_posting.title,
            "score": m.match_score,
            "created_at": m.created_at,
            "generated_at": m.generated_at
        }
        for m in matches
    ]


@router.get("/top/")
def get_top_matches(db: Session = Depends(get_db)):
    resumes = db.query(Resume).all()
    results = []

    for r in resumes:
        top = (
            db.query(Match)
            .filter(Match.resume_id == r.id)
            .order_by(Match.match_score.desc())
            .first()
        )
        if top:
            results.append({
                "resume": r.filename,
                "job_title": top.job_posting.title,
                "score": top.match_score,
                "generated_at": top.generated_at
            })

    return {"top_matches": results}

@router.get("/matches/debug/")
def debug_matches(db: Session = Depends(get_db)):
    matches = db.query(Match).all()
    return [
        {
            "id": m.id,
            "user": m.user.name if m.user else None,
            "resume": m.resume.file_name if m.resume else None,
            "job_title": m.job_posting.title if m.job_posting else None,
            "score": m.match_score,
            "created_at": m.created_at,
        }
        for m in matches
    ]
