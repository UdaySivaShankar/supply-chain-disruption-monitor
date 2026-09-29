from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from utils.config import settings

# Adjust URL for asyncpg if standard postgresql is used
db_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://") if "postgresql://" in settings.database_url else settings.database_url
# For sqlite fallback during dev if needed:
if db_url.startswith("sqlite"):
    db_url = db_url.replace("sqlite://", "sqlite+aiosqlite://")

engine = create_async_engine(db_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
