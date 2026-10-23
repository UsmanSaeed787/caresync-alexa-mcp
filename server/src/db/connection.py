"""Database connection manager and explicit transaction context."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Optional
import aiosqlite

from src.config import settings

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def resolve_db_path(db_path_override: Optional[str] = None) -> str:
    if db_path_override:
        return db_path_override
    raw_url = settings.DATABASE_URL
    if raw_url.startswith("sqlite:///"):
        return raw_url[len("sqlite:///"):]
    return raw_url


@asynccontextmanager
async def get_db(db_path_override: Optional[str] = None) -> AsyncGenerator[aiosqlite.Connection, None]:
    path = resolve_db_path(db_path_override)
    async with aiosqlite.connect(path) as db:
        # Enforce SQLite foreign key integrity
        await db.execute("PRAGMA foreign_keys = ON;")
        db.row_factory = aiosqlite.Row
        yield db


@asynccontextmanager
async def transaction(db: aiosqlite.Connection) -> AsyncGenerator[aiosqlite.Connection, None]:
    """Explicit transaction scope with deterministic commit and rollback."""
    try:
        await db.execute("BEGIN IMMEDIATE;")
    except Exception:
        pass  # If already inside transaction, continue
    try:
        yield db
        await db.commit()
    except Exception:
        await db.rollback()
        raise


async def init_db(db_path_override: Optional[str] = None) -> None:
    """Initialize database tables from schema.sql."""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    async with get_db(db_path_override) as db:
        await db.executescript(schema_sql)
        await db.commit()
