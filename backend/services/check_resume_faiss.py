import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    # make backend imports work when this script runs directly
    sys.path.append(project_root)

from backend.vectorStore import faiss_index


def main():
    # load the current faiss files used by the project
    faiss_index.load_index()

    # print how many vectors exist in the current index
    total_embeddings = faiss_index.index_size()
    print(f"faiss embeddings currently stored: {total_embeddings}")

    # check whether the current metadata includes resume ids
    linked_resume_ids = []
    for metadata in faiss_index.metadata_store:
        resume_id = metadata.get("resume_id")
        if resume_id is not None:
            linked_resume_ids.append(resume_id)

    if linked_resume_ids:
        print(f"resume embeddings currently stored in faiss: {len(linked_resume_ids)}")
        print("sample resume ids:")
        for resume_id in linked_resume_ids[:5]:
            print(resume_id)
    else:
        print("resume embeddings currently stored in faiss: 0")
        print("sample resume ids: none")
        print("note: the current faiss workflow stores job posting vectors, not resume vectors.")


if __name__ == "__main__":
    main()
