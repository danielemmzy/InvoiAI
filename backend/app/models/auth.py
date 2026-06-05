from pydantic import BaseModel, EmailStr, Field
from typing import Any, Optional
from datetime import datetime

class SignUpRequest(BaseModel):
    email: EmailStr
    password: str
 
 
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
 
 
class RefreshRequest(BaseModel):
    refresh_token: str
 
 
class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    user_id: str
    email: str
    plan: str
 
 
class UserProfile(BaseModel):
    user_id: str
    email: str
    plan: str
    usage: dict[str, Any]