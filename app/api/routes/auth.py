from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.user import LoginRequest, TokenResponse
from app.models.employee import Employee
from app.core.jwt_token import create_access_token
from app.database.db import get_db

router = APIRouter()

@router.post("/auth/login", response_model=TokenResponse)
def login_user(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(Employee).filter(
        Employee.employee_id == data.employee_id,
        Employee.username == data.username,
        Employee.role == data.role
    ).first()

    if not user or user.password != data.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({
        "sub": user.username,
        "role": user.role,
        "employee_id": user.employee_id
    })

    return {"access_token": token, "token_type": "bearer"}
