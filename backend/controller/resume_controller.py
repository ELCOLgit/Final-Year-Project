from fastapi import APIRouter, UploadFile, Depends
from sqlalchemy.orm import Session
from backend.database import SessionLocal, DATABASE_URL
from backend.models.resume_model import Resume
from backend.models.user_model import User, UserRole
import fitz
from datetime import datetime
import os

router = APIRouter(
    prefix="/resumes",
    tags=["Resumes"]
)

# === Debug route: show database path ===
@router.get("/db-path")
def get_db_path():
    return {"database_path": os.path.abspath(DATABASE_URL.replace("sqlite:///", ""))}

# === Dependency to get DB session ===
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# === Helper: extract text from PDF ===
def extract_text_from_pdf(file: UploadFile) -> str:
    pdf_text = ""
    with fitz.open(stream=file.file.read(), filetype="pdf") as pdf_doc:
        for page in pdf_doc:
            pdf_text += page.get_text("text")
    return pdf_text.strip()

# === Upload and parse a CV ===
@router.post("/upload/")
async def upload_resume(file: UploadFile, db: Session = Depends(get_db)):
    text_content = extract_text_from_pdf(file)

    user = db.query(User).filter(User.id == 1).first()
    if not user:
        user = User(
            name="Demo Seeker",
            email="demo@example.com",
            password_hash="123",
            role=UserRole.job_seeker
        )
        db.add(user)
        db.commit()
        db.refresh(user)

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
        "message": "Resume uploaded and parsed successfully",
        "user": user.name,
        "resume_id": resume.id,
        "text_preview": text_content[:400] + "..." if len(text_content) > 400 else text_content
    }

# === View all resumes ===
@router.get("/")
def list_resumes(db: Session = Depends(get_db)):
    resumes = db.query(Resume).all()
    return [
        {
            "id": r.id,
            "filename": r.filename,
            "upload_date": r.upload_date,
            "user_id": r.user_id
        }
        for r in resumes
    ]
