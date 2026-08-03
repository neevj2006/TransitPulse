import logging

import structlog
from structlog.typing import EventDict, WrappedLogger

SENSITIVE_KEYS = {"authorization", "cookie", "password", "secret", "token", "api_key"}


def redact_secrets(_: WrappedLogger, __: str, event_dict: EventDict) -> EventDict:
    """Keep structured logs useful without serialising common credentials."""
    for key in list(event_dict):
        if any(fragment in key.lower() for fragment in SENSITIVE_KEYS):
            event_dict[key] = "[REDACTED]"
    return event_dict


def configure_logging(level: str) -> None:
    logging.basicConfig(level=level, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            redact_secrets,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
