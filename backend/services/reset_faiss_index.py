from pathlib import Path
import sys


# add the project root so backend imports work when this file is run directly
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.vectorStore import faiss_index


# recreate the faiss index and clear saved metadata
faiss_index.reset_index()

# print a simple confirmation message
print(f"faiss index reset successfully. current size: {faiss_index.index_size()}")
