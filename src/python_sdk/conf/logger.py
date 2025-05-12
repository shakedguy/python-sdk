import logging.config
from datetime import datetime
from logging import INFO, LogRecord
from typing import Any, Dict
from pytz import timezone as tz

import colorlog


def format_time(record: LogRecord) -> str:
    return datetime.fromtimestamp(record.created, tz=tz("Asia/Tel_Aviv")).isoformat()


class ISO8601Formatter(logging.Formatter):
    def formatTime(self, record: LogRecord, datefmt: str | None = None) -> str:
        return format_time(record=record)


class ColoredISO8601Formatter(colorlog.ColoredFormatter):
    def formatTime(self, record: LogRecord, datefmt: str | None = None) -> str:
        return format_time(record=record)


LOGGING_CONFIG: Dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "colorized": {
            "()": ColoredISO8601Formatter,
            "format": "%(log_color)s[%(asctime)s] - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
            "log_colors": {
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
            },
        },
        "detailed": {
            "()": ISO8601Formatter,
            "format": "[%(asctime)s] - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "detailed",
        },
    },
    "loggers": {
        "": {
            "level": "INFO",
            "handlers": ["console"],
        },
    },
}


logging.config.dictConfig(LOGGING_CONFIG)


def get_logger(name: str, level: int | str = INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level.upper() if isinstance(level, str) else level)
    return logger
