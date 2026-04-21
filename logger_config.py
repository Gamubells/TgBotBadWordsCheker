import logging
import os
import sys
from pathlib import Path

import sentry_sdk
from loguru import logger
from sentry_sdk.integrations.loguru import LoguruIntegration


# Создаем папку для логов, если её нет
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# Инициализация Sentry (сработает только если DSN есть в .env)
SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        # Интеграция с Loguru заставит Sentry ловить все logger.error()
        integrations=[LoguruIntegration()],
        # Уровень отслеживания производительности (0.0 - 1.0)
        traces_sample_rate=1.0,
    )


class InterceptHandler(logging.Handler):
    """Перехватчик для стандартного logging, чтобы всё шло в Loguru"""

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
    """Настройка Loguru и перехват логов"""
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    logging.getLogger("aiogram").setLevel(logging.INFO)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    logger.remove()

    # Вывод в консоль
    logger.add(sys.stdout, level="INFO", colorize=True)

    # Вывод в файл (все логи)
    logger.add(
        LOGS_DIR / "app.log",
        level="INFO",
        rotation="5 MB",
        retention="10 days",
        encoding="utf-8",
    )

    # Вывод в файл (только ошибки)
    logger.add(
        LOGS_DIR / "errors.log",
        level="ERROR",
        rotation="5 MB",
        retention="30 days",
        encoding="utf-8",
    )
