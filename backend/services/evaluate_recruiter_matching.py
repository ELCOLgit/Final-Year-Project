import os
import sys
from contextlib import redirect_stdout
from io import StringIO


project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    # make backend imports work when this script runs directly
    sys.path.append(project_root)

from backend.database import SessionLocal
from backend.models import job_postings_model, match_model, resume_model, user_model  # noqa: F401
from backend.models.job_postings_model import JobPosting
from backend.models.resume_model import Resume
from backend.services.cvService import compare_matching_methods, generate_match_explanation, multi_step_match_analysis
from backend.utils.embedding_utils import generate_embedding
from backend.vectorStore.resume_faiss_index import search as search_resumes_faiss


def run_match_analysis(resume_text, job_text, embedding_score):
    # hide helper debug prints so the output stays easy to read
    with redirect_stdout(StringIO()):
        method_scores = compare_matching_methods(resume_text, job_text)
        analysis = multi_step_match_analysis(
            resume_text,
            job_text,
            embedding_score=embedding_score,
        )
        explanation = generate_match_explanation(
            resume_text,
            job_text,
            analysis.get("final_score", 0.0),
        )

    return method_scores, analysis, explanation


def print_result(job, resume, method_scores, analysis, explanation, rank_number):
    # print one ranked resume result in a report-style block
    print(f"rank {rank_number}")
    print(f"resume id: {resume.id}")
    print(f"final score: {analysis.get('final_score', 0.0):.2f}")
    print(f"ats score: {method_scores.get('ats_score', 0.0):.2f}")
    print(f"tfidf score: {method_scores.get('tfidf_score', 0.0):.2f}")
    print(f"embedding score: {method_scores.get('embedding_score', 0.0):.2f}")
    print(f"match label: {analysis.get('match_label', 'weak match')}")
    print(f"matching skills: {analysis.get('matching_skills', [])}")
    print(f"missing skills: {analysis.get('missing_skills', [])}")
    print(f"explanation: {explanation}")
    print("-" * 72)


def main():
    # open one database session for the evaluation
    db = SessionLocal()

    try:
        selected_jobs = (
            db.query(JobPosting)
            .filter(JobPosting.description.isnot(None))
            .order_by(JobPosting.id.asc())
            .limit(3)
            .all()
        )

        if not selected_jobs:
            print("no job postings found")
            return

        for job in selected_jobs:
            job_text = job.description or ""
            if not job_text.strip():
                continue

            job_embedding = generate_embedding(job_text)
            faiss_results = search_resumes_faiss(job_embedding, k=5)

            print("=" * 72)
            print(f"job id: {job.id}")
            print(f"job title: {job.title}")
            print("=" * 72)

            if not faiss_results:
                print("no resume matches found")
                continue

            seen_resume_ids = set()
            rank_number = 1

            for result in faiss_results:
                metadata = result.get("metadata") or {}
                resume_id = metadata.get("resume_id")

                if resume_id is None or resume_id in seen_resume_ids:
                    continue

                resume = db.query(Resume).filter(Resume.id == resume_id).first()
                if not resume or not (resume.text_content or "").strip():
                    continue

                seen_resume_ids.add(resume_id)

                method_scores, analysis, explanation = run_match_analysis(
                    resume.text_content or "",
                    job_text,
                    float(result.get("score", 0.0)),
                )

                print_result(job, resume, method_scores, analysis, explanation, rank_number)
                rank_number += 1
    finally:
        db.close()


if __name__ == "__main__":
    main()
