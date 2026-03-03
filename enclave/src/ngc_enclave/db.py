import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Read DATABASE_URL environment variable, falls back to local Docker default
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://ngc:ngc@localhost:5433/ngc")
# Connection pool — sized for moderate concurrent load.
# pool_size: persistent connections kept alive.
# max_overflow: extra connections allowed under burst traffic.
engine = create_async_engine(DATABASE_URL, pool_size=5, max_overflow=10, pool_timeout=30)
# Session factory
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


# FastAPI dependency
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
