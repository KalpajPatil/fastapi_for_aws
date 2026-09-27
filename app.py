from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import Base, get_db, get_engine
from models import User
from schemas import UserSchema

USERS_URL = "https://jsonplaceholder.typicode.com/users"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Creates the users table if it doesn't exist yet.
    Base.metadata.create_all(bind=get_engine())
    yield


app = FastAPI(lifespan=lifespan)

origins = ["*"]
app.add_middleware(
 CORSMiddleware,
 allow_origins=origins,
 allow_credentials=True,
 allow_methods=["*"],
 allow_headers=["*"],
)

@app.get("/api/test")
async def test():
    return "Hello World!"


@app.get("/api/users", response_model=list[UserSchema])
async def get_users():
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.get(USERS_URL)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Upstream request failed: {exc}")
    return response.json()


# Plain `def` (not async) so FastAPI runs the blocking HTTP + DB calls in a threadpool.
@app.post("/api/users/save", response_model=list[UserSchema])
def save_users(db: Session = Depends(get_db)):
    try:
        response = httpx.get(USERS_URL, timeout=10)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Upstream request failed: {exc}")

    users = [UserSchema.model_validate(u) for u in response.json()]
    for user in users:
        # merge() inserts new rows and updates existing ones, so re-running is safe.
        db.merge(
            User(
                id=user.id,
                name=user.name,
                username=user.username,
                email=user.email,
                phone=user.phone,
                website=user.website,
                address=user.address.model_dump(),
                company=user.company.model_dump(by_alias=True),
            )
        )
    db.commit()
    return users


@app.get("/api/db/users", response_model=list[UserSchema])
def list_saved_users(db: Session = Depends(get_db)):
    return db.scalars(select(User).order_by(User.id)).all()
