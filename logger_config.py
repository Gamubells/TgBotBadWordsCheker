import logging
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from loguru import logger


LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")


def telegram_alert_sink(message):

    if not BOT_TOKEN or not ADMIN_ID:
        return

    text = f"🚨 <b>Критическая ошибка в боте!</b>\n\n<pre>{message}</pre>"
    if len(text) > 4000:
        text = text[:4000] + "\n...[ОБРЕЗАНО]...</pre>"

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": ADMIN_ID, "text": text, "parse_mode": "HTML"}).encode(
        "utf-8"
    )

    try:
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=5):
            pass
    except Exception as e:
        print(f"Не удалось отправить алерт в Telegram: {e}", file=sys.stderr)


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
        LOGS_DIR / "app.log",
        level="INFO",
        rotation="5 MB",
        retention="10 days",
        encoding="utf-8",
    )

    logger.add(
        LOGS_DIR / "errors.log",
        level="ERROR",
        rotation="5 MB",
        retention="30 days",
        encoding="utf-8",
    )

    logger.add(
        telegram_alert_sink,
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {name}:{function}:{line}\n{message}",
    )
