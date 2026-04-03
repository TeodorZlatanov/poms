import asyncio
import re
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlmodel import SQLModel

from core.config import settings

# Import ALL models so SQLModel.metadata is populated
from models import *  # noqa: F401, F403

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# Override URL from settings
config.set_main_option("sqlalchemy.url", settings.database_url)


def _next_revision_id(context, revision, directives):  # noqa: ARG001
    """Generate sequential revision IDs like 001, 002, etc."""
    versions_dir = Path(config.get_main_option("script_location")) / "versions"
    existing = [
        int(m.group(1)) for f in versions_dir.glob("*.py") if (m := re.match(r"^(\d+)_", f.name))
    ]
    next_id = max(existing, default=0) + 1
    for directive in directives:
        directive.rev_id = f"{next_id:03d}"


target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        process_revision_directives=_next_revision_id,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        process_revision_directives=_next_revision_id,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
