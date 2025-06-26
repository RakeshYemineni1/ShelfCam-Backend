from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserResponse
from app.services.auth_service import hash_password, verify_password, create_access_token

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from fastapi import HTTPException

@router.post("/signup", response_model=UserResponse)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    try:
        # Check if email already exists
        existing = db.query(User).filter(User.email == user.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered.")

        hashed_pw = hash_password(user.password)
        db_user = User(
            username=user.username,
            email=user.email,
            hashed_password=hashed_pw,
            role=user.role,
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        print(f"🆕 SIGNUP: {db_user.username} | Email: {db_user.email} | Role: {db_user.role}")
        return db_user

    except Exception as e:
        print("❌ Signup error:", e)
        raise HTTPException(status_code=500, detail="Signup failed.")




@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token({"sub": user.username, "role": db_user.role})
    
    # ✅ Print login details to terminal
    print(f"🔐 LOGIN SUCCESS: {db_user.username} | Role: {db_user.role}")
    print(f"📦 Token: {token}")

    return {"access_token": token, "token_type": "bearer"}


