# app/schemas/response.py
from pydantic import BaseModel
from datetime import datetime
from typing import List

class ShelfWithAssignments(BaseModel):
    id: int
    name: str
    category: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    capacity: int
    assigned_staff_count: int
    assigned_staff: List[str]

    class Config:
        orm_mode = True
