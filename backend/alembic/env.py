from logging.config import fileConfig
from sqlalchemy import String, engine_from_config, inspect, pool
from alembic import context
from alembic.ddl.mysql import MySQLImpl

# Import Core Settings và Base Metadata
from app.core.config import settings
from app.core.database import Base
# Import toàn bộ models để Base.metadata nhận diện đủ các bảng
import app.models

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Gán URL từ Pydantic Settings nếu chưa được truyền từ CLI
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

target_metadata = Base.metadata


class LearnMateMySQLImpl(MySQLImpl):
    __dialect__ = "mysql"

    def version_table_impl(self, **kwargs):
        # Existing revision IDs exceed Alembic's default VARCHAR(32).
        table = super().version_table_impl(**kwargs)
        table.c.version_num.type = String(64)
        return table


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = settings.DATABASE_URL

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        if connection.dialect.name == "mysql":
            inspector = inspect(connection)
            if inspector.has_table("alembic_version"):
                version_column = next(
                    column for column in inspector.get_columns("alembic_version")
                    if column["name"] == "version_num"
                )
                if version_column["type"].length < 64:
                    connection.exec_driver_sql(
                        "ALTER TABLE alembic_version MODIFY version_num VARCHAR(64) NOT NULL"
                    )
            connection.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

