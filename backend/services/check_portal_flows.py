import json
import os
import sys
from contextlib import redirect_stdout
from io import StringIO


project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    # make backend imports work when this script runs directly
    sys.path.append(project_root)

from backend.database import SessionLocal
from backend.models.job_postings_model import JobPosting  # noqa: F401
from backend.models.match_model import Match  # noqa: F401
from backend.models.resume_model import Resume
from backend.models.user_model import User  # noqa: F401
from backend.services.cvService import generate_match_explanation, multi_step_match_analysis
from backend.utils.embedding_utils import generate_embedding
from backend.vectorStore.faiss_index import search as search_job_postings_faiss
from backend.vectorStore.resume_faiss_index import search as search_resumes_faiss


def print_check(label, passed, detail=""):
    # print one simple pass fail line
    status = "PASS" if passed else "FAIL"
    if detail:
        print(f"[{status}] {label}: {detail}")
    else:
        print(f"[{status}] {label}")


def run_analysis_silently(cv_text, job_text, embedding_score):
    # hide debug prints from the shared scoring helpers
    with redirect_stdout(StringIO()):
        analysis = multi_step_match_analysis(
            cv_text,
            job_text,
            embedding_score=embedding_score,
        )
        explanation = generate_match_explanation(
            cv_text,
            job_text,
            analysis.get("final_score", 0.0),
        )

    return analysis, explanation


def check_job_seeker_flow(db):
    # test the resume to jobs flow used by job seekers
    print("job seeker flow")

    resume = db.query(Resume).filter(Resume.text_content.isnot(None)).order_by(Resume.id.asc()).first()
    if not resume or not (resume.text_content or "").strip():
        print_check("cv input", False, "no resume with text found")
        return

    print_check("cv input", True, f"resume db id {resume.id}")

    resume_embedding = None
    if resume.embedding and resume.embedding != "[]":
        try:
            resume_embedding = json.loads(resume.embedding)
        except json.JSONDecodeError:
            resume_embedding = None

    if not resume_embedding:
        resume_embedding = generate_embedding(resume.text_content or "")

    print_check("embedding generation", bool(resume_embedding), f"vector size {len(resume_embedding) if resume_embedding else 0}")

    faiss_results = search_job_postings_faiss(resume_embedding, k=5) if resume_embedding else []
    print_check("search against job_postings.faiss", bool(faiss_results), f"{len(faiss_results)} results")

    if not faiss_results:
        print_check("ranked jobs returned", False, "no ranked jobs found")
        print_check("explanation fields returned", False, "no job result to explain")
        return

    ranked_job_results = []
    explanation_ok = False

    for result in faiss_results:
        metadata = result.get("metadata") or {}
        job_id = metadata.get("job_id")
        if job_id is None:
            continue

        job = db.query(JobPosting).filter(JobPosting.id == job_id).first()
        if not job:
            continue

        analysis, explanation = run_analysis_silently(
            resume.text_content or "",
            job.description or "",
            float(result.get("score", 0.0)),
        )

        ranked_job_results.append(job_id)
        if explanation and analysis.get("matching_skills") is not None and analysis.get("missing_skills") is not None:
            explanation_ok = True

    print_check("ranked jobs returned", bool(ranked_job_results), f"{len(ranked_job_results)} ranked jobs")
    print_check("explanation fields returned", explanation_ok, "matching skills, missing skills, and explanation checked")


def check_recruiter_flow(db):
    # test the job to resumes flow used by recruiters
    print("\nrecruiter flow")

    job = db.query(JobPosting).filter(JobPosting.description.isnot(None)).order_by(JobPosting.id.asc()).first()
    if not job or not (job.description or "").strip():
        print_check("job input", False, "no job with description found")
        return

    print_check("job input", True, f"job id {job.id}")

    job_embedding = generate_embedding(job.description or "")
    print_check("embedding generation", bool(job_embedding), f"vector size {len(job_embedding) if job_embedding else 0}")

    faiss_results = search_resumes_faiss(job_embedding, k=5) if job_embedding else []
    print_check("search against resumes.faiss", bool(faiss_results), f"{len(faiss_results)} results")

    if not faiss_results:
        print_check("ranked resumes returned", False, "no ranked resumes found")
        print_check("explanation fields returned", False, "no resume result to explain")
        return

    ranked_resume_results = []
    explanation_ok = False

    for result in faiss_results:
        metadata = result.get("metadata") or {}
        resume_id = metadata.get("resume_id")
        if resume_id is None:
            continue

        resume = db.query(Resume).filter(Resume.id == resume_id).first()
        if not resume:
            continue

        analysis, explanation = run_analysis_silently(
            resume.text_content or "",
            job.description or "",
            float(result.get("score", 0.0)),
        )

        ranked_resume_results.append(resume_id)
        if explanation and analysis.get("matching_skills") is not None and analysis.get("missing_skills") is not None:
            explanation_ok = True

    print_check("ranked resumes returned", bool(ranked_resume_results), f"{len(ranked_resume_results)} ranked resumes")
    print_check("explanation fields returned", explanation_ok, "matching skills, missing skills, and explanation checked")


def main():
    # open one db session for the checks
    db = SessionLocal()

    try:
        check_job_seeker_flow(db)
        check_recruiter_flow(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
