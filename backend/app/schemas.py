from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from uuid import UUID

class CheckoutRequest(BaseModel):
    user_id: UUID
    product_id: UUID
    amount: float = Field(..., gt=0, description="Amount must be greater than zero")
    ip_address: str
    device_fingerprint: str

class Token(BaseModel):
    access_token: str
    token_type: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")