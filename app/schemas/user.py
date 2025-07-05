from pydantic import BaseModel

class LoginRequest(BaseModel):
    employee_id: str
    username: str
    password: str
    role: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
