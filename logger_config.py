import html
import logging
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import sentry_sdk
from loguru import logger


LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

SENTRY_DSN = os.getenv("SENTRY_DSN")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

if SENTRY_DSN:
    sentry_sdk.init(dsn=SENTRY_DSN, traces_sample_rate=1.0)


def sentry_sink(message):
    record = message.record
    if record["exception"]:
        sentry_sdk.capture_exception(record["exception"].value)
    else:
        sentry_sdk.capture_message(record["message"], level="error")
    sentry_sdk.flush()


def telegram_alert_sink(message):
    """Отправка ошибок в ТГ с защитой от HTML-тегов"""
    if not BOT_TOKEN or not ADMIN_ID:
        return

    escaped_msg = html.escape(str(message))

    text = f"🚨 <b>Ошибка в боте!</b>\n\n<pre>{escaped_msg}</pre>"
    if len(text) > 4000:
        text = text[:4000] + "\n...[ОБРЕЗАНО]...</pre>"

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        data = urllib.parse.urlencode(
            {"chat_id": ADMIN_ID, "text": text, "parse_mode": "HTML"}
        ).encode()
        with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=5):
            pass
    except Exception as e:
        print(f"Ошибка отправки алерта в ТГ: {e}", file=sys.stderr)


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
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    logger.remove()

    logger.add(sys.stdout, level="INFO", colorize=True)

    logger.add(LOGS_DIR / "app.log", rotation="5 MB", level="INFO")

    if SENTRY_DSN:
        logger.add(sentry_sink, level="ERROR")

    logger.add(
        telegram_alert_sink,
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {name}:{function}:{line}\n{message}",
    )
