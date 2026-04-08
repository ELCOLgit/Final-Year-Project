import os
import sys


project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    # make backend imports work when this script runs directly
    sys.path.append(project_root)

from backend.database import SessionLocal
from backend.models import job_postings_model, match_model, resume_model, user_model  # noqa: F401
from backend.models.resume_model import Resume


def main():
    # remove every resume row from the database
    db = SessionLocal()

    try:
        resumes = db.query(Resume).order_by(Resume.id.asc()).all()
        total_resumes = len(resumes)

        for resume in resumes:
            db.delete(resume)

        db.commit()
        print(f"resumes cleared from database: {total_resumes}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
