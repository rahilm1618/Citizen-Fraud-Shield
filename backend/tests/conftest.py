import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.database import Base

TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5434/citizen_fraud_shield"

# Use the test database URL for testing
engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    # Setup tables
    async with engine.begin() as conn:
        # Create extension if not exists inside pgvector image
        await conn.execute(org_sa_text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Teardown tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session():
    async with TestingSessionLocal() as session:
        yield session

# Need this for executing raw SQL inside the async fixture
from sqlalchemy import text as org_sa_text
