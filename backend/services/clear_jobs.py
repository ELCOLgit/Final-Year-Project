from pathlib import Path
import sys


# add the project root so backend imports work when this file is run directly
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.database import SessionLocal
from backend.models import job_postings_model, match_model, resume_model, user_model
from backend.models.job_postings_model import JobPosting
from backend.vectorStore import faiss_index


# open the database session
db = SessionLocal()

try:
    # delete all rows from the job postings table
    db.query(JobPosting).delete()
    db.commit()

    # clear faiss too so the index matches the database
    faiss_index.reset_index()

    # check how many jobs are left after deleting
    remaining_jobs = db.query(JobPosting).count()
    print(f"total number of remaining jobs after delete: {remaining_jobs}")

finally:
    # close the database session
    db.close()
