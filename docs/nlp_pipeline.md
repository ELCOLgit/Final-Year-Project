# nlp matching pipeline (simple overview)

this project matches cvs to jobs by sending text through a few clear steps.

## quick flow

```text
pdf upload
   |
   v
text extraction
   |
   v
preprocessing
   |
   v
embedding generation
   |
   v
faiss storage/index
   |
   v
match search
   |
   v
frontend display
```

## step-by-step

### 1) pdf upload
- user uploads a cv pdf in the job seeker portal.
- backend receives the file at the resume upload endpoint.

### 2) text extraction
- backend reads the pdf and extracts raw text.
- this gives us plain text we can process.

### 3) preprocessing
- text is cleaned before vectorizing.
- we lowercase text, remove weird chars, and collapse extra spaces.
- this makes input more consistent.

### 4) embedding generation
- cleaned text is converted into a numeric vector (embedding).
- same idea for job descriptions.
- vectors let us compare meaning/similarity with math.

### 5) faiss storage
- job embeddings are added to faiss index (`IndexFlatIP`).
- metadata (like `job_id`) is stored with vector order.
- embedding is also saved in the database as json.

### 6) match search
- when searching for a resume, backend loads resume embedding.
- backend calls faiss search to get top similar jobs.
- results include similarity score + metadata.
- metadata is used to load full job data from database.

### 7) frontend display
- frontend calls `/matches/search/{resume_id}`.
- ui shows matched job title + similarity score.
- user can open compare view to see cv text vs job description with highlights.

## why this pipeline works
- preprocessing makes text cleaner and more stable.
- embeddings convert text into comparable numbers.
- faiss makes nearest-neighbor search fast.
- backend returns useful info, and frontend shows it in a readable way.
