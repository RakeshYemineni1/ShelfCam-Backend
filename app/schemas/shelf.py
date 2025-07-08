from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

class ShelfBase(BaseModel):
    """Base shelf schema"""
    name: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., min_length=1, max_length=200)  # changed from location → category
    capacity: int = Field(..., ge=1)
    description: Optional[str] = Field(None, max_length=500)
    is_active: bool = True

class ShelfCreate(ShelfBase):
    """Create shelf schema"""
    pass

class ShelfUpdate(BaseModel):
    """Update shelf schema"""
    shelf_name: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[str] = Field(None, min_length=1, max_length=200)  # changed here
    capacity: Optional[int] = Field(None, ge=1)
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None

class ShelfResponse(ShelfBase):
    """Shelf response schema"""
    id: int
    current_stock: int = 0
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)



class ShelfWithAssignments(BaseModel):
    id: int
    name: str
    category: str  # <- use str or Enum if you have one
    is_active: bool
    capacity: int
    created_at: datetime
    updated_at: datetime
    assigned_staff_count: int
    assigned_staff: List[str]

    class Config:
        from_attributes = True  # allows mapping from SQLAlchemy model

