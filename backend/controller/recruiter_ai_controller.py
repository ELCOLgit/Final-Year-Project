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
from backend.services.cvService import (
    build_match_score_data,
    compare_matching_methods,
    detect_intent,
    generate_response,
    get_match_label,
    multi_step_match_analysis,
)
from backend.utils.embedding_utils import generate_embedding
from backend.utils.dependencies import require_recruiter
from backend.vectorStore.resume_faiss_index import search as resume_faiss_search

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


def build_score_data(score):
    # keep the raw score and add simpler display values
    if score is None:
        return {
            "match_score": None,
            "percentage_score": None,
            "rating_score": None,
            "match_label": None,
        }

    match_label = get_match_label(score)

    return {
        "match_score": score,
        "percentage_score": int(score * 100),
        "rating_score": round(score * 10),
        "match_label": match_label,
    }


def build_score_data_from_analysis(cv_text, job_text):
    # compute a temporary score when no saved match row exists yet
    method_scores = compare_matching_methods(cv_text or "", job_text or "")
    analysis = multi_step_match_analysis(
        cv_text or "",
        job_text or "",
        embedding_score=method_scores.get("embedding_score", 0.0),
    )
    score_data = build_match_score_data(analysis.get("final_score", 0.0))
    return {
        "match_score": score_data["final_score"],
        "percentage_score": score_data["percentage_score"],
        "rating_score": score_data["rating_score"],
        "match_label": score_data["match_label"],
    }


def get_live_best_candidate(job, db: Session):
    # compute the best recruiter candidate live so dataset resumes are included too
    if not job:
        return None

    from backend.controller.match_controller import rerank_recruiter_match

    job_text = f"{job.title or ''} {job.description or ''}".strip()
    job_embedding = generate_embedding(job_text)
    faiss_results = resume_faiss_search(job_embedding, k=20)
    seen_resume_ids = set()
    ranked_candidates = []

    for result in faiss_results:
        metadata = result.get("metadata") or {}
        resume_id = metadata.get("resume_id")
        if resume_id is None or resume_id in seen_resume_ids:
            continue

        resume = db.query(Resume).filter(Resume.id == resume_id).first()
        if not resume:
            continue

        seen_resume_ids.add(resume_id)
        analysis = multi_step_match_analysis(
            resume.text_content or "",
            job_text,
            embedding_score=float(result.get("score", 0.0)),
        )
        rerank_data = rerank_recruiter_match(job, resume, metadata, analysis)
        score_data = build_match_score_data(rerank_data["recruiter_score"])
        ranked_candidates.append(
            {
                "filename": resume.filename,
                "score": score_data["final_score"],
                "percentage_score": score_data["percentage_score"],
                "rating_score": score_data["rating_score"],
                "match_label": score_data["match_label"],
            }
        )

    if not ranked_candidates:
        return None

    ranked_candidates.sort(key=lambda item: item["score"], reverse=True)
    return ranked_candidates[0]


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
    job_text = f"{job.title or ''} {job.description or ''}".strip() if job else ""
    cv_skills = extract_skills_from_text(resume.text_content or "") if resume else []
    job_skills = extract_skills_from_text(job_text) if job else []
    missing_skills = [skill for skill in job_skills if skill not in cv_skills] if resume and job else []
    suggestions = generate_suggestions(
        resume.text_content or "",
        job_text,
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
    live_best_candidate = get_live_best_candidate(job, db) if job else None
    if job and not live_best_candidate:
        top_match = (
            db.query(Match)
            .filter(Match.job_posting_id == job.id)
            .order_by(Match.match_score.desc())
            .first()
        )

    if selected_match:
        selected_score_data = build_score_data(selected_match.match_score)
    elif resume and job:
        selected_score_data = build_score_data_from_analysis(resume.text_content or "", job_text)
    elif top_match:
        selected_score_data = build_score_data(top_match.match_score)
    else:
        selected_score_data = build_score_data(None)

    if live_best_candidate:
        best_score_data = {
            "match_score": live_best_candidate["score"],
            "percentage_score": live_best_candidate["percentage_score"],
            "rating_score": live_best_candidate["rating_score"],
            "match_label": live_best_candidate["match_label"],
        }
    else:
        best_candidate_score = top_match.match_score if top_match else None
        best_score_data = build_score_data(best_candidate_score)

    context_data = {
        "candidate_name": resume.filename if resume else "this candidate",
        "job_title": job.title if job else "this role",
        "cv_text": resume.text_content if resume else "",
        "job_text": job_text if job else "",
        "cv_skills": cv_skills,
        "job_skills": job_skills,
        "missing_skills": missing_skills,
        "suggestions": suggestions,
        "match_score": selected_score_data["match_score"],
        "percentage_score": selected_score_data["percentage_score"],
        "rating_score": selected_score_data["rating_score"],
        "match_label": selected_score_data["match_label"],
        "best_candidate_name": live_best_candidate["filename"] if live_best_candidate else (top_match.resume.filename if top_match and top_match.resume else None),
        "best_candidate_score": best_score_data["match_score"],
        "best_candidate_percentage_score": best_score_data["percentage_score"],
        "best_candidate_rating_score": best_score_data["rating_score"],
        "best_candidate_match_label": best_score_data["match_label"],
    }

    intent = detect_intent(question)
    answer = generate_response(intent, context_data)

    return {
        "answer": answer,
        "intent": intent,
        "cv_skills": cv_skills,
        "job_skills": job_skills,
        "match_score": context_data["match_score"],
        "percentage_score": context_data["percentage_score"],
        "rating_score": context_data["rating_score"],
        "match_label": context_data["match_label"],
        "resume_id": payload.resume_id,
        "job_id": payload.job_id,
        "best_candidate_name": context_data["best_candidate_name"],
        "best_candidate_score": context_data["best_candidate_score"],
        "best_candidate_percentage_score": context_data["best_candidate_percentage_score"],
        "best_candidate_rating_score": context_data["best_candidate_rating_score"],
        "best_candidate_match_label": context_data["best_candidate_match_label"],
        "missing_skills": missing_skills,
        "suggestions": suggestions,
        "candidate_name": context_data["candidate_name"],
        "job_title": context_data["job_title"],
    }
