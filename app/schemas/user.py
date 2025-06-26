from pydantic import BaseModel
from typing import Literal

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: Literal["staff", "manager", "admin"] = "staff"

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str

class Config:
    from_attributes = True

