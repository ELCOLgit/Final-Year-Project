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
from backend.vectorStore.faiss_index import index_size as job_index_size
from backend.vectorStore.resume_faiss_index import index_size as resume_index_size


def print_line():
    # print a simple separator for report output
    print("-" * 72)


def run_sample_match(case_name, cv_text, job_text):
    # use the shared scoring logic and hide debug prints from helper functions
    method_scores = compare_matching_methods(cv_text, job_text)

    with redirect_stdout(StringIO()):
        analysis = multi_step_match_analysis(
            cv_text,
            job_text,
            embedding_score=method_scores.get("embedding_score", 0.0),
        )
        explanation = generate_match_explanation(
            cv_text,
            job_text,
            analysis.get("final_score", 0.0),
        )

    print_line()
    print(case_name)
    print(f"ats score       : {method_scores.get('ats_score', 0.0):.2f}")
    print(f"tfidf score     : {method_scores.get('tfidf_score', 0.0):.2f}")
    print(f"embedding score : {method_scores.get('embedding_score', 0.0):.2f}")
    print(f"final score     : {analysis.get('final_score', 0.0):.2f}")
    print(f"match label     : {analysis.get('match_label', 'weak match')}")
    print(f"explanation     : {explanation}")


def main():
    # open one database session for the report counts
    db = SessionLocal()

    try:
        total_jobs = db.query(JobPosting).count()
        total_resumes = db.query(Resume).count()
    finally:
        db.close()

    print("evaluation results")
    print_line()
    print("database and vector totals")
    print(f"total jobs in database    : {total_jobs}")
    print(f"total resumes in database : {total_resumes}")
    print(f"total job embeddings      : {job_index_size()}")
    print(f"total resume embeddings   : {resume_index_size()}")

    print()
    print("sample match results")

    sample_cases = [
        {
            "name": "sample 1: strong match",
            "cv_text": (
                "Data analyst with Python, SQL, Tableau, Excel, data visualization, "
                "machine learning, communication, and teamwork experience."
            ),
            "job_text": (
                "We need a data analyst with Python, SQL, Tableau, Excel, data visualization, "
                "machine learning, communication, and teamwork."
            ),
        },
        {
            "name": "sample 2: moderate match",
            "cv_text": (
                "Business analyst with Excel, SQL, communication, reporting, office tools, "
                "data processing, and customer support experience."
            ),
            "job_text": (
                "Looking for an operations analyst with Excel, SQL, data analysis, "
                "communication, office tools, and problem solving."
            ),
        },
        {
            "name": "sample 3: weak match",
            "cv_text": (
                "Creative photographer with portrait editing, lighting, event coverage, "
                "and social media content experience."
            ),
            "job_text": (
                "Hiring an accountant with budgeting, financial reporting, payroll, "
                "tax preparation, Excel, and bookkeeping."
            ),
        },
    ]

    for case in sample_cases:
        run_sample_match(case["name"], case["cv_text"], case["job_text"])

    print_line()


if __name__ == "__main__":
    main()
