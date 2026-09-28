import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

USERS_URL = "https://jsonplaceholder.typicode.com/users"


app = FastAPI()

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


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/users")
async def get_users():
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.get(USERS_URL)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Upstream request failed: {exc}")
    return response.json()
