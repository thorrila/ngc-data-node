import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Read DATABASE_URL environment variable, falls back to local Docker default
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://ngc:ngc@localhost:5433/ngc")
# Connection pool
engine = create_async_engine(DATABASE_URL)
# Session factory
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


# FastAPI dependency
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
