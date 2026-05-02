import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from litestar.plugins.sqlalchemy import (
    AsyncSessionConfig,
    SQLAlchemyAsyncConfig,
    SQLAlchemyInitPlugin,
)
from database.tables import *
from litestar.plugins.sqlalchemy import UUIDAuditBase

CONNECTION_STRING = os.getenv("CONNECTION_STRING")

# Plugin makes session factory available for injection
metadata = UUIDAuditBase.metadata
session_config = AsyncSessionConfig(expire_on_commit=False)
sqlalchemy_config = SQLAlchemyAsyncConfig(
    connection_string=CONNECTION_STRING,
    session_config=session_config,
    metadata=metadata,  # Ensure the metadata is set here
)

sqlalchemy_plugin = SQLAlchemyInitPlugin(config=sqlalchemy_config)


# Create session factory for dependency injection
engine = create_async_engine(
    url=CONNECTION_STRING,
    future=True,
)
session_factory = async_sessionmaker(engine, expire_on_commit=False)
