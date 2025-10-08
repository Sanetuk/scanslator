from __future__ import annotations

import logging
import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect

DEFAULT_DB_URL = "sqlite:///orchestrator.db"
logger = logging.getLogger(__name__)


def _ensure_revision_table(config: Config, database_url: str) -> None:
    engine = create_engine(database_url, future=True)
    try:
        with engine.connect() as conn:
            inspector = inspect(conn)
            has_version_table = inspector.has_table("alembic_version")
            jobs_exists = inspector.has_table("jobs")
            logger.info("has_version_table=%s jobs_exists=%s", has_version_table, jobs_exists)
            if not has_version_table and jobs_exists:
                script = ScriptDirectory.from_config(config)
                head = script.get_current_head()
                logger.warning(
                    "Alembic version table missing; stamping head %s to match existing schema.", head
                )
                command.stamp(config, head)
    finally:
        engine.dispose()


def run_migrations() -> None:
    base_path = Path(__file__).resolve().parents[1]
    alembic_ini = base_path / "alembic.ini"
    migrations_path = base_path / "migrations"

    config = Config(str(alembic_ini))
    config.set_main_option("script_location", str(migrations_path))
    database_url = os.getenv("ORCHESTRATOR_DATABASE_URL", DEFAULT_DB_URL)
    config.set_main_option("database_url", database_url)

    logger.info("Running Alembic migrations at %s", database_url)
    try:
        _ensure_revision_table(config, database_url)
        command.upgrade(config, "head")
    except Exception:
        logger.exception("Alembic upgrade failed")
        raise
