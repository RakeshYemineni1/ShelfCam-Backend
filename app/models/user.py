from pydantic import BaseModel
from enum import Enum

class UserRole(str, Enum):
    area_manager = "area_manager"
    store_manager = "store_manager"
    staff = "staff"

class LoginRequest(BaseModel):
    employee_id: str
    username: str
    password: str
    role: UserRole

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
