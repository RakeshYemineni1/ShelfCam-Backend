from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class EmployeeBase(BaseModel):
    """Base employee schema"""
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')
    phone: Optional[str] = Field(None, max_length=20)
    position: Optional[str] = Field(None, max_length=100)
    department: Optional[str] = Field(None, max_length=100)
    is_active: bool = True


class EmployeeCreate(EmployeeBase):
    """Create employee schema"""
    pass


class EmployeeUpdate(BaseModel):
    """Update employee schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')
    phone: Optional[str] = Field(None, max_length=20)
    position: Optional[str] = Field(None, max_length=100)
    department: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None


class EmployeeResponse(EmployeeBase):
    """Employee response schema"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)