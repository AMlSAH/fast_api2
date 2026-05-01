from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    username: str
    password: str
    group: str = "user"

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    group: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    group: Optional[str] = None

class AdvertisementCreate(BaseModel):
    title: str
    description: str

class AdvertisementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str
    created_at: datetime
    owner_id: int

class AdvertisementUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class LoginData(BaseModel):
    username: str
    password: str
