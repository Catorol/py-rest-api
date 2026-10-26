# ruff: noqa: E402
import os

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://app:app@localhost:5432/tasks_test",
)
os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from app.db import Base, get_session
from app.main import app


async def create_test_database() -> None:
    """Создаёт БД tasks_test"""
    url = make_url(TEST_DATABASE_URL)
    admin_engine = create_async_engine(
        url.set(database="postgres"),
        isolation_level="AUTOCOMMIT",
        poolclass=NullPool,
    )
    async with admin_engine.connect() as conn:
        exists = await conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": url.database},
        )
        if not exists:
            await conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    await admin_engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def engine():
    await create_test_database()
    test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield test_engine
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def client(engine):
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE tasks, users RESTART IDENTITY CASCADE"))

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
