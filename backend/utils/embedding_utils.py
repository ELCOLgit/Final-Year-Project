from sklearn.feature_extraction.text import HashingVectorizer


# use 384 because this matches the size expected by our faiss index
EMBEDDING_DIM = 384

# hashing vectorizer is simple and always gives fixed-size vectors
_vectorizer = HashingVectorizer(
    n_features=EMBEDDING_DIM,
    alternate_sign=False,
    norm="l2",
)


def generate_embedding(text: str):
    # make sure we always pass a string
    safe_text = text or ""

    # transform text into a fixed-size numeric vector
    vector = _vectorizer.transform([safe_text]).toarray()[0]

    # convert numpy values to normal python floats for json storage
    return [float(v) for v in vector]
