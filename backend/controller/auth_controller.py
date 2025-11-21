from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models.user_model import User, UserRole
from backend.utils.auth_utils import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/register/")
def register_user(name: str, email: str, password: str, role: str, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pw = hash_password(password)

    # Normalize and safely map role
    role = role.lower().strip()
    if role == "recruiter":
        role_enum = UserRole.recruiter
    elif role == "job_seeker":
        role_enum = UserRole.job_seeker
    else:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'recruiter' or 'job_seeker'.")

    try:
        user = User(
            name=name,
            email=email,
            password_hash=hashed_pw,
            role=role_enum
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return {
        "message": "User registered successfully",
        "user_id": user.id,
        "role": user.role.value
    }



@router.post("/login/")
def login_user(email: str, password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token({"sub": user.email, "role": user.role.value})
    return {"access_token": token, "token_type": "bearer", "role": user.role.value}
