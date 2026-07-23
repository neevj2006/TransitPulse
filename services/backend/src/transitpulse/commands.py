import sys

import structlog
import uvicorn
from alembic.config import main as alembic_main

from transitpulse.config import get_settings
from transitpulse.logging import configure_logging


def run_api() -> None:
    uvicorn.run("transitpulse.main:app", host="127.0.0.1", port=8000, factory=False)


def run_migrations() -> None:
    alembic_main(argv=["upgrade", "head"])


def run_worker() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    structlog.get_logger().info(
        "worker_foundation_ready",
        environment=settings.environment,
    )
    sys.stdout.flush()
