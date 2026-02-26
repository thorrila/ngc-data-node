from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase


# Base class — all ORM models inherit from this so SQLAlchemy knows about them
class Base(DeclarativeBase):
    pass


# ORM model — maps the audit_log table to a Python class
class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)  # auto-incrementing row ID
    ts = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))  # timestamp
    endpoint = Column(String, nullable=False)  # e.g. "/variants"
    query_params = Column(JSONB, nullable=True)  # e.g. {"chr": "17"} stored as JSON
    status_code = Column(Integer, nullable=False)  # HTTP status: 200, 500, etc.


# Inserts one audit row — called by every route after handling a request
async def log_request(
    db: AsyncSession,
    endpoint: str,
    query_params: dict[str, Any],
    status_code: int,
) -> None:
    entry = AuditLog(
        endpoint=endpoint,
        query_params=query_params,
        status_code=status_code,
    )
    db.add(entry)  # stage the new row
    await db.commit()  # write it to Postgres
