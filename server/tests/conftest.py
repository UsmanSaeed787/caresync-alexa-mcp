"""Pytest shared fixtures for CareSync tests."""

from pathlib import Path
from typing import AsyncGenerator
import aiosqlite
import pytest
from httpx import ASGITransport, AsyncClient

from src.config import settings
from src.db.connection import SCHEMA_PATH, init_db
from src.main import app


@pytest.fixture
async def test_db_path(tmp_path: Path) -> AsyncGenerator[str, None]:
    """Provide a path to a temporary isolated SQLite database file."""
    db_file = tmp_path / "test_caresync.db"
    db_path = str(db_file)
    await init_db(db_path_override=db_path)
    yield db_path


@pytest.fixture
async def test_db_conn(test_db_path: str) -> AsyncGenerator[aiosqlite.Connection, None]:
    """Provide an open aiosqlite connection to the test database with FKs enabled."""
    async with aiosqlite.connect(test_db_path) as conn:
        await conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = aiosqlite.Row
        yield conn


@pytest.fixture
async def async_client(test_db_path: str, monkeypatch: pytest.MonkeyPatch) -> AsyncGenerator[AsyncClient, None]:
    """HTTP client wired to the FastAPI app with test DB configured."""
    monkeypatch.setattr(settings, "DATABASE_URL", f"sqlite:///{test_db_path}")
    monkeypatch.setattr(settings, "SEED_ON_STARTUP", True)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
