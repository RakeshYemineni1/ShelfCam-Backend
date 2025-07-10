from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database.db import get_db
from app.models.inventory import Inventory
from app.models.employee import Employee
from app.models.shelf import Shelf
from app.schemas.inventory import InventoryCreate, InventoryUpdate, InventoryResponse, CategoryEnum, ShelfSlotsResponse
from app.deps.roles import require_store_manager
from sqlalchemy.exc import IntegrityError

router = APIRouter(prefix="/inventory", tags=["inventory"])

@router.post("/", response_model=InventoryResponse, status_code=status.HTTP_201_CREATED)
def create_inventory_item(
    inventory_data: InventoryCreate,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_store_manager)
):
    """Create a new inventory item (Store Manager only)"""
    
    # Check if shelf exists and is active
    shelf = db.query(Shelf).filter(Shelf.name == inventory_data.shelf_name).first()
    if not shelf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shelf not found"
        )
    
    if not shelf.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add items to inactive shelf"
        )
    
    # Check if shelf has capacity
    current_items = db.query(Inventory).filter(Inventory.shelf_name == inventory_data.shelf_name).count()
    if current_items >= shelf.capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Shelf capacity exceeded. Maximum capacity: {shelf.capacity}"
        )
    
    # Check if rack is already occupied on this shelf
    existing_rack = db.query(Inventory).filter(
        Inventory.shelf_name == inventory_data.shelf_name,
        Inventory.rack_name == inventory_data.rack_name
    ).first()
    
    if existing_rack:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rack '{inventory_data.rack_name}' is already occupied on shelf '{inventory_data.shelf_name}'"
        )
    
    try:
        db_inventory = Inventory(
            shelf_name=inventory_data.shelf_name,
            product_number=inventory_data.product_number,
            product_name=inventory_data.product_name,
            category=inventory_data.category.value,
            rack_name=inventory_data.rack_name
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

@router.get("/shelf/{shelf_name}/slots", response_model=ShelfSlotsResponse)
def get_shelf_slots(
    shelf_name: str,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(require_store_manager)
):
    """Get available slots for a specific shelf (Store Manager only)"""
    
    # Check if shelf exists
    shelf = db.query(Shelf).filter(Shelf.name == shelf_name).first()
    if not shelf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shelf not found"
        )
    
    # Get occupied racks
    occupied_items = db.query(Inventory).filter(Inventory.shelf_name == shelf_name).all()
    occupied_racks = [item.rack_name for item in occupied_items]
    
    return ShelfSlotsResponse(
        shelf_name=shelf_name,
        capacity=shelf.capacity,
        occupied_slots=len(occupied_racks),
        available_slots=shelf.capacity - len(occupied_racks),
        occupied_racks=occupied_racks
    )

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
    
    update_data = inventory_data.model_dump(exclude_unset=True)
    
    # If updating shelf_name, check if new shelf exists and is active
    if 'shelf_name' in update_data:
        shelf = db.query(Shelf).filter(Shelf.name == update_data['shelf_name']).first()
        if not shelf:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shelf not found"
            )
        if not shelf.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot move item to inactive shelf"
            )
    
    # If updating shelf_name or rack_name, check for conflicts
    if 'shelf_name' in update_data or 'rack_name' in update_data:
        target_shelf = update_data.get('shelf_name', inventory_item.shelf_name)
        target_rack = update_data.get('rack_name', inventory_item.rack_name)
        
        # Check if rack is already occupied (excluding current item)
        existing_rack = db.query(Inventory).filter(
            Inventory.shelf_name == target_shelf,
            Inventory.rack_name == target_rack,
            Inventory.id != inventory_item.id
        ).first()
        
        if existing_rack:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Rack '{target_rack}' is already occupied on shelf '{target_shelf}'"
            )
        
        # If moving to different shelf, check capacity
        if target_shelf != inventory_item.shelf_name:
            shelf = db.query(Shelf).filter(Shelf.name == target_shelf).first()
            current_items = db.query(Inventory).filter(Inventory.shelf_name == target_shelf).count()
            if current_items >= shelf.capacity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Target shelf capacity exceeded. Maximum capacity: {shelf.capacity}"
                )
    
    try:
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