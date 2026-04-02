from pathlib import Path
import sys


# add the project root so backend imports work when this file is run directly
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.database import SessionLocal
from backend.models import job_postings_model, match_model, resume_model, user_model
from backend.models.job_postings_model import JobPosting


# open the database session
db = SessionLocal()

try:
    # count the total number of job postings
    total_jobs = db.query(JobPosting).count()
    print(f"total number of job postings: {total_jobs}")

    # get the last 10 inserted jobs using the highest ids
    latest_jobs = (
        db.query(JobPosting)
        .order_by(JobPosting.id.desc())
        .limit(10)
        .all()
    )

    print("last 10 inserted job titles:")
    for job in latest_jobs:
        print(f"id: {job.id} | title: {job.title}")

finally:
    # close the database session
    db.close()
