import json
import os
import sys
from collections import Counter
from pathlib import Path


project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    # make backend imports work when this script runs directly
    sys.path.append(project_root)

from backend.database import SessionLocal
from backend.models import match_model, resume_model, user_model  # noqa: F401
from backend.models.resume_model import Resume


def main():
    # build the metadata path once so the script is easy to follow
    metadata_path = Path(project_root) / "backend" / "data" / "resumes_metadata.json"

    if metadata_path.exists():
        with open(metadata_path, "r", encoding="utf-8") as file:
            metadata = json.load(file)
    else:
        metadata = []

    # collect resume ids from the metadata file
    metadata_resume_ids = []
    for item in metadata:
        resume_id = item.get("resume_id")
        if resume_id is not None:
            metadata_resume_ids.append(resume_id)

    total_metadata_entries = len(metadata)
    unique_resume_ids = set(metadata_resume_ids)
    resume_id_counts = Counter(metadata_resume_ids)
    duplicate_resume_ids = sorted(
        resume_id for resume_id, count in resume_id_counts.items() if count > 1
    )
    duplicate_count = len(duplicate_resume_ids)

    db = SessionLocal()

    try:
        # compare metadata ids against what is currently in the database
        db_resume_ids = {
            resume.id
            for resume in db.query(Resume).order_by(Resume.id.asc()).all()
        }
    finally:
        db.close()

    missing_from_db = sorted(unique_resume_ids - db_resume_ids)

    print(f"total metadata entries: {total_metadata_entries}")
    print(f"unique resume ids: {len(unique_resume_ids)}")
    print(f"duplicate count: {duplicate_count}")

    if duplicate_resume_ids:
        print(f"sample duplicates: {duplicate_resume_ids[:10]}")
    else:
        print("sample duplicates: none")

    print(f"metadata ids missing from db: {len(missing_from_db)}")
    if missing_from_db:
        print(f"sample metadata ids missing from db: {missing_from_db[:10]}")


if __name__ == "__main__":
    main()
