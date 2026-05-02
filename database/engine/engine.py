from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from litestar.plugins.sqlalchemy import (
    AsyncSessionConfig,
    SQLAlchemyAsyncConfig,
    SQLAlchemyInitPlugin,
)
from database.tables import UUIDAuditBase
from core.config import settings

# Plugin makes session factory available for injection
metadata = UUIDAuditBase.metadata
session_config = AsyncSessionConfig(expire_on_commit=False)
sqlalchemy_config = SQLAlchemyAsyncConfig(
    connection_string=settings.DATABASE_URL,
    session_config=session_config,
    metadata=metadata,
)

sqlalchemy_plugin = SQLAlchemyInitPlugin(config=sqlalchemy_config)

# Create session factory for manual use (e.g. workers)
engine = create_async_engine(
    url=settings.DATABASE_URL,
    future=True,
)
session_factory = async_sessionmaker(engine, expire_on_commit=False)
