from fastapi import APIRouter, UploadFile, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import SessionLocal, DATABASE_URL
from backend.models.resume_model import Resume
from backend.models.user_model import User
from backend.utils.dependencies import get_current_user
import fitz
from datetime import datetime
import os

router = APIRouter(
    prefix="/resumes",
    tags=["Resumes"]
)

# === Read DB session ===
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# === Debug route ===
@router.get("/db-path")
def get_db_path():
    return {"database_path": os.path.abspath(DATABASE_URL.replace("sqlite:///", ""))}

# === Extract text from PDF ===
def extract_text_from_pdf(file: UploadFile) -> str:
    pdf_text = ""
    with fitz.open(stream=file.file.read(), filetype="pdf") as pdf_doc:
        for page in pdf_doc:
            pdf_text += page.get_text("text")
    return pdf_text.strip()


# ==============================
#   UPLOAD RESUME (AUTH REQUIRED)
# ==============================
@router.post("/upload/")
async def upload_resume(
    file: UploadFile,
    current_user: User = Depends(get_current_user),   # <-- ORM user directly
    db: Session = Depends(get_db)
):
    # current_user is already a User model instance
    user = current_user  

    if not user:
        raise HTTPException(status_code=404, detail="Authenticated user not found")

    # Extract resume text
    text_content = extract_text_from_pdf(file)

    # Save resume
    resume = Resume(
        user_id=user.id,
        filename=file.filename,
        text_content=text_content,
        embedding="[]",
        upload_date=datetime.utcnow()
    )

    db.add(resume)
    db.commit()
    db.refresh(resume)

    return {
        "message": "Resume uploaded successfully",
        "uploaded_by": user.email,
        "user_id": user.id,
        "resume_id": resume.id,
        "filename": file.filename,
    }

# === List all resumes (DEBUG) ===
@router.get("/")
def list_resumes(db: Session = Depends(get_db)):
    resumes = db.query(Resume).all()
    return [
        {
            "id": r.id,
            "filename": r.filename,
            "upload_date": r.upload_date,
            "user_id": r.user_id,
        }
        for r in resumes
    ]
