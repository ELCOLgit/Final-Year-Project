from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def compute_similarity_matrix(resume_texts, job_texts):
    """Compute resume × job similarity matrix."""
    if not resume_texts or not job_texts:
        return []

    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf = vectorizer.fit_transform(resume_texts + job_texts)

    resume_vecs = tfidf[:len(resume_texts)]
    job_vecs = tfidf[len(resume_texts):]

    sim_matrix = cosine_similarity(resume_vecs, job_vecs)
    return sim_matrix.round(3)

