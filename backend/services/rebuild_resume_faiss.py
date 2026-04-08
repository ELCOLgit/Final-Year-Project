import json
import os
import sys


project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    # make backend imports work when this script runs directly
    sys.path.append(project_root)

from backend.database import SessionLocal
from backend.models import match_model, resume_model, user_model  # noqa: F401
from backend.models.resume_model import Resume
from backend.nlp.preprocessing import preprocess_text
from backend.utils.embedding_utils import generate_embedding
from backend.vectorStore.resume_faiss_index import add_vector as add_resume_vector
from backend.vectorStore.resume_faiss_index import reset_index as reset_resume_index


def parse_dataset_resume_info(filename):
    # read dataset id and category from the stored filename when available
    dataset_resume_id = None
    category = None

    if filename and filename.startswith("dataset_resume_"):
        trimmed_name = filename.removeprefix("dataset_resume_").removesuffix(".txt")
        parts = trimmed_name.split("_", 1)
        dataset_resume_id = parts[0] if parts else None
        category = parts[1] if len(parts) > 1 else None

    return dataset_resume_id, category


def main():
    # start from a clean resume faiss index and metadata file
    reset_resume_index()

    db = SessionLocal()

    try:
        resumes = db.query(Resume).order_by(Resume.id.asc()).all()
        total_resumes = len(resumes)
        written_resume_ids = set()
        seen_resume_texts = set()
        total_embeddings_written = 0

        for resume in resumes:
            if resume.id in written_resume_ids:
                continue

            raw_text = resume.text_content or ""
            if not raw_text.strip():
                continue

            # clean the text before embedding so the index stays consistent
            cleaned_text = preprocess_text(raw_text)
            if not cleaned_text:
                continue

            # skip duplicate resume text so the rebuilt index stays unique
            if cleaned_text in seen_resume_texts:
                continue

            embedding = generate_embedding(cleaned_text)
            if not embedding:
                continue

            # keep the stored resume data aligned with the rebuilt index
            resume.text_content = cleaned_text
            resume.embedding = json.dumps(embedding)

            dataset_resume_id, category = parse_dataset_resume_info(resume.filename)
            add_resume_vector(
                embedding,
                {
                    "resume_id": resume.id,
                    "dataset_resume_id": dataset_resume_id,
                    "category": category or "unknown",
                },
            )
            written_resume_ids.add(resume.id)
            seen_resume_texts.add(cleaned_text)
            total_embeddings_written += 1

        db.commit()

        print(f"total resumes in db: {total_resumes}")
        print(f"total embeddings created: {total_embeddings_written}")
        print("resume faiss rebuild completed")
    finally:
        db.close()


if __name__ == "__main__":
    main()
