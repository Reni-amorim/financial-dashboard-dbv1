from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class AccountBase(BaseModel):
    business_id:    int
    name:           Optional[str] = Field(None, max_length=255)
    marketplace_id: Optional[int] = None
    status:         Optional[str] = "active"


class AccountCreate(AccountBase):
    pass


class AccountUpdate(BaseModel):
    name:           Optional[str] = Field(None, max_length=255)
    marketplace_id: Optional[int] = None
    status:         Optional[str] = None


class AccountOut(AccountBase):
    id:         int
    created_at: datetime

    class Config:
        from_attributes = True