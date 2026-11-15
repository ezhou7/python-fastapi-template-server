from fastapi import FastAPI

from api.routers import posts

app = FastAPI(title="API", version="0.1.0")
app.include_router(posts.router)
