from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

print(f"DATABASE_URL: {settings.DATABASE_URL.replace(settings.POSTGRES_PASSWORD, '***')}")
engine = create_async_engine(settings.DATABASE_URL, echo=False)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI that yields a database session.
    Closes the session automatically after the request.
    """
    async with AsyncSessionLocal() as session:
        yield session
