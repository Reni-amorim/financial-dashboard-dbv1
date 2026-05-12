from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(max_length=72)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    id: int
    username: str
    name: str
    email: EmailStr

    class Config:
        from_attributes = True