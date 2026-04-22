import logging
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import sentry_sdk
from loguru import logger
from sentry_sdk.integrations.loguru import LoguruIntegration


LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

SENTRY_DSN = os.getenv("SENTRY_DSN")
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")


def telegram_alert_sink(message):
    if not BOT_TOKEN or not ADMIN_ID:
        return

    text = f"🚨 <b>Ошибка в боте!</b>\n\n<pre>{message}</pre>"
    if len(text) > 4000:
        text = text[:4000] + "..."

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        data = urllib.parse.urlencode(
            {"chat_id": ADMIN_ID, "text": text, "parse_mode": "HTML"}
        ).encode()
        with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=5):
            pass
    except Exception as e:
        print(f"Ошибка отправки алерта: {e}", file=sys.stderr)


if SENTRY_DSN:
    import logging

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            LoguruIntegration(
                level=logging.INFO,
                event_level=logging.ERROR,
            )
        ],
        traces_sample_rate=1.0,
    )


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

    logger.add(
        telegram_alert_sink,
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {name}:{function}:{line}\n{message}",
    )
