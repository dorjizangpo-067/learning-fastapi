from typing import Annotated, Sequence

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

import models
from database import Base, engine, get_db
from schemas import (
    PostCreate,
    PostResponse,
    PostUpdate,
    UserCreate,
    UserResponse,
    UserUpdate,
)

Base.metadata.create_all(bind=engine)


app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")

templates = Jinja2Templates(directory="templates")


## home
@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
def home(request: Request, db: Annotated[Session, Depends(get_db)]) -> HTMLResponse:
    result = db.execute(select(models.Post))
    posts = result.scalars().all()
    return templates.TemplateResponse(
        request,
        "home.html",
        {"posts": posts, "title": "Home"},
    )


## post_page
@app.get("/posts/{post_id}", include_in_schema=False)
def post_page(
    request: Request, post_id: int, db: Annotated[Session, Depends(get_db)]
) -> HTMLResponse:
    result = db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
    if post:
        title = post.title[:50]
        return templates.TemplateResponse(
            request,
            "post.html",
            {"post": post, "title": title},
        )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")


## user_posts_page
@app.get("/users/{user_id}/posts", include_in_schema=False, name="user_posts")
def user_posts_page(
    request: Request,
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> HTMLResponse:
    result = db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    result = db.execute(select(models.Post).where(models.Post.user_id == user_id))
    posts = result.scalars().all()
    return templates.TemplateResponse(
        request,
        "user_posts.html",
        {"posts": posts, "user": user, "title": f"{user.username}'s Posts"},
    )


# ------------------------------------------------------------------------------
# create User
@app.post(
    "/api/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user(  # noqa:ANN201
    user: UserCreate, db: Annotated[Session, Depends(get_db)]
) -> UserResponse:
    username = db.execute(
        select(models.User).where(models.User.username == user.username)
    )
    existing_username = username.scalars().first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Useranme Already uxist try with different user name",
        )

    email = db.execute(select(models.User).where(models.User.email == user.email))
    existing_email = email.scalars().first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email Already uxist try with different user name",
        )

    new_user = models.User(
        username=user.username,
        email=user.email,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return UserResponse.model_validate(new_user)


## update_user
@app.patch("/api/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> UserResponse:
    result = db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user_update.username is not None and user_update.username != user.username:
        result = db.execute(
            select(models.User).where(models.User.username == user_update.username),
        )
        existing_user = result.scalars().first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists",
            )

    if user_update.email is not None and user_update.email != user.email:
        result = db.execute(
            select(models.User).where(models.User.email == user_update.email),
        )
        existing_email = result.scalars().first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

    if user_update.username is not None:
        user.username = user_update.username
    if user_update.email is not None:
        user.email = user_update.email
    if user_update.image_file is not None:
        user.image_file = user_update.image_file

    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


## delete_user
@app.delete("/api/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Annotated[Session, Depends(get_db)]) -> None:
    result = db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    db.delete(user)
    db.commit()


@app.get(
    "/api/users/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=UserResponse,
)
def get_user(user_id: int, db: Annotated[Session, Depends(get_db)]) -> UserResponse:
    user = (
        db.execute(select(models.User).where(models.User.id == user_id))
        .scalars()
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User Not found"
        )
    return UserResponse.model_validate(user)


## get_user_posts
@app.get("/api/users/{user_id}/posts", response_model=list[PostResponse])
def get_user_posts(
    user_id: int, db: Annotated[Session, Depends(get_db)]
) -> list[PostResponse]:
    result = db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    result = db.execute(select(models.Post).where(models.Post.user_id == user_id))
    posts = result.scalars().all()
    return [PostResponse.model_validate(post) for post in posts]


@app.get("/api/posts", response_model=list[PostResponse])
def get_posts(db: Annotated[Session, Depends(get_db)]) -> list[PostResponse]:
    result = db.execute(select(models.Post))
    posts = result.scalars().all()
    return [PostResponse.model_validate(post) for post in posts]


## get_post
@app.get("/api/posts/{post_id}", response_model=PostResponse)
def get_post(post_id: int, db: Annotated[Session, Depends(get_db)]) -> PostResponse:
    result = db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
    if post:
        return PostResponse.model_validate(post)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")


## create_post
@app.post(
    "/api/posts",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_post(
    post: PostCreate, db: Annotated[Session, Depends(get_db)]
) -> PostResponse:
    user = (
        db.execute(select(models.User).where(models.User.id == post.user_id))
        .scalars()
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    new_post = models.Post(
        title=post.title,
        content=post.content,
        user_id=post.user_id,
    )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return PostResponse.model_validate(new_post)


# Update Post
@app.put("/api/posts/{post_id}", response_model=PostResponse)
def update_post_full(
    post_id: int,
    post_data: PostCreate,
    db: Annotated[Session, Depends(get_db)],
) -> PostResponse:
    result = db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()

    # Do Post Exist
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    # Is user Id vilad
    user = (
        db.execute(select(models.User).where(models.User.id == post_data.user_id))
        .scalars()
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Is clint author of post
    if post_data.user_id != post.user_id:
        raise HTTPException(
            status_code=status.HTTP_203_NON_AUTHORITATIVE_INFORMATION,
            detail="Your Not Author of Post",
        )

    post.title = post_data.title
    post.content = post_data.content
    post.user_id = post_data.user_id

    db.add(post)
    db.commit()
    db.refresh(post)

    return PostResponse.model_validate(post)


# Update Post
@app.patch("/api/posts/{post_id}", response_model=PostResponse)
def update_post_partal(
    post_id: int,
    post_data: PostUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> PostResponse:
    result = db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()

    # Do Post Exist
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    update_data = post_data.model_dump(exclude_unset=True)
    for filed, value in update_data.items():
        setattr(post, filed, value)

    db.commit()
    db.refresh(post)
    return PostResponse.model_validate(post)


## Delete post
@app.delete("/api/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: int, db: Annotated[Session, Depends(get_db)]) -> None:
    result = db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )
    db.delete(post)
    db.commit()


### StarletteHTTPException Handler
@app.exception_handler(StarletteHTTPException)
def general_http_exception_handler(
    request: Request, exception: StarletteHTTPException
) -> HTMLResponse | JSONResponse:
    message = (
        exception.detail
        if exception.detail
        else "An error occurred. Please check your request and try again."
    )

    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=exception.status_code,
            content={"detail": message},
        )
    return templates.TemplateResponse(
        request,
        "error.html",
        context={
            "status_code": exception.status_code,
            "title": exception.status_code,
            "message": message,
        },
        status_code=exception.status_code,
    )


### RequestValidationError Handler
@app.exception_handler(RequestValidationError)
def validation_exception_handler(
    request: Request, exception: RequestValidationError
) -> HTMLResponse | JSONResponse:
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": exception.errors()},
        )
    return templates.TemplateResponse(
        request,
        "error.html",
        context={
            "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "title": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "message": "Invalid request. Please check your input and try again.",
        },
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )


# 10: 40
