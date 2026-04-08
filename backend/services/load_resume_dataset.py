import json
import os
import sys
from collections import Counter

import pandas as pd

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    # make backend imports work when this script runs directly
    sys.path.append(project_root)

from backend.database import SessionLocal
from backend.models.match_model import Match  # noqa: F401
from backend.models.resume_model import Resume
from backend.models.user_model import User  # noqa: F401
from backend.nlp.preprocessing import preprocess_text
from backend.utils.embedding_utils import generate_embedding
from backend.vectorStore.resume_faiss_index import add_vector as add_resume_vector


def build_resume_filename(dataset_resume_id, category):
    # keep the dataset id and category in the stored filename
    filename = f"dataset_resume_{dataset_resume_id}"
    if pd.notna(category) and str(category).strip():
        filename += f"_{str(category).strip()}"
    filename += ".txt"
    return filename


def main():
    # build the csv path relative to this file
    csv_path = os.path.join(project_root, "backend", "data", "Resume.csv")

    # load the full dataset so every category can be included
    resume_data = pd.read_csv(csv_path)
    db = SessionLocal()

    try:
        # track current dataset ids and cleaned text so duplicates are skipped
        existing_resumes = db.query(Resume).all()
        existing_dataset_ids = set()
        seen_resume_texts = set()

        for resume in existing_resumes:
            filename = resume.filename or ""
            if filename.startswith("dataset_resume_"):
                trimmed_name = filename.removeprefix("dataset_resume_").removesuffix(".txt")
                parts = trimmed_name.split("_", 1)
                if parts and parts[0]:
                    existing_dataset_ids.add(parts[0])

            cleaned_existing_text = preprocess_text(str(resume.text_content or ""))
            if cleaned_existing_text:
                seen_resume_texts.add(cleaned_existing_text)

        total_rows_read = 0
        unique_resumes_inserted = 0
        duplicates_skipped = 0
        total_resume_embeddings_created = 0
        total_metadata_entries_written = 0
        category_counts = Counter()

        for _, row in resume_data.iterrows():
            dataset_resume_id = row.get("ID")
            category = row.get("Category")
            resume_text = row.get("Resume_str")
            total_rows_read += 1

            # skip rows with missing or empty resume text
            if pd.isna(resume_text) or not str(resume_text).strip():
                duplicates_skipped += 1
                continue

            # clean the text before creating the embedding
            cleaned_text = preprocess_text(str(resume_text))
            if not cleaned_text:
                duplicates_skipped += 1
                continue

            # skip rows already stored in the database by dataset id or resume text
            dataset_resume_id_text = str(dataset_resume_id).strip() if pd.notna(dataset_resume_id) else ""
            if dataset_resume_id_text and dataset_resume_id_text in existing_dataset_ids:
                duplicates_skipped += 1
                continue

            if cleaned_text in seen_resume_texts:
                duplicates_skipped += 1
                continue

            embedding = generate_embedding(cleaned_text)
            if not embedding:
                duplicates_skipped += 1
                continue

            # keep the original dataset id and category inside the filename label
            filename = build_resume_filename(dataset_resume_id, category)

            # save the resume row into the existing resumes table
            resume = Resume(
                user_id=None,
                filename=filename,
                text_content=cleaned_text,
                embedding=json.dumps(embedding),
            )
            db.add(resume)
            db.flush()

            # add exactly one vector and one metadata row for this unique resume
            category_name = str(category).strip() if pd.notna(category) and str(category).strip() else "unknown"
            add_resume_vector(
                embedding,
                {
                    "resume_id": resume.id,
                    "dataset_resume_id": dataset_resume_id_text or None,
                    "category": category_name,
                },
            )

            if dataset_resume_id_text:
                existing_dataset_ids.add(dataset_resume_id_text)
            seen_resume_texts.add(cleaned_text)
            unique_resumes_inserted += 1
            total_resume_embeddings_created += 1
            total_metadata_entries_written += 1
            category_counts[category_name] += 1

        db.commit()

        print(f"total rows read: {total_rows_read}")
        print(f"total unique resumes inserted into db: {unique_resumes_inserted}")
        print(f"total duplicates skipped: {duplicates_skipped}")
        print(f"total resume embeddings created: {total_resume_embeddings_created}")
        print(f"total metadata entries written: {total_metadata_entries_written}")
        print("breakdown of resumes per category:")
        for category_name, count in sorted(category_counts.items()):
            print(f"{category_name}: {count}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
