from pydantic import BaseModel, ConfigDict, Field


class PostBase(BaseModel):
    title: str = Field(..., max_length=100)
    content: str = Field(..., min_length=50)
    author: str = Field(..., max_length=50)


class PostCreate(PostBase):
    pass


class PostResponse(PostBase):
    id: int
    date_posted: str

    model_config = ConfigDict(from_attributes=True)
