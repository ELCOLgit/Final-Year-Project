import os
import sys
from collections import Counter
from contextlib import redirect_stdout
from io import StringIO


project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    # make backend imports work when this script runs directly
    sys.path.append(project_root)

from backend.controller.match_controller import (
    get_likely_job_categories,
    parse_resume_category,
    rerank_recruiter_match,
)
from backend.database import SessionLocal
from backend.models import job_postings_model, match_model, resume_model, user_model  # noqa: F401
from backend.models.job_postings_model import JobPosting
from backend.models.resume_model import Resume
from backend.services.cvService import multi_step_match_analysis
from backend.utils.embedding_utils import generate_embedding
from backend.vectorStore.resume_faiss_index import search as search_resumes_faiss


def get_expected_categories(job):
    # reuse the same likely category mapping as the real recruiter portal
    return get_likely_job_categories(job)


def category_match_comment(job, top_categories):
    # give a stricter comment on whether the top categories really fit the job area
    expected_categories = get_expected_categories(job)

    if not top_categories:
        return "no clear category pattern found"

    if not expected_categories:
        return "no simple expected category rule for this job, so review manually"

    matching_category_count = sum(1 for category in top_categories if category in expected_categories)

    if matching_category_count >= 2:
        return "top resume categories look reasonable for this job"

    if matching_category_count == 1:
        return "top resume categories only partially align with this job"

    return "top resume categories may not fully match the expected job area"


def main():
    # open one database session for the category evaluation
    db = SessionLocal()

    try:
        selected_jobs = (
            db.query(JobPosting)
            .filter(JobPosting.description.isnot(None))
            .order_by(JobPosting.id.asc())
            .limit(5)
            .all()
        )

        if not selected_jobs:
            print("no job postings found")
            return

        all_top_categories = Counter()

        for job in selected_jobs:
            job_text = job.description or ""
            if not job_text.strip():
                continue

            job_embedding = generate_embedding(job_text)
            faiss_results = search_resumes_faiss(job_embedding, k=20)

            print("=" * 72)
            print(f"job id: {job.id}")
            print(f"job title: {job.title}")

            if not faiss_results:
                print("no resume matches found")
                continue

            reranked_results = []
            top_categories = []
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
                resume_text = resume.text_content or ""

                with redirect_stdout(StringIO()):
                    analysis = multi_step_match_analysis(
                        resume_text,
                        job_text,
                        embedding_score=float(result.get("score", 0.0)),
                    )

                rerank_data = rerank_recruiter_match(job, resume, metadata, analysis)
                reranked_results.append({
                    "resume": resume,
                    "category": rerank_data["resume_category"],
                    "final_score": rerank_data["recruiter_score"],
                })

            reranked_results.sort(key=lambda item: item["final_score"], reverse=True)

            for rank_number, item in enumerate(reranked_results[:5], start=1):
                resume = item["resume"]
                category = item["category"]
                top_categories.append(category)
                all_top_categories[category] += 1

                print(
                    f"rank {rank_number}: resume {resume.id} | "
                    f"category: {category} | filename: {resume.filename}"
                )

            common_top_categories = [category for category, _ in Counter(top_categories).most_common(3)]
            print(f"top categories: {common_top_categories if common_top_categories else ['unknown']}")
            print(f"category check: {category_match_comment(job, common_top_categories)}")

        print("=" * 72)
        print("most common categories in top recruiter matches")
        for category, count in all_top_categories.most_common(10):
            print(f"{category}: {count}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
