import re
import sys
from datetime import datetime
from typing import Any

from loguru import logger

from .app_settings import settings

LOG_FORMAT = "<green>[{local_time}]</green> | <level>{level.name}</level> | <cyan>{pod_name}:{name}</cyan> | <blue>{module}.{function}</blue>:<yellow>{line}</yellow> | <level>{message}</level>\n"


def remove_unwanted_tags(text: str) -> str:
    allowed = {"<green>", "<level>", "<cyan>", "<blue>", "<yellow>"}
    return re.sub(
        r"<[^<>]+>", lambda m: m.group(0) if m.group(0) in allowed else "", text
    )


def escape_color_tags(value: str) -> str:
    return re.sub(r"<([^<>]+)>", r"\\<\1\\>", value)


def format_log(record: Any) -> str:
    from ..utils.strings import Strings

    data = {
        **dict(record),
        "local_time": datetime.now(settings.timezone).strftime(
            "%Y-%m-%d %H:%M:%S (UTC%z)"
        ),
        "pod_name": settings.kube.pod_name,
        "message": remove_unwanted_tags(Strings.normalize(record.pop("message", ""))),
    }
    for key in ("module", "function", "name"):
        val = data.get(key, "")
        data[key] = escape_color_tags(str(val))

    return LOG_FORMAT.format(**data)


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
        backtrace=True,
        diagnose=True,

    )


async def complete_and_stop_logger() -> None:
    await logger.complete()
    logger.stop()


configure_logger()
