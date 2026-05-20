from datetime import datetime

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


async def send_daily_report(bot):
    try:
        active_chats = await BadWordsRepository.get_all_active_chats()

        if not active_chats:
            logger.info("ℹ️ Планировщик: Нет активных чатов для рассылки отчета.")
            return

        logger.info(f"🚀 Планировщик: Начинаю рассылку отчетов для {len(active_chats)} чатов.")

        for chat_id in active_chats:
            records = await BadWordsRepository.get_all_for_date(
                chat_id=chat_id, date=datetime.now(TZ_KYIV).date()
            )

            if not records:
                await bot.send_message(chat_id, "📊 Сегодня ругательств не было. Молодцы!")
                continue

            await bot.send_message(chat_id, format_daily_report(records))
            await bot.send_message(
                chat_id, "Молодцы, все хорошо постарались! Завтра надо больше 😈"
            )

    except Exception as e:
        logger.error(f"❌ Ошибка внутри планировщика отчетов: {e}")
