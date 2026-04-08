import os
import sys


project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    # make backend imports work when this script runs directly
    sys.path.append(project_root)

from backend.vectorStore import resume_faiss_index


def main():
    # recreate the resume faiss files from scratch
    resume_faiss_index.reset_index()
    print(f"resume faiss reset successfully. current size: {resume_faiss_index.index_size()}")


if __name__ == "__main__":
    main()
