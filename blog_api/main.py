from contextlib import asynccontextmanager

from fastapi import FastAPI

from blog_api.db import engine
from blog_api.routers import posts


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # Close pooled database connections on shutdown.
    await engine.dispose()


app = FastAPI(title="Blog API", version="0.1.0", lifespan=lifespan)
app.include_router(posts.router)
