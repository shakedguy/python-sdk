import sys
from datetime import datetime
from typing import Any

from loguru import logger

from .app_settings import settings

LOG_FORMAT = "<green>[{local_time}]</green> | <level>{level.name}</level> | <cyan>{pod_name}:{name}</cyan> | <blue>{module}.{function}</blue>:<yellow>{line}</yellow> | <level>{message}</level>\n"


def format_log(record: Any) -> str:
    from ..utils.strings import Strings

    data = {
        **dict(record),
        "local_time": datetime.now(settings.timezone).strftime(
            "%Y-%m-%d %H:%M:%S (UTC%z)"
        ),
        "pod_name": settings.kube.pod_name,
        "message": Strings.normalize(record.pop("message", "")),
    }
    data.setdefault("module", "")
    data.setdefault("function", "")
    data.setdefault("name", "")
    return LOG_FORMAT.format(**data)


logger.remove()
logger.add(
    sys.stderr, level=settings.log_level, colorize=True, enqueue=True, format=format_log
)


def configure_logger() -> None:
    """
    Configure the logger settings.
    """
    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.log_level,
        colorize=True,
        enqueue=True,
        format=format_log,
    )
