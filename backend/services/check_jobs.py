from pathlib import Path
import sys


# add the project root so backend imports work when this file is run directly
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.database import SessionLocal
from backend.models import job_postings_model, match_model, resume_model, user_model
from backend.models.job_postings_model import JobPosting


# open a database session
db = SessionLocal()

try:
    # get all job postings from the database
    jobs = db.query(JobPosting).all()

    # print the total number of jobs
    print(f"total number of jobs: {len(jobs)}")

    # print the first 5 job titles
    print("first 5 job titles:")
    for job in jobs[:5]:
        print(job.title)

finally:
    # close the database session
    db.close()
