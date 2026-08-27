from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):

    email: EmailStr

    username: str

    password: str


class UserLogin(BaseModel):

    email: EmailStr

    password: str


class UserResponse(BaseModel):

    id: int

    email: EmailStr

    username: str

    is_premium: bool

    created_at: datetime

    class Config:

        from_attributes = True
