import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models.match_model import Match
from backend.models.job_postings_model import JobPosting
from backend.models.resume_model import Resume
from backend.models.user_model import User
from backend.nlp.skills_extractor import extract_skills_from_text
from backend.services.cvService import generate_match_explanation, multi_step_match_analysis
from backend.utils.dependencies import get_current_user, require_recruiter
from backend.utils.embedding_utils import generate_embedding
from backend.vectorStore.faiss_index import search as faiss_search

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

@router.get("/by-resume/{resume_id}")
def get_matches_for_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    matches = (
        db.query(Match)
        .filter(Match.resume_id == resume_id)
        .order_by(Match.match_score.desc())
        .all()
    )

    return [
        {
            "job_id": m.job_posting.id,
            "job_title": m.job_posting.title,
            "score": round(m.match_score, 3),
            "generated_at": m.generated_at
        }
        for m in matches
    ]


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


@router.get("/by-job/{job_id}")
def get_matches_for_job(
    job_id: int,
    current_user: User = Depends(require_recruiter),
    db: Session = Depends(get_db)
):
    # load all matches for one job and rank them from highest to lowest
    matches = (
        db.query(Match)
        .filter(Match.job_posting_id == job_id)
        .order_by(Match.match_score.desc())
        .all()
    )

    return [
        {
            "resume_id": m.resume.id,
            "filename": m.resume.filename,
            "user_id": m.resume.user_id,
            "score": round(m.match_score, 3),
            "generated_at": m.generated_at,
            "skills": extract_skills_from_text(m.resume.text_content or ""),
        }
        for m in matches
    ]


@router.get("/search/{resume_id}")
def search_matches_for_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # get the resume from the database using the id
    resume = (
        db.query(Resume)
        .filter(Resume.id == resume_id, Resume.user_id == current_user.id)
        .first()
    )
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    # create and save the resume embedding if it is missing
    if not resume.embedding or resume.embedding == "[]":
        resume_text = resume.text_content or ""
        resume_embedding = generate_embedding(resume_text)
        resume.embedding = json.dumps(resume_embedding)
        db.commit()
        db.refresh(resume)

    # load the stored embedding (it is saved as json text)
    try:
        resume_embedding = json.loads(resume.embedding or "[]")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Resume embedding is invalid") from exc

    # stop here if no embedding was saved yet
    if not resume_embedding:
        raise HTTPException(status_code=400, detail="Resume embedding is empty")

    # get the cv text once so we can compare it with each job
    cv_text = resume.text_content or ""
    cv_skills = extract_skills_from_text(cv_text)

    # run faiss search using the resume embedding
    faiss_results = faiss_search(resume_embedding, k=10)

    # build a ranked list of job matches from the faiss results
    matches = []
    seen_job_ids = set()

    for result in faiss_results:
        metadata = result.get("metadata") or {}

        # read job id from metadata so we can load job details
        job_id = metadata.get("job_id") or metadata.get("id") or metadata.get("job_posting_id")
        if job_id is None:
            continue
        if job_id in seen_job_ids:
            continue
        seen_job_ids.add(job_id)

        job = db.query(JobPosting).filter(JobPosting.id == job_id).first()
        if not job:
            continue

        # read job text and metadata so we can build a richer response
        job_text = job.description or ""
        analysis = multi_step_match_analysis(cv_text, job_text)
        explanation = generate_match_explanation(cv_text, job_text)
        faiss_score = float(result.get("score", 0.0))
        skill_score = float(analysis.get("score", 0.0))
        matching_skills = analysis.get("matching_skills", [])
        missing_skills = analysis.get("missing_skills", [])

        # combine faiss score with the current skill-based score
        ranked_score = round((faiss_score + skill_score) / 2, 3)

        # save or update the ranked match in the database
        saved_match = (
            db.query(Match)
            .filter(Match.resume_id == resume.id, Match.job_posting_id == job.id)
            .first()
        )
        if saved_match:
            saved_match.match_score = ranked_score
            saved_match.generated_at = datetime.utcnow()
        else:
            saved_match = Match(
                user_id=current_user.id,
                resume_id=resume.id,
                job_posting_id=job.id,
                match_score=ranked_score,
                created_at=datetime.utcnow(),
                generated_at=datetime.utcnow(),
            )
            db.add(saved_match)
            db.flush()

        # keep only first ~200 chars so response stays short
        description_preview = job_text[:200]

        matches.append({
            "id": saved_match.id,
            "score": ranked_score,
            "faiss_score": faiss_score,
            "skill_match_score": skill_score,
            "job_id": job.id,
            "title": job.title,
            "similarity_score": faiss_score,
            "description_preview": description_preview,
            "reasoning": {
                "matching_skills": matching_skills,
                "missing_skills": missing_skills,
                "explanation": explanation,
            },
        })

    # save all match rows before returning
    db.commit()

    # rank matches from highest score to lowest
    matches.sort(key=lambda item: item["score"], reverse=True)

    # return the ranked matches list directly
    return matches
