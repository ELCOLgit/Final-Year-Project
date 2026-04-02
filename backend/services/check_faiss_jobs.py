from pathlib import Path
import sys


# add the project root so backend imports work when this file is run directly
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.vectorStore import faiss_index


# load the saved faiss files first
faiss_index.load_index()

# read the current number of embeddings in the faiss index
total_embeddings = faiss_index.index_size()
print(f"job embeddings currently stored in faiss: {total_embeddings}")

# print a few linked job ids if metadata is available
job_ids = []
for metadata in faiss_index.metadata_store[:5]:
    job_id = metadata.get("job_id")
    if job_id is not None:
        job_ids.append(job_id)

if job_ids:
    print(f"sample linked job ids: {job_ids}")
else:
    print("sample linked job ids: none available")
