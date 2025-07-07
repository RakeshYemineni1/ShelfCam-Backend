# ============ 1. app/auth.py ============
from fastapi import HTTPException, Depends, status, Query
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.models.employee import Employee
from typing import Optional
from enum import Enum

class UserRole(str, Enum):
    AREA_MANAGER = "area_manager"
    STORE_MANAGER = "store_manager"
    STAFF = "staff"

def get_current_user(
    employee_id: Optional[str] = Query(None, description="Employee ID"),
    db: Session = Depends(get_db)
):
    if not employee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee ID is required. Add ?employee_id=your_id to the URL"
        )
    
    try:
        user = None
        if employee_id.isdigit():
            user = db.query(Employee).filter(Employee.id == int(employee_id)).first()
        
        if not user and hasattr(Employee, 'employee_id'):
            user = db.query(Employee).filter(Employee.employee_id == employee_id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee '{employee_id}' not found"
            )
        
        if hasattr(user, 'is_active') and not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Employee account is inactive"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication error: {str(e)}"
        )

def require_area_manager(current_user: Employee = Depends(get_current_user)):
    """🏢 AREA MANAGER ONLY - Can see active shelves and other regions/stores"""
    if not hasattr(current_user, 'role'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. User role not defined."
        )
    
    if current_user.role != UserRole.AREA_MANAGER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Area Manager role required. Your role: {current_user.role}"
        )
    
    return current_user

def require_store_manager(current_user: Employee = Depends(get_current_user)):
    """🏪 STORE MANAGER ONLY - Can access everything except other stores"""
    if not hasattr(current_user, 'role'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. User role not defined."
        )
    
    if current_user.role != UserRole.STORE_MANAGER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Store Manager role required. Your role: {current_user.role}"
        )
    
    return current_user

def require_staff(current_user: Employee = Depends(get_current_user)):
    """👤 STAFF ONLY - Can only access alerts"""
    if not hasattr(current_user, 'role'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. User role not defined."
        )
    
    if current_user.role != UserRole.STAFF:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Staff role required. Your role: {current_user.role}"
        )
    
    return current_user

def require_manager_or_above(current_user: Employee = Depends(get_current_user)):
    """🏢🏪 AREA MANAGER OR STORE MANAGER"""
    if not hasattr(current_user, 'role'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. User role not defined."
        )
    
    allowed_roles = [UserRole.AREA_MANAGER, UserRole.STORE_MANAGER]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Manager role required. Your role: {current_user.role}"
        )
    
    return current_user

# Helper function to check if user can access specific store
def can_access_store(current_user: Employee, store_id: str) -> bool:
    """Check if user can access a specific store"""
    if current_user.role == UserRole.AREA_MANAGER:
        return True  # Area managers can access all stores
    
    if current_user.role == UserRole.STORE_MANAGER:
        # Store managers can only access their own store
        if hasattr(current_user, 'store_id'):
            return current_user.store_id == store_id
        return True  # If no store_id field, allow access for now
    
    return False  # Staff cannot access store management
