from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from blog_api.config import settings

engine = create_async_engine(settings.database_url, echo=settings.db_echo)

# expire_on_commit=False keeps loaded attributes usable after commit,
# since async sessions can't lazy-load expired attributes.
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: one session per request."""
    async with SessionLocal() as session:
        yield session
