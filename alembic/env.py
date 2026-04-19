import asyncio
import os
import sys
from logging.config import fileConfig

from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine

from alembic import context
from app.config import settings

# ensure project package imports work when alembic runs from migrations dir
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# import your project's objects so that Alembic can autogenerate migrations
from app.database import Base
from app.database import engine as async_engine  # the async engine and declarative Base
from app.models import *  # noqa: F401,F403 - import models so metadata is populated

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    Configures the context with just a URL and not an Engine.
    """
    url = config.get_main_option('sqlalchemy.url', settings.DATABASE_URL)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={'paramstyle': 'named'},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """
    Run migrations using a synchronous Connection - this is called
    inside AsyncIO's connection.run_sync to execute the migration
    code in a synchronous context as Alembic expects.
    """
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode using an AsyncEngine.

    This connects with the project's async engine and delegates the
    migration work to a synchronous callable via connection.run_sync.
    """
    # async_engine is expected to be an instance of sqlalchemy.ext.asyncio.AsyncEngine
    if not isinstance(async_engine, AsyncEngine):
        raise RuntimeError("Expected 'async_engine' to be an instance of AsyncEngine")

    async with async_engine.connect() as connection:
        # run_sync will run the given callable in a synchronous context
        await connection.run_sync(do_run_migrations)


if context.is_offline_mode():
    run_migrations_offline()
else:
    # Use asyncio.run to execute the async migration runner.
    asyncio.run(run_migrations_online())
