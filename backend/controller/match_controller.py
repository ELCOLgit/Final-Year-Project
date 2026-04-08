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
from backend.services.cvService import (
    build_match_score_data,
    generate_match_explanation,
    multi_step_match_analysis,
)
from backend.utils.dependencies import get_current_user, require_recruiter
from backend.utils.embedding_utils import generate_embedding
from backend.vectorStore.faiss_index import search as faiss_search
from backend.vectorStore.resume_faiss_index import search as resume_faiss_search

router = APIRouter(prefix="/matches", tags=["Matches"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def build_score_data(score):
    # build one shared score payload for every match response
    return build_match_score_data(score)


def parse_resume_category(resume, metadata):
    # read the resume category from faiss metadata first, then fall back to the filename
    metadata_category = (metadata or {}).get("category")
    if metadata_category and str(metadata_category).strip():
        return str(metadata_category).strip()

    filename = (resume.filename or "")
    if not filename.startswith("dataset_resume_"):
        return "unknown"

    trimmed_name = filename.removeprefix("dataset_resume_").removesuffix(".txt")
    parts = trimmed_name.split("_", 1)

    if len(parts) < 2 or not parts[1].strip():
        return "unknown"

    return parts[1].strip()


def get_likely_job_categories(job):
    # map simple job keywords to likely resume categories
    job_text = f"{job.title or ''} {job.description or ''}".lower()
    likely_categories = set()

    category_keywords = {
        "DIGITAL-MEDIA": ["marketing", "social media", "content", "brand", "digital media"],
        "PUBLIC-RELATIONS": ["marketing", "public relations", "communications", "media relations"],
        "BUSINESS-DEVELOPMENT": [
            "marketing",
            "sales",
            "business development",
            "account manager",
            "consultant",
            "service manager",
            "customer service",
        ],
        "SALES": [
            "marketing",
            "sales",
            "business development",
            "account manager",
            "service manager",
            "customer service",
            "waiter",
        ],
        "HEALTHCARE": ["therapist", "counselor", "mental health", "nurse", "medical", "healthcare", "dental"],
        "ADVOCATE": ["attorney", "law", "legal", "compliance"],
        "ENGINEERING": ["engineer", "developer", "technician", "software", "mechanical", "electrical", "service technician"],
        "INFORMATION-TECHNOLOGY": ["engineer", "developer", "technician", "software", "it", "python", "sql", "cloud", "data engineer"],
        "AUTOMOBILE": ["engineer", "technician", "automotive", "service technician"],
        "CHEF": [
            "restaurant",
            "hospitality",
            "food",
            "dining",
            "service manager",
            "kitchen",
            "chef",
            "waiter",
            "food service",
        ],
        "FINANCE": ["finance", "financial", "budget", "accountant", "accounting"],
        "BANKING": ["banking", "bank", "loan", "credit"],
        "ACCOUNTANT": ["accountant", "accounting", "tax", "payroll", "bookkeeping"],
        "TEACHER": ["teacher", "lecturer", "tutor", "education", "instructor"],
        "FITNESS": ["fitness", "trainer", "coach", "gym", "service-oriented", "guest experience"],
        "DESIGNER": ["designer", "design", "creative", "graphic"],
        "ARTS": ["designer", "creative", "arts", "artist"],
        "CONSULTANT": ["consultant", "advisory", "strategy"],
        "BPO": ["customer service", "call handling", "guest service", "service manager", "waiter"],
    }

    for category, keywords in category_keywords.items():
        if any(keyword in job_text for keyword in keywords):
            likely_categories.add(category)

    return likely_categories


def clamp_score(score):
    # keep recruiter rerank scores inside the normal ui range
    if score < 0:
        return 0.0
    if score > 1:
        return 1.0
    return float(score)


def get_recruiter_category_bonus(likely_categories, resume_category):
    # add a small domain bonus when the resume category matches the job area
    if not likely_categories or resume_category == "unknown":
        return 0.0

    if resume_category in likely_categories:
        return 0.05

    return 0.0


def is_marketing_job(job):
    # detect marketing-style roles so stronger media bonuses can be applied
    job_text = f"{job.title or ''} {job.description or ''}".lower()
    marketing_keywords = [
        "marketing",
        "media",
        "communications",
        "brand",
        "advertising",
        "campaign",
    ]
    return any(keyword in job_text for keyword in marketing_keywords)


def get_marketing_category_bonus(job, resume_category):
    # give pr and digital-media a slightly stronger boost for marketing roles
    if not is_marketing_job(job):
        return 0.0

    if resume_category in {"PUBLIC-RELATIONS", "DIGITAL-MEDIA"}:
        return 0.03

    if resume_category in {"BUSINESS-DEVELOPMENT", "SALES", "DESIGNER", "ARTS"}:
        return 0.01

    return 0.0


def get_recruiter_core_skill_bonus(analysis):
    # reward stronger core skill coverage a bit more than generic overlap
    core_matching_count = int(analysis.get("core_matching_count", 0))

    if core_matching_count >= 5:
        return 0.05
    if core_matching_count >= 3:
        return 0.03
    if core_matching_count >= 1:
        return 0.01
    return 0.0


def get_recruiter_generic_only_penalty(analysis):
    # reduce scores that rely mostly on generic transferable skills
    core_matching_count = int(analysis.get("core_matching_count", 0))
    generic_matching_count = int(analysis.get("generic_matching_count", 0))

    if generic_matching_count >= 3 and core_matching_count == 0:
        return 0.08
    if generic_matching_count >= 2 and core_matching_count <= 1:
        return 0.04
    return 0.0


def is_hospitality_or_service_job(job):
    # detect restaurant and service roles so unrelated categories can be penalized a bit
    job_text = f"{job.title or ''} {job.description or ''}".lower()
    hospitality_keywords = [
        "restaurant",
        "hospitality",
        "food",
        "dining",
        "service manager",
        "kitchen",
        "chef",
        "waiter",
        "customer service",
    ]
    return any(keyword in job_text for keyword in hospitality_keywords)


def get_recruiter_domain_mismatch_penalty(job, likely_categories, resume_category, base_score):
    # lower obviously unrelated categories for hospitality and service roles unless text match is very strong
    if not is_hospitality_or_service_job(job):
        return 0.0

    if resume_category in likely_categories or resume_category == "unknown":
        return 0.0

    if base_score >= 0.8:
        return 0.0

    if resume_category in {"ADVOCATE", "TEACHER", "INFORMATION-TECHNOLOGY"}:
        return 0.05

    return 0.02


def rerank_recruiter_match(job, resume, metadata, analysis):
    # rerank the faiss candidates using small domain-aware score adjustments
    base_score = float(analysis.get("final_score", 0.0))
    likely_categories = get_likely_job_categories(job)
    resume_category = parse_resume_category(resume, metadata)
    category_bonus = get_recruiter_category_bonus(likely_categories, resume_category)
    marketing_category_bonus = get_marketing_category_bonus(job, resume_category)
    core_skill_bonus = get_recruiter_core_skill_bonus(analysis)
    generic_only_penalty = get_recruiter_generic_only_penalty(analysis)
    domain_mismatch_penalty = get_recruiter_domain_mismatch_penalty(
        job,
        likely_categories,
        resume_category,
        base_score,
    )
    recruiter_score = clamp_score(
        base_score
        + category_bonus
        + marketing_category_bonus
        + core_skill_bonus
        - generic_only_penalty
        - domain_mismatch_penalty
    )

    return {
        "recruiter_score": recruiter_score,
        "resume_category": resume_category,
        "likely_categories": sorted(likely_categories),
        "category_bonus": category_bonus,
        "marketing_category_bonus": marketing_category_bonus,
        "core_skill_bonus": core_skill_bonus,
        "generic_only_penalty": generic_only_penalty,
        "domain_mismatch_penalty": domain_mismatch_penalty,
    }


def unique_by_id(items, id_key):
    # keep only one item for each id
    unique_items = []
    seen_ids = set()

    for item in items:
        item_id = item.get(id_key)
        if item_id in seen_ids:
            continue

        seen_ids.add(item_id)
        unique_items.append(item)

    return unique_items


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

    results = [
        {
            "id": m.id,
            "resume": m.resume.filename,
            "job_title": m.job_posting.title,
            **build_score_data(m.match_score),
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
                **build_score_data(top.match_score),
                "generated_at": top.generated_at
            })

    return {"top_matches": unique_by_id(results, "resume")}

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

    results = [
        {
            "job_id": m.job_posting.id,
            "job_title": m.job_posting.title,
            **build_score_data(m.match_score),
            "generated_at": m.generated_at
        }
        for m in matches
    ]
    return unique_by_id(results, "id")
    return unique_by_id(results, "job_id")


@router.get("/debug/")
def debug_matches(db: Session = Depends(get_db)):
    matches = db.query(Match).all()
    results = [
        {
            "id": m.id,
            "user_id": m.user_id,
            "resume": m.resume.filename,
            "job_title": m.job_posting.title,
            **build_score_data(m.match_score),
        }
        for m in matches
    ]
    return unique_by_id(results, "id")
    return unique_by_id(results, "id")


@router.get("/by-job/{job_id}")
def get_matches_for_job(
    job_id: int,
    current_user: User = Depends(require_recruiter),
    db: Session = Depends(get_db)
):
    # make sure the recruiter can only view their own job rankings
    job = (
        db.query(JobPosting)
        .filter(JobPosting.id == job_id, JobPosting.recruiter_id == current_user.id)
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # create an embedding from the selected job text
    job_text = job.description or ""
    job_embedding = generate_embedding(job_text)

    # search the separate resume faiss index for the closest resumes
    faiss_results = resume_faiss_search(job_embedding, k=20)
    ranked_resumes = []
    seen_resume_ids = set()

    for result in faiss_results:
        metadata = result.get("metadata") or {}
        resume_id = metadata.get("resume_id")
        if resume_id is None or resume_id in seen_resume_ids:
            continue

        resume = db.query(Resume).filter(Resume.id == resume_id).first()
        if not resume:
            continue

        seen_resume_ids.add(resume_id)

        # score the resume against the selected job using the shared hybrid logic
        resume_text = resume.text_content or ""
        embedding_score = float(result.get("score", 0.0))
        analysis = multi_step_match_analysis(resume_text, job_text, embedding_score=embedding_score)
        rerank_data = rerank_recruiter_match(job, resume, metadata, analysis)
        final_score = rerank_data["recruiter_score"]

        # save or update the ranked result in the matches table
        saved_match = (
            db.query(Match)
            .filter(Match.resume_id == resume.id, Match.job_posting_id == job.id)
            .first()
        )
        if saved_match:
            saved_match.match_score = final_score
            saved_match.generated_at = datetime.utcnow()
        else:
            saved_match = Match(
                user_id=resume.user_id,
                resume_id=resume.id,
                job_posting_id=job.id,
                match_score=final_score,
                created_at=datetime.utcnow(),
                generated_at=datetime.utcnow(),
            )
            db.add(saved_match)
            db.flush()

        ranked_resumes.append({
            "resume_id": resume.id,
            "filename": resume.filename,
            "user_id": resume.user_id,
            **build_score_data(final_score),
            "base_final_score": float(analysis.get("final_score", 0.0)),
            "resume_category": rerank_data["resume_category"],
            "likely_categories": rerank_data["likely_categories"],
            "category_bonus": rerank_data["category_bonus"],
            "marketing_category_bonus": rerank_data["marketing_category_bonus"],
            "core_skill_bonus": rerank_data["core_skill_bonus"],
            "generic_only_penalty": rerank_data["generic_only_penalty"],
            "domain_mismatch_penalty": rerank_data["domain_mismatch_penalty"],
            "generated_at": saved_match.generated_at,
            "reasoning": {
                "matching_skills": analysis.get("matching_skills", []),
                "missing_skills": analysis.get("missing_skills", []),
                "core_matching_skills": analysis.get("core_matching_skills", []),
                "generic_matching_skills": analysis.get("generic_matching_skills", []),
                "explanation": generate_match_explanation(resume_text, job_text, final_score),
            },
        })

    db.commit()

    ranked_resumes.sort(key=lambda item: item.get("final_score", 0.0), reverse=True)
    return unique_by_id(ranked_resumes, "resume_id")


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
        embedding_score = float(result.get("score", 0.0))
        analysis = multi_step_match_analysis(cv_text, job_text, embedding_score=embedding_score)
        final_score = float(analysis.get("final_score", 0.0))
        matching_skills = analysis.get("matching_skills", [])
        missing_skills = analysis.get("missing_skills", [])

        # save or update the final hybrid score in the database
        saved_match = (
            db.query(Match)
            .filter(Match.resume_id == resume.id, Match.job_posting_id == job.id)
            .first()
        )
        if saved_match:
            saved_match.match_score = final_score
            saved_match.generated_at = datetime.utcnow()
        else:
            saved_match = Match(
                user_id=current_user.id,
                resume_id=resume.id,
                job_posting_id=job.id,
                match_score=final_score,
                created_at=datetime.utcnow(),
                generated_at=datetime.utcnow(),
            )
            db.add(saved_match)
            db.flush()

        # keep only first ~200 chars so response stays short
        description_preview = job_text[:200]

        matches.append({
            "id": saved_match.id,
            **build_score_data(final_score),
            "embedding_score": embedding_score,
            "skill_overlap_score": analysis.get("skill_overlap_score", 0.0),
            "final_score": final_score,
            "job_id": job.id,
            "title": job.title,
            "similarity_score": embedding_score,
            "description_preview": description_preview,
            "reasoning": {
                "matching_skills": matching_skills,
                "missing_skills": missing_skills,
                "explanation": generate_match_explanation(cv_text, job_text, final_score),
            },
        })

    # save all match rows before returning
    db.commit()

    # rank matches from highest score to lowest
    matches.sort(key=lambda item: item["final_score"], reverse=True)

    # return the ranked matches list directly
    return unique_by_id(matches, "job_id")
