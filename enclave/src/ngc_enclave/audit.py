import asyncio
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase


# Base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    endpoint = Column(String, nullable=False)
    query_params = Column(JSONB, nullable=True)
    status_code = Column(Integer, nullable=False)


class AuditLogger:
    """Manages asynchronous batch logging to PostgreSQL."""

    def __init__(self, batch_interval: float = 2.0):
        self.queue = asyncio.Queue()
        self.batch_interval = batch_interval
        self._worker_task = None

    async def start(self, engine):
        """Start the background worker."""
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._worker(engine))

    async def _worker(self, engine):
        """Background task that flushes the queue periodically."""
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy.orm import sessionmaker

        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        while True:
            await asyncio.sleep(self.batch_interval)

            entries = []
            while not self.queue.empty():
                entries.append(self.queue.get_nowait())

            if not entries:
                continue

            try:
                async with async_session() as session:
                    async with session.begin():
                        session.add_all(entries)
                # print(f"✓ Audited {len(entries)} requests")
            except Exception as e:
                print(f"✗ Failed to flush audit logs: {e}")

    def log(self, endpoint: str, query_params: dict[str, Any], status_code: int):
        """Queue a log entry without waiting for DB."""
        entry = AuditLog(
            endpoint=endpoint,
            query_params=query_params,
            status_code=status_code,
        )
        self.queue.put_nowait(entry)


# Global logger instance
audit_logger = AuditLogger()


async def log_request(
    _db_is_unused: Any,  # Kept for signature compatibility for now
    endpoint: str,
    query_params: dict[str, Any],
    status_code: int,
) -> None:
    """Public wrapper to queue a request log."""
    audit_logger.log(endpoint, query_params, status_code)
