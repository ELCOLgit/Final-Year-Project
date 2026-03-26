from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models.job_postings_model import JobPosting
from backend.models.match_model import Match
from backend.models.resume_model import Resume
from backend.nlp.skills_extractor import extract_skills_from_text
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
    question = (payload.question or "").strip().lower()
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

    # answer skills questions for one selected cv
    if "skill" in question and resume:
        skills = extract_skills_from_text(resume.text_content or "")
        if skills:
            answer = f"the main skills in {resume.filename} are: {', '.join(skills)}"
        else:
            answer = f"i could not find any known skills in {resume.filename}"

        return {
            "answer": answer,
            "skills": skills,
            "resume_id": resume.id,
            "job_id": payload.job_id,
        }

    # answer best match questions for one selected job
    if job and ("best" in question or "top" in question or "rank" in question or "match" in question):
        matches = (
            db.query(Match)
            .filter(Match.job_posting_id == job.id)
            .order_by(Match.match_score.desc())
            .all()
        )

        if not matches:
            answer = f"there are no ranked candidates yet for {job.title}"
            return {"answer": answer, "resume_id": payload.resume_id, "job_id": job.id}

        top_names = [match.resume.filename for match in matches[:3]]
        answer = f"the best matching candidates for {job.title} are: {', '.join(top_names)}"

        return {
            "answer": answer,
            "top_candidates": top_names,
            "resume_id": payload.resume_id,
            "job_id": job.id,
        }

    # answer summary questions for one selected cv
    if resume and ("summary" in question or "summarise" in question or "summarize" in question or "tell me about" in question):
        skills = extract_skills_from_text(resume.text_content or "")
        top_matches = (
            db.query(Match)
            .filter(Match.resume_id == resume.id)
            .order_by(Match.match_score.desc())
            .all()
        )
        top_jobs = [match.job_posting.title for match in top_matches[:3]]

        answer = (
            f"{resume.filename} has skills in {', '.join(skills) if skills else 'no known skills found'}"
        )
        if top_jobs:
            answer += f" and matches best with {', '.join(top_jobs)}"

        return {
            "answer": answer,
            "skills": skills,
            "top_jobs": top_jobs,
            "resume_id": resume.id,
            "job_id": payload.job_id,
        }

    # answer simple count questions about candidates
    if "how many" in question and ("candidate" in question or "cv" in question or "resume" in question):
        resume_count = db.query(Resume).count()
        answer = f"there are {resume_count} uploaded candidate resumes in the system"
        return {
            "answer": answer,
            "candidate_count": resume_count,
            "resume_id": payload.resume_id,
            "job_id": payload.job_id,
        }

    # give a simple fallback if the question does not match a known pattern
    return {
        "answer": (
            "try a question like: what skills are in this cv, summarise this candidate, "
            "or who are the best matches for this job"
        ),
        "resume_id": payload.resume_id,
        "job_id": payload.job_id,
    }
