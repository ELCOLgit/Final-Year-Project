import faiss
import numpy as np
from typing import Any, Dict, List


# minilm gives 384 numbers for each embedding vector
EMBEDDING_DIM = 384

# this faiss index uses inner product to measure similarity
index = faiss.IndexFlatIP(EMBEDDING_DIM)

# store metadata in the same order as vectors added to faiss
metadata_store: List[Dict[str, Any]] = []


def add_vector(embedding, metadata):
    # convert embedding to float32 numpy so faiss can read it
    vector = np.array(embedding, dtype=np.float32).reshape(1, -1)

    # add the vector into the faiss index
    index.add(vector)

    # save matching metadata so we can return it in search results
    metadata_store.append(metadata)


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
