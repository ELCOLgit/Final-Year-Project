from pathlib import Path
import json
import sys

import pandas as pd

# add the project root so backend imports work when this file is run directly
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.database import Base, SessionLocal, engine
from backend.models import job_postings_model, match_model, resume_model, user_model
from backend.models.job_postings_model import JobPosting
from backend.nlp.preprocessing import preprocess_text
from backend.utils.embedding_utils import generate_embedding
from backend.vectorStore.faiss_index import add_vector


# make sure the database tables exist before importing data
Base.metadata.create_all(bind=engine)

# set the csv path
data_file = Path(__file__).resolve().parent.parent / "data" / "postings.csv"

# load only the first 100 rows for testing
df = pd.read_csv(data_file, nrows=100)

# print the dataset columns first
print("column names:")
print(list(df.columns))

# use the linkedin dataset columns for title and description
title_column = "title"
description_column = "description"

# remove rows where title or description is missing
df = df.dropna(subset=[title_column, description_column])

db = SessionLocal()
imported_count = 0
skipped_count = 0

try:
    for _, row in df.iterrows():
        title = str(row[title_column]).strip()
        description = str(row[description_column]).strip()

        # skip rows that become empty after trimming
        if not title or not description:
            continue

        # clean the description using the existing preprocessing function
        cleaned_description = preprocess_text(description)

        # check if the same job is already in the database
        existing_job = (
            db.query(JobPosting)
            .filter(
                JobPosting.title == title,
                JobPosting.description == cleaned_description
            )
            .first()
        )

        # skip duplicate jobs
        if existing_job:
            print(
                f"title: {title} | database id: {existing_job.id} | "
                f"embedding created: no | added to faiss: no | status: skipped"
            )
            skipped_count += 1
            continue

        # preprocess the description before creating the embedding
        cleaned_description = preprocess_text(description)

        # save the job in the database first so it gets an id
        job_posting = JobPosting(
            title=title,
            description=cleaned_description
        )

        db.add(job_posting)
        db.flush()

        embedding_created = "no"
        added_to_faiss = "no"

        # generate the embedding from the cleaned description
        embedding = generate_embedding(cleaned_description)
        embedding_created = "yes"

        # save the embedding in the database as json text
        job_posting.embedding = json.dumps(embedding)

        # add the embedding to faiss with the job id as metadata
        add_vector(embedding, {"job_id": job_posting.id})
        added_to_faiss = "yes"

        print(
            f"title: {title} | database id: {job_posting.id} | "
            f"embedding created: {embedding_created} | added to faiss: {added_to_faiss}"
        )
        imported_count += 1

    db.commit()

finally:
    db.close()

# print a simple summary at the end
print()
print(f"rows imported into database: {imported_count}")
print(f"rows skipped as duplicates: {skipped_count}")
