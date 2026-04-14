import logging
from datetime import date

from database.orm_query import BadWordsRepository


async def send_daily_report(bot):
    """
    Отправляет ежедневный отчет по всем подписанным чатам.
    """
    try:
        active_chats = await BadWordsRepository.get_all_active_chats()

        if not active_chats:
            logging.info("ℹ️ Планировщик: Нет активных чатов для рассылки отчета.")
            return

        logging.info(f"🚀 Планировщик: Начинаю рассылку отчетов для {len(active_chats)} чатов.")

        for chat_id in active_chats:
            records = await BadWordsRepository.get_all_for_date(chat_id=chat_id, date=date.today())

            if not records:
                await bot.send_message(chat_id, "📊 Сегодня ругательств не было. Молодцы!")
                continue

            text_parts = ["📊 Итоги дня:\n\n"]
            for record in records:
                text_parts.append(
                    f"━━━━━━━━━━━━━━━━━\n"
                    f"👤 {record.username or record.user_id}\n"
                    f"💬 Матерных слов: {record.badwords_count}\n\n"
                )

            # Отправляем
            await bot.send_message(chat_id, "".join(text_parts))
            await bot.send_message(
                chat_id, "Молодцы, все хорошо постарались! Завтра надо больше 😈"
            )

    except Exception as e:
        logging.error(f"❌ Ошибка внутри планировщика отчетов: {e}", exc_info=True)
