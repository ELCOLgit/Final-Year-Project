import json
import os
import sys
from pathlib import Path

import faiss


project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    # make local imports work when this script runs directly
    sys.path.append(project_root)


def main():
    # build the file paths for the resume faiss workflow
    data_dir = Path(project_root) / "backend" / "data"
    index_file = data_dir / "resumes.faiss"
    metadata_file = data_dir / "resumes_metadata.json"

    # load the resume faiss index and print its size
    if index_file.exists():
        index = faiss.read_index(str(index_file))
        print(f"resume embeddings stored: {index.ntotal}")
    else:
        print("resume embeddings stored: 0")
        print("sample resume ids: none")
        return

    # load the metadata file and print a few linked resume ids
    if metadata_file.exists():
        with open(metadata_file, "r", encoding="utf-8") as file:
            metadata = json.load(file)
    else:
        metadata = []

    sample_resume_ids = []
    for item in metadata[:5]:
        resume_id = item.get("resume_id")
        if resume_id is not None:
            sample_resume_ids.append(resume_id)

    if sample_resume_ids:
        print(f"sample resume ids: {sample_resume_ids}")
    else:
        print("sample resume ids: none")


if __name__ == "__main__":
    main()
