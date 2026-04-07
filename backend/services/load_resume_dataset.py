import json
import os
import sys

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


def main():
    # build the csv path relative to this file
    csv_path = os.path.join(project_root, "backend", "data", "Resume.csv")

    # load only the first 20 rows for testing
    resume_data = pd.read_csv(csv_path).head(20)
    db = SessionLocal()

    try:
        for _, row in resume_data.iterrows():
            dataset_resume_id = row.get("ID")
            category = row.get("Category")
            resume_text = row.get("Resume_str")

            # skip rows with missing or empty resume text
            if pd.isna(resume_text) or not str(resume_text).strip():
                continue

            # clean the text before creating the embedding
            cleaned_text = preprocess_text(str(resume_text))
            embedding = generate_embedding(cleaned_text)
            embedding_created = "yes" if embedding else "no"

            # keep the original dataset id and category inside the filename label
            filename = f"dataset_resume_{dataset_resume_id}"
            if pd.notna(category) and str(category).strip():
                filename += f"_{str(category).strip()}"
            filename += ".txt"

            # save the resume row into the existing resumes table
            resume = Resume(
                user_id=None,
                filename=filename,
                text_content=cleaned_text,
                embedding=json.dumps(embedding),
            )
            db.add(resume)
            db.commit()
            db.refresh(resume)

            # resumes are not part of the current faiss index workflow
            added_to_faiss = "no"

            print(f"resume id: {dataset_resume_id}")
            print(f"category: {category}")
            print(f"embedding created: {embedding_created}")
            print(f"added to faiss: {added_to_faiss}")
            print("---")
    finally:
        db.close()


if __name__ == "__main__":
    main()
