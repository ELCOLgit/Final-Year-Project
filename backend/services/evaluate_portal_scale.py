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
from backend.models import job_postings_model, match_model, resume_model, user_model  # noqa: F401
from backend.models.job_postings_model import JobPosting
from backend.models.resume_model import Resume
from backend.services.cvService import multi_step_match_analysis
from backend.utils.embedding_utils import generate_embedding
from backend.vectorStore.faiss_index import index_size as job_index_size
from backend.vectorStore.faiss_index import search as search_job_postings_faiss
from backend.vectorStore.resume_faiss_index import index_size as resume_index_size
from backend.vectorStore.resume_faiss_index import search as search_resumes_faiss


def run_analysis(cv_text, job_text, embedding_score):
    # hide debug prints from the shared scoring helper
    with redirect_stdout(StringIO()):
        return multi_step_match_analysis(
            cv_text,
            job_text,
            embedding_score=embedding_score,
        )


def get_resume_embedding(resume):
    # reuse the stored embedding when it exists, otherwise create one
    if resume.embedding and resume.embedding != "[]":
        try:
            stored_embedding = json.loads(resume.embedding)
            if stored_embedding:
                return stored_embedding
        except json.JSONDecodeError:
            pass

    return generate_embedding(resume.text_content or "")


def build_summary_stats(results):
    # turn a list of match results into simple summary numbers
    if not results:
        return {
            "sampled_matches": 0,
            "average_final_score": 0.0,
            "strong_matches": 0,
            "moderate_matches": 0,
            "weak_matches": 0,
        }

    total_score = sum(item.get("final_score", 0.0) for item in results)
    strong_matches = sum(1 for item in results if item.get("match_label") == "strong match")
    moderate_matches = sum(1 for item in results if item.get("match_label") == "moderate match")
    weak_matches = sum(1 for item in results if item.get("match_label") == "weak match")

    return {
        "sampled_matches": len(results),
        "average_final_score": total_score / len(results),
        "strong_matches": strong_matches,
        "moderate_matches": moderate_matches,
        "weak_matches": weak_matches,
    }


def get_example_matches(results, label, limit=3):
    # keep a few example matches for report output
    example_matches = [item for item in results if item.get("match_label") == label]
    example_matches.sort(key=lambda item: item.get("final_score", 0.0), reverse=True)
    return example_matches[:limit]


def evaluate_job_seeker_sample(db, sample_size=10, top_k=5):
    # sample current resumes and test resume to job matching
    sampled_results = []
    resumes = (
        db.query(Resume)
        .filter(Resume.text_content.isnot(None))
        .order_by(Resume.id.asc())
        .limit(sample_size)
        .all()
    )

    for resume in resumes:
        if not (resume.text_content or "").strip():
            continue

        resume_embedding = get_resume_embedding(resume)
        faiss_results = search_job_postings_faiss(resume_embedding, k=top_k)

        for result in faiss_results:
            metadata = result.get("metadata") or {}
            job_id = metadata.get("job_id")
            if job_id is None:
                continue

            job = db.query(JobPosting).filter(JobPosting.id == job_id).first()
            if not job or not (job.description or "").strip():
                continue

            analysis = run_analysis(
                resume.text_content or "",
                job.description or "",
                float(result.get("score", 0.0)),
            )
            sampled_results.append({
                "portal": "job seeker",
                "resume_id": resume.id,
                "job_id": job.id,
                "job_title": job.title,
                **analysis,
            })

    return {
        "summary": build_summary_stats(sampled_results),
        "results": sampled_results,
    }


def evaluate_recruiter_sample(db, sample_size=10, top_k=5):
    # sample current jobs and test job to resume matching
    sampled_results = []
    jobs = (
        db.query(JobPosting)
        .filter(JobPosting.description.isnot(None))
        .order_by(JobPosting.id.asc())
        .limit(sample_size)
        .all()
    )

    for job in jobs:
        if not (job.description or "").strip():
            continue

        job_embedding = generate_embedding(job.description or "")
        faiss_results = search_resumes_faiss(job_embedding, k=top_k)

        for result in faiss_results:
            metadata = result.get("metadata") or {}
            resume_id = metadata.get("resume_id")
            if resume_id is None:
                continue

            resume = db.query(Resume).filter(Resume.id == resume_id).first()
            if not resume or not (resume.text_content or "").strip():
                continue

            analysis = run_analysis(
                resume.text_content or "",
                job.description or "",
                float(result.get("score", 0.0)),
            )
            sampled_results.append({
                "portal": "recruiter",
                "resume_id": resume.id,
                "job_id": job.id,
                "job_title": job.title,
                **analysis,
            })

    return {
        "summary": build_summary_stats(sampled_results),
        "results": sampled_results,
    }


def print_summary(title, summary):
    # print one portal summary in a clear report-style block
    print(title)
    print(f"sampled matches      : {summary['sampled_matches']}")
    print(f"average final score  : {summary['average_final_score']:.2f}")
    print(f"strong matches       : {summary['strong_matches']}")
    print(f"moderate matches     : {summary['moderate_matches']}")
    print(f"weak matches         : {summary['weak_matches']}")


def print_examples(title, results, label):
    # print a few example matches for one score band
    print(title)
    example_matches = get_example_matches(results, label)

    if not example_matches:
        print("none")
        return

    for item in example_matches:
        print(
            f"resume {item['resume_id']} -> job {item['job_id']} ({item['job_title']}): "
            f"{item.get('final_score', 0.0):.2f} | {item.get('match_label', 'weak match')}"
        )


def main():
    # open one database session for the large-scale evaluation
    db = SessionLocal()

    try:
        total_jobs = db.query(JobPosting).count()
        total_resumes = db.query(Resume).count()

        job_seeker_data = evaluate_job_seeker_sample(db)
        recruiter_data = evaluate_recruiter_sample(db)
    finally:
        db.close()

    print("large-scale portal evaluation")
    print("-" * 72)
    print(f"total jobs            : {total_jobs}")
    print(f"total resumes         : {total_resumes}")
    print(f"total job embeddings  : {job_index_size()}")
    print(f"total resume embeddings: {resume_index_size()}")
    print()
    print_summary("job seeker sample summary", job_seeker_data["summary"])
    print_examples("example strong matches", job_seeker_data["results"], "strong match")
    print_examples("example weak matches", job_seeker_data["results"], "weak match")
    print()
    print_summary("recruiter sample summary", recruiter_data["summary"])
    print_examples("example strong matches", recruiter_data["results"], "strong match")
    print_examples("example weak matches", recruiter_data["results"], "weak match")


if __name__ == "__main__":
    main()
