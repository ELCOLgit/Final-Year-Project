from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models.match_model import Match
from backend.models.resume_model import Resume
from backend.models.user_model import User
from backend.utils.dependencies import get_current_user

router = APIRouter(prefix="/matches", tags=["Matches"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/")
def get_user_matches(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    matches = (
        db.query(Match)
        .filter(Match.user_id == current_user.id)
        .order_by(Match.match_score.desc())
        .all()
    )

    return [
        {
            "id": m.id,
            "resume": m.resume.filename,
            "job_title": m.job_posting.title,
            "score": m.match_score,
            "created_at": m.created_at,
            "generated_at": m.generated_at,
        }
        for m in matches
    ]


@router.get("/top/")
def get_top_matches(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    resumes = db.query(Resume).filter(Resume.user_id == current_user.id).all()

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


@router.get("/debug/")
def debug_matches(db: Session = Depends(get_db)):
    matches = db.query(Match).all()
    return [
        {
            "id": m.id,
            "user_id": m.user_id,
            "resume": m.resume.filename,
            "job_title": m.job_posting.title,
            "score": m.match_score,
        }
        for m in matches
    ]
