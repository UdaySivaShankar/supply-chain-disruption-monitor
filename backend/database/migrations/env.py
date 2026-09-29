import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

# Make the backend package root importable when alembic is executed directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
from models import Base
from utils.config import settings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = settings.database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: pool.Pool) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = settings.database_url.replace("postgresql://", "postgresql+asyncpg://") if "postgresql://" in settings.database_url else settings.database_url
    if configuration["sqlalchemy.url"].startswith("sqlite"):
        configuration["sqlalchemy.url"] = configuration["sqlalchemy.url"].replace("sqlite://", "sqlite+aiosqlite://")

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
