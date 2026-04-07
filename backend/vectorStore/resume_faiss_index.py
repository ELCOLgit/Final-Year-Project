import json
from pathlib import Path
from typing import Any, Dict, List

import faiss
import numpy as np


# resume embeddings use the same vector size as the rest of the project
EMBEDDING_DIM = 384

# store the resume faiss files inside backend/data
data_dir = Path(__file__).resolve().parent.parent / "data"
index_file = data_dir / "resumes.faiss"
metadata_file = data_dir / "resumes_metadata.json"


def create_empty_index():
    # this faiss index uses inner product for similarity search
    return faiss.IndexFlatIP(EMBEDDING_DIM)


index = create_empty_index()

# keep metadata in the same order as the saved vectors
metadata_store: List[Dict[str, Any]] = []


def load_index():
    # load the saved resume index and metadata if they exist
    global index, metadata_store

    data_dir.mkdir(parents=True, exist_ok=True)

    if index_file.exists():
        index = faiss.read_index(str(index_file))
    else:
        index = create_empty_index()

    if metadata_file.exists():
        with open(metadata_file, "r", encoding="utf-8") as file:
            metadata_store = json.load(file)
    else:
        metadata_store = []


def save_index():
    # save the resume faiss index and metadata to disk
    data_dir.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_file))

    with open(metadata_file, "w", encoding="utf-8") as file:
        json.dump(metadata_store, file, indent=2)


def reset_index():
    # clear the resume faiss data and start fresh
    global index, metadata_store
    index = create_empty_index()
    metadata_store = []
    save_index()


def add_vector(embedding, metadata):
    # convert the embedding to the shape faiss expects
    vector = np.array(embedding, dtype=np.float32).reshape(1, -1)

    # add the vector and save its metadata
    index.add(vector)
    metadata_store.append(metadata)
    save_index()


def search(embedding, k=5):
    # search the resume index using the provided embedding
    query_vector = np.array(embedding, dtype=np.float32).reshape(1, -1)
    scores, indices = index.search(query_vector, k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue

        results.append({
            "score": float(score),
            "metadata": metadata_store[idx],
        })

    return results


def index_size():
    # return the number of stored resume vectors
    return index.ntotal


# load the saved files when this module is imported
load_index()
