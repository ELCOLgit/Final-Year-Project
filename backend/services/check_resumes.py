import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    # make backend imports work when this script runs directly
    sys.path.append(project_root)

from backend.database import SessionLocal
from backend.models.match_model import Match  # noqa: F401
from backend.models.resume_model import Resume
from backend.models.user_model import User  # noqa: F401


def parse_dataset_resume_info(filename):
    # read dataset id and category from the saved filename when available
    dataset_resume_id = None
    category = None

    if filename and filename.startswith("dataset_resume_"):
        trimmed_name = filename.removeprefix("dataset_resume_")
        trimmed_name = trimmed_name.removesuffix(".txt")
        parts = trimmed_name.split("_", 1)
        dataset_resume_id = parts[0] if parts else None
        category = parts[1] if len(parts) > 1 else None

    return dataset_resume_id, category


def main():
    # open a database session
    db = SessionLocal()

    try:
        total_resumes = db.query(Resume).count()
        first_resumes = db.query(Resume).order_by(Resume.id.asc()).limit(15).all()

        # print the total number of resumes
        print(f"total resumes: {total_resumes}")
        print("\nfirst 15 resumes:")

        # print the first imported rows in a simple readable way
        for resume in first_resumes:
            dataset_resume_id, category = parse_dataset_resume_info(resume.filename)

            print(f"db resume id: {resume.id}")
            print(f"resume id: {dataset_resume_id if dataset_resume_id else 'not available'}")
            print(f"category: {category if category else 'not available'}")
            print(f"filename: {resume.filename}")
            print("---")
    finally:
        db.close()


if __name__ == "__main__":
    main()
