from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum

class CategoryEnum(str, Enum):
    CLOTHES = "clothes"
    FRUITS = "fruits"
    VEGETABLES = "vegetables"
    SPORTS = "sports"
    GROCERIES = "groceries"

class InventoryCreate(BaseModel):
    shelf_name: str = Field(..., min_length=1, max_length=100, description="Name of the shelf")
    product_number: str = Field(..., min_length=1, max_length=50, description="Unique product number")
    product_name: str = Field(..., min_length=1, max_length=200, description="Name of the product")
    category: CategoryEnum = Field(..., description="Product category")
    rack_name: str = Field(..., min_length=1, max_length=100, description="Name of the rack")

class InventoryUpdate(BaseModel):
    shelf_name: Optional[str] = Field(None, min_length=1, max_length=100)
    product_number: Optional[str] = Field(None, min_length=1, max_length=50)
    product_name: Optional[str] = Field(None, min_length=1, max_length=200)
    category: Optional[CategoryEnum] = None
    rack_name: Optional[str] = Field(None, min_length=1, max_length=100)

class InventoryResponse(BaseModel):
    id: int
    shelf_name: str
    product_number: str
    product_name: str
    category: str
    rack_name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ShelfSlotsResponse(BaseModel):
    shelf_name: str
    capacity: int
    occupied_slots: int
    available_slots: int
    occupied_racks: list[str]