from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "AI Career Advisor backend is running"}

@app.post("/upload-cv/")
async def upload_cv(file: UploadFile):
    content = await file.read()
    return {"filename": file.filename, "size": len(content)}
