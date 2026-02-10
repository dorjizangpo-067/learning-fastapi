from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    username: str = Field(..., max_length=50)
    email: EmailStr = Field(..., max_length=120)


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = Field(default=None, max_length=120)
    image_file: str | None = Field(default=None)


class UserResponse(UserBase):
    id: int
    image_file: str | None = None
    image_path: str

    model_config = ConfigDict(from_attributes=True)


class PostBase(BaseModel):
    title: str = Field(..., max_length=100)
    content: str = Field(..., min_length=50)


class PostCreate(PostBase):
    user_id: int  # Temp


class PostUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=100)
    content: str | None = Field(default=None, min_length=50)


class PostResponse(PostBase):
    id: int
    user_id: int
    date_posted: datetime
    author: UserResponse

    model_config = ConfigDict(from_attributes=True)
