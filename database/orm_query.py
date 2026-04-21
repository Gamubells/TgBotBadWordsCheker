from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from loguru import logger
from sqlalchemy import delete, select

from database.db import async_session_maker
from database.models import BadWords, ReportChat, SwearLog


TZ_KYIV = ZoneInfo("Europe/Kyiv")


class BadWordsRepository:
    @classmethod
    async def add_swear(cls, chat_id, user_id, username, swears, date, found_words: list[str]):
        async with async_session_maker() as session:
            try:
                stmt = select(BadWords).where(
                    BadWords.chat_id == chat_id, BadWords.user_id == user_id, BadWords.date == date
                )
                result = await session.execute(stmt)
                record = result.scalar_one_or_none()

                if record:
                    record.badwords_count += swears
                else:
                    record = BadWords(
                        chat_id=chat_id,
                        user_id=user_id,
                        username=username,
                        badwords_count=swears,
                        date=date,
                    )
                    session.add(record)

                for word in found_words:
                    log_entry = SwearLog(
                        chat_id=chat_id,
                        user_id=user_id,
                        username=username,
                        word=word,
                        timestamp=datetime.now(TZ_KYIV),
                    )
                    session.add(log_entry)

                await session.commit()
                logger.info(f"✓ БД: Сохранено {swears} матов для {username}")
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Ошибка записи в БД: {e}")
                raise

    @classmethod
    async def get_swear_count(cls, chat_id, user_id, date):
        async with async_session_maker() as session:
            try:
                stmt = select(BadWords).where(
                    BadWords.chat_id == chat_id, BadWords.user_id == user_id, BadWords.date == date
                )

                result = await session.execute(stmt)
                record = result.scalar_one_or_none()

                if record:
                    logger.debug(f"✓ БД: Найдено {record.badwords_count} матов")
                    return record.badwords_count
                logger.debug("✓ БД: Матов не найдено (вернут 0)")
                return 0
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Ошибка получения статистики: {e}")
                return 0

    @classmethod
    async def get_all_for_date(cls, chat_id, date):
        async with async_session_maker() as session:
            try:
                stmt = select(BadWords).where(BadWords.chat_id == chat_id, BadWords.date == date)

                result = await session.execute(stmt)
                records = result.scalars().all()
                logger.debug(f"✓ БД: Получено {len(records)} записей для {date}")
                return records
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Ошибка получения данных за дату: {e}")
                return []

    @classmethod
    async def get_recent_logs(cls, chat_id, user_id, limit=30):
        async with async_session_maker() as session:
            try:
                now_kyiv = datetime.now(TZ_KYIV)
                today_start = datetime.combine(now_kyiv.date(), time.min).replace(tzinfo=TZ_KYIV)
                tomorrow_start = today_start + timedelta(days=1)

                stmt = (
                    select(SwearLog)
                    .where(
                        SwearLog.chat_id == chat_id,
                        SwearLog.user_id == user_id,
                        SwearLog.timestamp >= today_start,
                        SwearLog.timestamp < tomorrow_start,
                    )
                    .order_by(SwearLog.timestamp.desc())
                    .limit(limit)
                )
                result = await session.execute(stmt)
                return result.scalars().all()
            except Exception as e:
                logger.error(f"❌ Ошибка получения логов: {e}")
                return []

    @classmethod
    async def clear_old_logs(cls, days=7):
        async with async_session_maker() as session:
            try:
                threshold_date = datetime.now() - timedelta(days=days)

                stmt = delete(SwearLog).where(SwearLog.timestamp < threshold_date)

                result = await session.execute(stmt)
                await session.commit()

                deleted_count = result.rowcount
                logger.info(
                    f"♻️ Очистка БД: удалено {deleted_count} старых логов (старше {days} дней)."
                )

            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Ошибка очистки логов: {e}")

    @classmethod
    async def subscribe_chat(cls, chat_id: int) -> bool:
        """Добавляет чат в рассылку. Возвращает True если добавлен, False если уже был."""
        async with async_session_maker() as session:
            try:
                stmt = select(ReportChat).where(ReportChat.chat_id == chat_id)
                result = await session.execute(stmt)
                if result.scalar_one_or_none():
                    return False

                session.add(ReportChat(chat_id=chat_id))
                await session.commit()
                logger.info(f"✅ БД: Чат {chat_id} подписан на рассылку")
                return True
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Ошибка при подписке чата {chat_id}: {e}")
                return False

    @classmethod
    async def unsubscribe_chat(cls, chat_id: int) -> bool:
        """Удаляет чат из рассылки. Возвращает True если удален, False если его там не было."""
        async with async_session_maker() as session:
            try:
                stmt = delete(ReportChat).where(ReportChat.chat_id == chat_id)
                result = await session.execute(stmt)
                await session.commit()

                if result.rowcount > 0:
                    logger.info(f"❌ БД: Чат {chat_id} отписан от рассылки")
                    return True
                return False
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Ошибка при отписке чата {chat_id}: {e}")
                return False

    @classmethod
    async def get_all_active_chats(cls) -> list[int]:
        """Получает список всех ID чатов, подписанных на рассылку."""
        async with async_session_maker() as session:
            try:
                stmt = select(ReportChat.chat_id)
                result = await session.execute(stmt)
                return list(result.scalars().all())
            except Exception as e:
                logger.error(f"❌ Ошибка получения списка чатов: {e}")
                return []
