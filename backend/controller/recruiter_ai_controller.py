from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models.job_postings_model import JobPosting
from backend.models.match_model import Match
from backend.models.resume_model import Resume
from backend.nlp.improvement_suggestions import generate_suggestions
from backend.nlp.skills_extractor import extract_skills_from_text
from backend.services.cvService import detect_intent, generate_response
from backend.utils.dependencies import require_recruiter

router = APIRouter(prefix="/recruiter-ai", tags=["Recruiter AI"])


class RecruiterQuestion(BaseModel):
    question: str
    resume_id: Optional[int] = None
    job_id: Optional[int] = None


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/query/")
def query_recruiter_ai(
    payload: RecruiterQuestion,
    current_user=Depends(require_recruiter),
    db: Session = Depends(get_db)
):
    # clean the question so the simple checks are easier
    question = (payload.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")

    resume = None
    if payload.resume_id is not None:
        resume = db.query(Resume).filter(Resume.id == payload.resume_id).first()
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")

    job = None
    if payload.job_id is not None:
        job = db.query(JobPosting).filter(JobPosting.id == payload.job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

    # extract real context from the selected candidate and job
    cv_skills = extract_skills_from_text(resume.text_content or "") if resume else []
    job_skills = extract_skills_from_text(job.description or "") if job else []
    missing_skills = [skill for skill in job_skills if skill not in cv_skills] if resume and job else []
    suggestions = generate_suggestions(
        resume.text_content or "",
        job.description or "",
        missing_skills,
    ) if resume and job else []

    selected_match = None
    if resume and job:
        selected_match = (
            db.query(Match)
            .filter(Match.resume_id == resume.id, Match.job_posting_id == job.id)
            .first()
        )

    top_match = None
    if job:
        top_match = (
            db.query(Match)
            .filter(Match.job_posting_id == job.id)
            .order_by(Match.match_score.desc())
            .first()
        )

    context_data = {
        "candidate_name": resume.filename if resume else "this candidate",
        "job_title": job.title if job else "this role",
        "cv_text": resume.text_content if resume else "",
        "job_text": job.description if job else "",
        "cv_skills": cv_skills,
        "job_skills": job_skills,
        "missing_skills": missing_skills,
        "suggestions": suggestions,
        "match_score": selected_match.match_score if selected_match else (top_match.match_score if top_match else None),
        "best_candidate_name": top_match.resume.filename if top_match and top_match.resume else None,
        "best_candidate_score": top_match.match_score if top_match else None,
    }

    intent = detect_intent(question)
    answer = generate_response(intent, context_data)

    return {
        "answer": answer,
        "intent": intent,
        "cv_skills": cv_skills,
        "job_skills": job_skills,
        "match_score": context_data["match_score"],
        "resume_id": payload.resume_id,
        "job_id": payload.job_id,
        "best_candidate_name": context_data["best_candidate_name"],
        "best_candidate_score": context_data["best_candidate_score"],
        "missing_skills": missing_skills,
        "suggestions": suggestions,
        "candidate_name": context_data["candidate_name"],
        "job_title": context_data["job_title"],
    }
