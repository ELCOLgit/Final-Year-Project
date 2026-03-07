import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def compute_similarity_matrix(resume_texts, job_texts):
    # return empty list if one side has no text
    if not resume_texts or not job_texts:
        return []

    # turn all text into tf-idf vectors
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf = vectorizer.fit_transform(resume_texts + job_texts)

    # split vectors back into resume side and job side
    resume_vecs = tfidf[:len(resume_texts)]
    job_vecs = tfidf[len(resume_texts):]

    # compute cosine similarity for each resume-job pair
    sim_matrix = cosine_similarity(resume_vecs, job_vecs)
    return sim_matrix.round(3)


def cosine_distribution(embeddings):
    # if we have less than 2 embeddings, mean/std are just zero
    if embeddings is None or len(embeddings) < 2:
        return {"mean": 0.0, "std": 0.0}

    # convert to float32 numpy array so math is consistent
    vectors = np.array(embeddings, dtype=np.float32)

    # build cosine matrix between all embeddings
    sim_matrix = cosine_similarity(vectors)

    # only keep upper triangle so we do not double count pairs
    upper_idx = np.triu_indices_from(sim_matrix, k=1)
    pair_scores = sim_matrix[upper_idx]

    # return simple summary stats
    return {
        "mean": float(np.mean(pair_scores)),
        "std": float(np.std(pair_scores)),
    }


def precision_at_k(true_matches, retrieved_matches, k):
    # no retrieved items means precision is zero
    if not retrieved_matches or k <= 0:
        return 0.0

    # use only top-k retrieved items
    top_k = retrieved_matches[:k]

    # count how many top-k items are actually correct
    true_set = set(true_matches)
    correct = sum(1 for item in top_k if item in true_set)

    return correct / len(top_k)


def evaluate_pipeline():
    # sample cv and job text so we can test flow quickly
    resume_texts = [
        "python fastapi sql machine learning",
        "react javascript css frontend ui",
    ]
    job_texts = [
        "backend engineer with python and sql",
        "frontend developer with react and javascript",
        "data analyst using excel and tableau",
    ]

    # run the same similarity function used in the app
    sim_matrix = compute_similarity_matrix(resume_texts, job_texts)

    # convert sample text to vectors so we can inspect cosine distribution
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf = vectorizer.fit_transform(resume_texts + job_texts).toarray()
    distribution = cosine_distribution(tfidf)

    # pretend these are true good matches for resume 0
    true_matches = [0]

    # rank jobs for resume 0 by similarity score from high to low
    resume_zero_scores = list(enumerate(sim_matrix[0]))
    ranked_jobs = [job_id for job_id, _ in sorted(resume_zero_scores, key=lambda x: x[1], reverse=True)]

    # compute precision at k in a simple way
    p_at_1 = precision_at_k(true_matches, ranked_jobs, 1)
    p_at_3 = precision_at_k(true_matches, ranked_jobs, 3)

    return {
        "similarity_matrix": sim_matrix.tolist(),
        "cosine_distribution": distribution,
        "precision_at_1": p_at_1,
        "precision_at_3": p_at_3,
        "ranked_jobs_resume_0": ranked_jobs,
    }
