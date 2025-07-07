from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database.db import get_db
from app.models.inventory import Inventory
from app.models.employee import Employee
from app.schemas.inventory import InventoryCreate, InventoryUpdate, InventoryResponse, CategoryEnum
from app.core.auth import require_store_manager
from sqlalchemy.exc import IntegrityError

router = APIRouter(prefix="/inventory", tags=["inventory"])

@router.post("/", response_model=InventoryResponse, status_code=status.HTTP_201_CREATED)
def create_inventory_item(
    inventory_data: InventoryCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_store_manager)
):
    """Create a new inventory item (Store Manager only)"""
    try:
        db_inventory = Inventory(
            shelf_name=inventory_data.shelf_name,
            product_number=inventory_data.product_number,
            product_name=inventory_data.product_name,
            category=inventory_data.category.value
        )
        db.add(db_inventory)
        db.commit()
        db.refresh(db_inventory)
        return db_inventory
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product number already exists"
        )

@router.get("/", response_model=List[InventoryResponse])
def get_all_inventory(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_store_manager)
):
    """Get all inventory items (Store Manager only)"""
    inventory_items = db.query(Inventory).all()
    return inventory_items

@router.get("/{product_number}", response_model=InventoryResponse)
def get_inventory_item(
    product_number: str,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_store_manager)
):
    """Get specific inventory item by product number (Store Manager only)"""
    inventory_item = db.query(Inventory).filter(Inventory.product_number == product_number).first()
    if not inventory_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found"
        )
    return inventory_item

@router.put("/{product_number}", response_model=InventoryResponse)
def update_inventory_item(
    product_number: str,
    inventory_data: InventoryUpdate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_store_manager)
):
    """Update inventory item (Store Manager only)"""
    inventory_item = db.query(Inventory).filter(Inventory.product_number == product_number).first()
    if not inventory_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found"
        )
    
    try:
        update_data = inventory_data.model_dump(exclude_unset=True)
        if 'category' in update_data:
            update_data['category'] = update_data['category'].value
        
        for field, value in update_data.items():
            setattr(inventory_item, field, value)
        
        db.commit()
        db.refresh(inventory_item)
        return inventory_item
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product number already exists"
        )

@router.delete("/{product_number}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inventory_item(
    product_number: str,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_store_manager)
):
    """Delete inventory item (Store Manager only)"""
    inventory_item = db.query(Inventory).filter(Inventory.product_number == product_number).first()
    if not inventory_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found"
        )
    
    db.delete(inventory_item)
    db.commit()

@router.get("/categories/list", response_model=List[str])
def get_categories(
    current_user: Employee = Depends(require_store_manager)
):
    """Get all available product categories (Store Manager only)"""
    return [category.value for category in CategoryEnum]