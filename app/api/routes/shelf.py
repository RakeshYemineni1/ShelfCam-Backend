from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database.db import get_db
from app.models.shelf import Shelf, ShelfCategoryEnum
from app.models.employee import Employee
from app.schemas.shelf import ShelfCreate, ShelfUpdate, ShelfResponse
from app.core.auth import require_store_manager
from sqlalchemy.exc import IntegrityError
from app.models.staff_assignment import StaffAssignment

router = APIRouter(prefix="/shelves", tags=["shelf-management"])

@router.post("/", response_model=ShelfResponse, status_code=status.HTTP_201_CREATED)
def create_shelf(
    shelf_data: ShelfCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_store_manager)
):
    """Create a new shelf (Store Manager only)"""
    try:
        db_shelf = Shelf(
            name=shelf_data.name,
            category=shelf_data.category,
            capacity=shelf_data.capacity,
            description=shelf_data.description,
            is_active=shelf_data.is_active
        )
        db.add(db_shelf)
        db.commit()
        db.refresh(db_shelf)
        return db_shelf
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shelf name already exists"
        )

@router.get("/", response_model=List[ShelfResponse])
def get_all_shelves(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_store_manager)
):
    """Get all shelves (Store Manager only)"""
    query = db.query(Shelf)
    if not include_inactive:
        query = query.filter(Shelf.is_active == True)
    shelves = query.all()
    return shelves

@router.get("/{shelf_name}", response_model=ShelfResponse)
def get_shelf_by_name(
    shelf_name: str,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_store_manager)
):
    """Get specific shelf by name (Store Manager only)"""
    shelf = db.query(Shelf).filter(Shelf.name == shelf_name).first()
    if not shelf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shelf not found"
        )
    return shelf

@router.put("/{shelf_name}", response_model=ShelfResponse)
def update_shelf(
    shelf_name: str,
    shelf_data: ShelfUpdate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_store_manager)
):
    """Update shelf (Store Manager only)"""
    shelf = db.query(Shelf).filter(Shelf.name == shelf_name).first()
    if not shelf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shelf not found"
        )

    try:
        update_data = shelf_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(shelf, field, value)
        db.commit()
        db.refresh(shelf)
        return shelf
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shelf name already exists"
        )

@router.delete("/{shelf_name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shelf(
    shelf_name: str,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_store_manager)
):
    """Delete shelf (Store Manager only)"""
    shelf = db.query(Shelf).filter(Shelf.name == shelf_name).first()
    if not shelf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shelf not found"
        )

    active_assignments = db.query(StaffAssignment).filter(
        StaffAssignment.shelf_id == shelf.id,
        StaffAssignment.is_active == True
    ).count()

    if active_assignments > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete shelf with {active_assignments} active staff assignments"
        )

    db.delete(shelf)
    db.commit()

@router.get("/categories/list", response_model=List[str])
def get_shelf_categories(
    current_user: Employee = Depends(require_store_manager)
):
    """Get all available shelf categories (Store Manager only)"""
    return [category.value for category in ShelfCategoryEnum]

@router.patch("/{shelf_name}/toggle-status", response_model=ShelfResponse)
def toggle_shelf_status(
    shelf_name: str,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_store_manager)
):
    """Toggle shelf active/inactive status (Store Manager only)"""
    shelf = db.query(Shelf).filter(Shelf.name == shelf_name).first()
    if not shelf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shelf not found"
        )

    if shelf.is_active:
        active_assignments = db.query(StaffAssignment).filter(
            StaffAssignment.shelf_id == shelf.id,
            StaffAssignment.is_active == True
        ).count()

        if active_assignments > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot deactivate shelf with {active_assignments} active staff assignments"
            )

    shelf.is_active = not shelf.is_active
    db.commit()
    db.refresh(shelf)
    return shelf
