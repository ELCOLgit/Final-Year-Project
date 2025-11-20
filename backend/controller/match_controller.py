from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models.match_model import Match

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
