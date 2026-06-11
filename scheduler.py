import asyncio
from datetime import date, datetime, timedelta

from loguru import logger

from database.orm_query import TZ_KYIV, BadWordsRepository


MEDALS = ("🥇", "🥈", "🥉")


def format_daily_report(records) -> str:
    ranked_records = sorted(
        (record for record in records if record.badwords_count > 0),
        key=lambda record: record.badwords_count,
        reverse=True,
    )
    total_swears = sum(record.badwords_count for record in records)
    total_neutral = sum(record.neutral_count for record in records)

    text_parts = ["🏆 Матный рейтинг дня\n\n"]
    if not ranked_records:
        text_parts.append("Сегодня матов не было.\n")

    for place, record in enumerate(ranked_records, start=1):
        medal = MEDALS[place - 1] if place <= len(MEDALS) else f"{place}."
        text_parts.append(
            f"{medal} {record.username or record.user_id} — {record.badwords_count}\n"
        )

    text_parts.append(
        f"\n━━━━━━━━━━━━━━━━\n"
        f"📊 Всего матов: {total_swears}\n"
        f"🟡 Нейтральных ругательств: {total_neutral}"
    )
    return "".join(text_parts)


def is_last_day_of_month(current_date: date) -> bool:
    return (current_date + timedelta(days=1)).month != current_date.month


def format_monthly_report(records, year: int, month: int) -> str:
    ranked_records = sorted(
        (record for record in records if record.badwords_count > 0),
        key=lambda record: record.badwords_count,
        reverse=True,
    )
    total_swears = sum(record.badwords_count for record in records)
    total_neutral = sum(record.neutral_count for record in records)

    text_parts = [f"🏆 Матный рейтинг месяца {month:02d}.{year}\n\n"]
    if not ranked_records:
        text_parts.append("В этом месяце матов не было.\n")

    for place, record in enumerate(ranked_records, start=1):
        medal = MEDALS[place - 1] if place <= len(MEDALS) else f"{place}."
        text_parts.append(
            f"{medal} {record.username or record.user_id} — {record.badwords_count}\n"
        )

    text_parts.append(
        f"\n━━━━━━━━━━━━━━━━\n"
        f"📊 Всего матов за месяц: {total_swears}\n"
        f"🟡 Нейтральных ругательств за месяц: {total_neutral}"
    )
    return "".join(text_parts)


async def send_daily_report(bot):
    try:
        active_chats = await BadWordsRepository.get_all_active_chats()

        if not active_chats:
            logger.info("ℹ️ Планировщик: Нет активных чатов для рассылки отчета.")
            return

        logger.info(f"🚀 Планировщик: Начинаю рассылку отчетов для {len(active_chats)} чатов.")

        today = datetime.now(TZ_KYIV).date()
        should_send_monthly_report = is_last_day_of_month(today)
        monthly_reports = []

        for chat_id in active_chats:
            records = await BadWordsRepository.get_all_for_date(chat_id=chat_id, date=today)

            if not records:
                await bot.send_message(chat_id, "📊 Сегодня ругательств не было. Молодцы!")
            else:
                await bot.send_message(chat_id, format_daily_report(records))
                await bot.send_message(
                    chat_id, "Молодцы, все хорошо постарались! Завтра надо больше 😈"
                )

            if should_send_monthly_report:
                month_records = await BadWordsRepository.get_all_for_month(
                    chat_id=chat_id,
                    year=today.year,
                    month=today.month,
                )
                monthly_reports.append(
                    (chat_id, format_monthly_report(month_records, today.year, today.month))
                )

        if monthly_reports:
            await asyncio.sleep(60)
            for chat_id, report in monthly_reports:
                await bot.send_message(chat_id, report)

    except Exception as e:
        logger.error(f"❌ Ошибка внутри планировщика отчетов: {e}")
