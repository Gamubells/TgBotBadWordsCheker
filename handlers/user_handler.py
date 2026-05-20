import html
from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from loguru import logger

from database.orm_query import TZ_KYIV, BadWordsRepository
from metrics import ACTIVE_SUBSCRIPTIONS, MESSAGES_TOTAL, SWEARS_TOTAL
from services import check_text_for_swears


router = Router()


async def _is_admin_or_private_chat(message: Message) -> bool:
    if not message.from_user:
        return False

    if message.chat.type == "private":
        return True

    member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    return member.status in {"creator", "administrator"}


@router.message(CommandStart())
async def start_command_handler(message: Message):
    await message.answer("Добро пожаловать в бот, который будет считать ваши ругательства")


@router.message(Command("subscribe_swears"))
async def subscribe_command_handler(message: Message):
    if not await _is_admin_or_private_chat(message):
        await message.answer("⛔ Подпиской на отчеты могут управлять только администраторы чата.")
        return

    success = await BadWordsRepository.subscribe_chat(message.chat.id)
    if success:
        ACTIVE_SUBSCRIPTIONS.inc()
        await message.answer(
            "✅ Отлично! Этот чат подписан на ежедневные отчеты (в 23:01 по Киеву)."
        )
    else:
        await message.answer("ℹ️ Этот чат уже подписан на рассылку.")


@router.message(Command("unsubscribe_swears"))
async def unsubscribe_command_handler(message: Message):
    if not await _is_admin_or_private_chat(message):
        await message.answer("⛔ Подпиской на отчеты могут управлять только администраторы чата.")
        return

    success = await BadWordsRepository.unsubscribe_chat(message.chat.id)
    if success:
        ACTIVE_SUBSCRIPTIONS.dec()
        await message.answer("❌ Вы отписались. Отчеты больше приходить не будут.")
    else:
        await message.answer("ℹ️ Этот чат и так не был подписан на рассылку.")


@router.message(Command("count_swears"))
async def count_command_handler(message: Message):
    if not message.from_user:
        return

    request_date = datetime.now(TZ_KYIV).date()
    try:
        count = await BadWordsRepository.get_swear_count(
            chat_id=message.chat.id, user_id=message.from_user.id, date=request_date
        )

        count = count or 0
        logger.info(
            f"count command: chat_id={message.chat.id} "
            f"user_id={message.from_user.id} date={request_date} count={count}"
        )

        await message.answer(
            f"📊 {message.from_user.full_name}, у тебя сегодня {count} ругательств."
        )
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        await message.answer("⚠️ Не удалось получить статистику.")


@router.message(Command("helpy_swears"))
async def help_command_handler(message: Message):
    await message.answer("К сожалению помощь не придет.")


@router.message(Command("about_swears"))
async def about_command_handler(message: Message):
    text = (
        "🛡 <b>Swear Checker Bot (v0.1.4)</b>\n\n"
        "Инспектор чата 👮‍♂️\n"
        "Автоматический фильтр нецензурной лексики. Бот работает в фоновом режиме, "
        "анализирует сообщения и ведет статистику для каждого участника чата.\n\n"
        "<b>Особенности:</b>\n"
        "• Распознавание корней слов в любых склонениях.\n"
        "• Защита от обхода фильтра (Leetspeak, дублирование букв).\n"
        "• Персональная статистика и логирование.\n\n"
        "<b>Управление:</b>\n"
        "▫️ <code>/count_swears</code> — посмотреть количество своих матов за текущий день.\n"
        "▫️ <code>/logs_swears</code> — запросить детализацию (время и текст найденных ругательств)."
        "\n"
        "▫️ <code>/about_swears</code> — информация о боте.\n"
        "▫️ <code>/helpy_swears</code> — помощь.\n"
        "▫️ <code>/subscribe_swears</code> — подписаться на ежедневные отчеты (только для админов)."
        ".\n"
        "▫️ <code>/unsubscribe_swears</code> — отписаться от ежедневных отчетов.\n\n"
        "Автор бота: @Gamubells (Telegram)"
    )
    await message.answer(text, parse_mode="HTML")


@router.message(Command("logs_swears"))
async def logs_command_handler(message: Message):
    if not message.from_user:
        return

    logs = await BadWordsRepository.get_recent_logs(
        chat_id=message.chat.id, user_id=message.from_user.id, limit=30
    )

    if not logs:
        await message.answer("Ну ты и вежливый😇 Маты не обнаружены🧐")
        return

    today_kyiv = datetime.now(TZ_KYIV).date()
    text = (
        f"📜 <b>Твои ругательства за сегодня ({today_kyiv.strftime('%d.%m.%Y')})"
        f" — {html.escape(message.from_user.full_name)}:</b>\n\n"
    )

    grouped_logs = {}

    for log in logs:
        time_kyiv = log.timestamp.astimezone(TZ_KYIV)
        time_str = time_kyiv.strftime("%H:%M")

        if time_str not in grouped_logs:
            grouped_logs[time_str] = []

        grouped_logs[time_str].append(log.word)

    for time_str in sorted(grouped_logs.keys()):
        words_joined = html.escape(", ".join(grouped_logs[time_str]))
        text += f"[{time_str}] <b>{words_joined}</b>\n"

    await message.answer(text, parse_mode="HTML")


@router.message(F.text)
async def bad_words_handler(message: Message):
    MESSAGES_TOTAL.inc()

    if not message.from_user:
        logger.info("message ignored: from_user is missing")
        return

    logger.info(
        f"received message: {message.text} from {message.from_user.full_name} "
        f"(id={message.from_user.id}, bot={message.from_user.is_bot})"
    )

    if message.from_user.is_bot or not message.text or message.text.startswith("/"):
        logger.info(
            f"message ignored: bot={message.from_user.is_bot}, text_exists={bool(message.text)}, "
            f"is_command={message.text.startswith('/') if message.text else False}"
        )
        return

    badwords_count, found_words = check_text_for_swears(message.text)

    if not badwords_count:
        return

    SWEARS_TOTAL.inc(badwords_count)

    logger.info(
        f"Найдены маты: {found_words} (всего: {badwords_count}) от "
        f"{message.from_user.full_name} (uid:{message.from_user.id})"
    )
    try:
        await BadWordsRepository.add_swear(
            chat_id=message.chat.id,
            user_id=message.from_user.id,
            username=message.from_user.full_name,
            swears=badwords_count,
            date=datetime.now(TZ_KYIV).date(),
            found_words=found_words,
        )
        logger.info(f"✓ Добавлено {badwords_count} матов в БД от {message.from_user.full_name}")
    except Exception as e:
        logger.error(f"✗ Ошибка добавления ругательства: {e}")
