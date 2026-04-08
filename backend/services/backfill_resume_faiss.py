import json
import os
import sys
from pathlib import Path


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


def load_embedded_resume_ids(metadata_path):
    # load the current resume ids already linked in the faiss metadata file
    if not metadata_path.exists():
        return set()

    with open(metadata_path, "r", encoding="utf-8") as file:
        metadata = json.load(file)

    embedded_resume_ids = set()
    for item in metadata:
        resume_id = item.get("resume_id")
        if resume_id is not None:
            embedded_resume_ids.add(resume_id)

    return embedded_resume_ids


def main():
    # build the metadata path once so the script stays easy to read
    metadata_path = Path(project_root) / "backend" / "data" / "resumes_metadata.json"

    # load the resume ids that are already indexed
    embedded_resume_ids = load_embedded_resume_ids(metadata_path)

    db = SessionLocal()

    try:
        resumes = db.query(Resume).order_by(Resume.id.asc()).all()
        total_resumes = len(resumes)
        already_embedded_count = sum(1 for resume in resumes if resume.id in embedded_resume_ids)
        missing_resumes = [resume for resume in resumes if resume.id not in embedded_resume_ids]
        missing_count = len(missing_resumes)
        new_embeddings_added = 0

        for resume in missing_resumes:
            raw_text = resume.text_content or ""
            if not raw_text.strip():
                continue

            # clean the stored text before embedding so the index uses consistent input
            cleaned_text = preprocess_text(raw_text)
            if not cleaned_text:
                continue

            embedding = generate_embedding(cleaned_text)
            if not embedding:
                continue

            # keep the database text and embedding in sync with the indexed value
            resume.text_content = cleaned_text
            resume.embedding = json.dumps(embedding)

            add_resume_vector(embedding, {"resume_id": resume.id})
            embedded_resume_ids.add(resume.id)
            new_embeddings_added += 1

        db.commit()

        print(f"total resumes in db: {total_resumes}")
        print(f"already embedded count: {already_embedded_count}")
        print(f"missing count: {missing_count}")
        print(f"new resume embeddings added: {new_embeddings_added}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
