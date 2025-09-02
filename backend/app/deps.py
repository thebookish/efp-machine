from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import make_url
from app.config import settings

def to_async_url(url_str: str) -> str:
    """Force the DATABASE_URL to use async drivers."""
    u = make_url(url_str)
    if u.drivername.startswith("sqlite"):
        u = u.set(drivername="sqlite+aiosqlite")
    elif u.drivername.startswith("postgresql"):
        u = u.set(drivername="postgresql+asyncpg")
    return str(u)

ASYNC_DB_URL = to_async_url(settings.DATABASE_URL)

engine = create_async_engine(ASYNC_DB_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
