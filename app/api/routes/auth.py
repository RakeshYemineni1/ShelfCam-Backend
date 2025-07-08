from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.user import LoginRequest, TokenResponse
from app.models.employee import Employee
from app.core.jwt_token import create_access_token
from app.database.db import get_db

router = APIRouter(tags=["Authentication"])

@router.post("/auth/login", response_model=TokenResponse)
def login_user(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(Employee).filter(
        Employee.employee_id == data.employee_id,
        Employee.username == data.username,
        Employee.role == data.role
    ).first()

    if not user or user.password != data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Please check employee ID, username, password, or role."
        )

    if hasattr(user, 'is_active') and not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Contact admin."
        )

    token = create_access_token({
        "sub": user.employee_id,
        "role": user.role
    })

    return {"access_token": token, "token_type": "bearer"}
