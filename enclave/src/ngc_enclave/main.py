import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from .audit import Base, audit_logger, log_request
from .db import engine, get_db
from .query import query_allele_frequencies, query_variants

# Default Parquet path — override with PARQUET_PATH env var in production
PARQUET_PATH = os.getenv(
    "PARQUET_PATH",
    str(Path(__file__).parent.parent.parent.parent / "data" / "output.parquet"),
)

# API Security configuration
API_KEY = os.getenv("NGC_API_KEY", "ngc")
api_key_header = APIKeyHeader(name="Authorization", description="Use **ngc** to authorize.", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)):
    if not api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization Header")

    # Support 'Bearer <token>' or just the raw token
    token = api_key.replace("Bearer ", "") if api_key.startswith("Bearer ") else api_key

    if token != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )
    return token


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the background audit worker
    await audit_logger.start(engine)

    # Create DB tables on startup — retries because Postgres may still be initialising
    for attempt in range(10):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            print("✓ Database tables ready")
            break
        except Exception as e:
            if attempt == 9:
                print(f"✗ Could not connect after 10 attempts: {e}")
            else:
                wait = min(2**attempt, 5)  # exponential backoff, capped at 5s
                print(f"  DB not ready (attempt {attempt + 1}/10) — retrying in {wait}s...")
                await asyncio.sleep(wait)
    yield  # app runs here; cleanup goes after yield if needed


app = FastAPI(
    title="NGC Secure Enclave",
    description="**Use `ngc` to authorize.**",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "ok"}


@app.get("/variants")
async def get_variants(
    api_key: Annotated[str, Depends(verify_api_key)],
    chr: str | None = None,
    pos_min: int | None = None,
    pos_max: int | None = None,
    limit: int = 1000,
) -> list[dict[str, Any]]:
    """Query genomic variants from Parquet. Default limit is 1000 rows; max is 5000."""
    limit = min(limit, 5_000)  # hard cap — prevent accidentally fetching the whole dataset
    try:
        results = await asyncio.to_thread(
            query_variants, PARQUET_PATH, chrom=chr, pos_min=pos_min, pos_max=pos_max, limit=limit
        )
    except Exception as e:
        await log_request(None, "/variants", {"chr": chr, "pos_min": pos_min, "pos_max": pos_max}, 500)
        raise HTTPException(status_code=500, detail=str(e))

    await log_request(None, "/variants", {"chr": chr, "pos_min": pos_min, "pos_max": pos_max}, 200)
    return results


@app.get("/datasets")
async def list_datasets(
    db: Annotated[AsyncSession, Depends(get_db)],
    api_key: Annotated[str, Depends(verify_api_key)],
) -> list[dict[str, Any]]:
    """List all ingested datasets from Postgres."""
    from sqlalchemy import text

    result = await db.execute(
        text("SELECT id, vcf_filename, parquet_path, record_count, ingested_at FROM datasets ORDER BY ingested_at DESC")
    )
    rows = result.fetchall()
    await log_request(db, "/datasets", {}, 200)
    return [dict(row._mapping) for row in rows]


@app.get("/alleles")
async def get_alleles_frequencies(
    api_key: Annotated[str, Depends(verify_api_key)],
    chr: str | None = None,
    pos_min: int | None = None,
    pos_max: int | None = None,
) -> list[dict[str, Any]]:
    """Query allele frequencies from Parquet."""
    try:
        results = await asyncio.to_thread(
            query_allele_frequencies, PARQUET_PATH, chrom=chr, pos_min=pos_min, pos_max=pos_max
        )
    except Exception as e:
        await log_request(None, "/alleles", {"chr": chr, "pos_min": pos_min, "pos_max": pos_max}, 500)
        raise HTTPException(status_code=500, detail=str(e))
    await log_request(None, "/alleles", {"chr": chr, "pos_min": pos_min, "pos_max": pos_max}, 200)
    return results
