from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class BusinessBase(BaseModel):
    name:     str           = Field(min_length=2, max_length=255)
    document: Optional[str] = Field(None, max_length=20)


class BusinessCreate(BusinessBase):
    pass


class BusinessUpdate(BaseModel):
    name:     Optional[str] = Field(None, min_length=2, max_length=255)
    document: Optional[str] = Field(None, max_length=20)


class BusinessOut(BusinessBase):
    id:         int
    company_id: int
    created_at: datetime

    class Config:
        from_attributes = True