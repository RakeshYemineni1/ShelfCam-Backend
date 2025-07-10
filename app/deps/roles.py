from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.models.employee import Employee # adjust import path
from app.core.config import settings

# Use HTTPBearer for Swagger "Bearer <token>" auth input
bearer_scheme = HTTPBearer()

def get_current_user_role(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> Employee:
    token = credentials.credentials  # Extract Bearer token string

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        employee_id = payload.get("sub")

        if not employee_id:
            raise HTTPException(status_code=403, detail="Employee ID missing")

        user = db.query(Employee).filter_by(employee_id=employee_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return user

    except JWTError:
        raise HTTPException(status_code=403, detail="Invalid or expired token")

def require_store_manager(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> Employee:
    """Require store manager role for protected endpoints"""
    token = credentials.credentials
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        employee_id = payload.get("sub")
        role = payload.get("role")
        
        if not employee_id:
            raise HTTPException(status_code=403, detail="Employee ID missing")
        
        if role != "store_manager":
            raise HTTPException(status_code=403, detail="Store manager access required")
        
        user = db.query(Employee).filter_by(employee_id=employee_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return user
    
    except JWTError:
        raise HTTPException(status_code=403, detail="Invalid or expired token")
