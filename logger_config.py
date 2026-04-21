import logging
import sys
from pathlib import Path

from loguru import logger


LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)


class InterceptHandler(logging.Handler):

    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging():
    """Настройка Loguru"""
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    logging.getLogger("aiogram").setLevel(logging.INFO)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    logger.remove()

    logger.add(sys.stdout, level="INFO", colorize=True)

    logger.add(
        LOGS_DIR / "app.log", level="INFO", rotation="5 MB", retention="10 days", encoding="utf-8"
    )

    logger.add(
        LOGS_DIR / "errors.log",
        level="ERROR",
        rotation="5 MB",
        retention="30 days",
        encoding="utf-8",
    )
