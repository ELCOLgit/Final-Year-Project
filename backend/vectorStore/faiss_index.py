import json
from pathlib import Path
from typing import Any, Dict, List

import faiss
import numpy as np


# minilm gives 384 numbers for each embedding vector
EMBEDDING_DIM = 384

# store the faiss files inside backend/data
data_dir = Path(__file__).resolve().parent.parent / "data"
index_file = data_dir / "job_postings.faiss"
metadata_file = data_dir / "job_postings_metadata.json"


def create_empty_index():
    # this faiss index uses inner product to measure similarity
    return faiss.IndexFlatIP(EMBEDDING_DIM)


index = create_empty_index()

# store metadata in the same order as vectors added to faiss
metadata_store: List[Dict[str, Any]] = []


def load_index():
    # load the faiss index and metadata from disk if they exist
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
    # save the faiss index and metadata to disk
    data_dir.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_file))

    with open(metadata_file, "w", encoding="utf-8") as file:
        json.dump(metadata_store, file, indent=2)


def reset_index():
    # recreate the index and clear metadata
    global index, metadata_store
    index = create_empty_index()
    metadata_store = []
    save_index()


def add_vector(embedding, metadata):
    # convert embedding to float32 numpy so faiss can read it
    vector = np.array(embedding, dtype=np.float32).reshape(1, -1)

    # add the vector into the faiss index
    index.add(vector)

    # save matching metadata so we can return it in search results
    metadata_store.append(metadata)
    save_index()


def search(embedding, k=5):
    # convert query embedding to float32 numpy with shape (1, dim)
    query_vector = np.array(embedding, dtype=np.float32).reshape(1, -1)

    # run faiss search to get top k similar vectors
    scores, indices = index.search(query_vector, k)

    # build results as a list of score + metadata
    results = []
    for score, idx in zip(scores[0], indices[0]):
        # faiss returns -1 when there is no valid result, so skip it
        if idx == -1:
            continue

        results.append({
            "score": float(score),
            "metadata": metadata_store[idx],
        })

    return results


def index_size():
    # return total vectors currently stored in the faiss index
    return index.ntotal


# load saved faiss data when this file is imported
load_index()
