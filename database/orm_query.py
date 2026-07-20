from datetime import date, datetime, time, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from loguru import logger
from sqlalchemy import delete, func, select, text

from database.db import async_session_maker
from database.models import BadWords, BotChat, DailyMessages, ReportChat, SwearLog


TZ_KYIV = ZoneInfo("Europe/Kyiv")


def get_month_bounds(year: int, month: int) -> tuple[date, date]:
    month_start = date(year, month, 1)
    if month == 12:
        next_month_start = date(year + 1, 1, 1)
    else:
        next_month_start = date(year, month + 1, 1)

    return month_start, next_month_start


def get_previous_month(year: int, month: int) -> tuple[int, int]:
    if month == 1:
        return year - 1, 12

    return year, month - 1


class BadWordsRepository:
    @classmethod
    async def ensure_daily_swears_integrity(cls):
        async with async_session_maker() as session:
            try:
                await session.execute(
                    text(
                        """
                        ALTER TABLE daily_swears
                        ADD COLUMN IF NOT EXISTS neutral_count INTEGER NOT NULL DEFAULT 0
                        """
                    )
                )
                await session.execute(
                    text(
                        """
                        ALTER TABLE swear_logs
                        ADD COLUMN IF NOT EXISTS category VARCHAR(32) NOT NULL DEFAULT 'swear'
                        """
                    )
                )
                await session.execute(
                    text(
                        """
                        WITH ranked AS (
                            SELECT
                                id,
                                row_number() OVER (
                                    PARTITION BY chat_id, user_id, date
                                    ORDER BY id
                                ) AS row_num,
                                sum(badwords_count) OVER (
                                    PARTITION BY chat_id, user_id, date
                                ) AS total_count,
                                sum(neutral_count) OVER (
                                    PARTITION BY chat_id, user_id, date
                                ) AS total_neutral_count
                            FROM daily_swears
                        ),
                        updated AS (
                            UPDATE daily_swears AS daily
                            SET
                                badwords_count = ranked.total_count,
                                neutral_count = ranked.total_neutral_count
                            FROM ranked
                            WHERE daily.id = ranked.id AND ranked.row_num = 1
                            RETURNING daily.id
                        )
                        DELETE FROM daily_swears AS daily
                        USING ranked
                        WHERE daily.id = ranked.id AND ranked.row_num > 1
                        """
                    )
                )
                await session.execute(
                    text(
                        """
                        CREATE UNIQUE INDEX IF NOT EXISTS uq_daily_swears_chat_user_date
                        ON daily_swears (chat_id, user_id, date)
                        """
                    )
                )
                await session.execute(
                    text(
                        """
                        CREATE UNIQUE INDEX IF NOT EXISTS uq_daily_messages_chat_user_date
                        ON daily_messages (chat_id, user_id, date)
                        """
                    )
                )
                await session.commit()
                logger.info("✓ БД: Проверка целостности daily_swears завершена")
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Ошибка проверки целостности daily_swears: {e}")
                raise

    @classmethod
    async def increment_message_count(cls, chat_id, user_id, username, date):
        async with async_session_maker() as session:
            try:
                lock_key = f"messages:{chat_id}:{user_id}:{date.isoformat()}"
                await session.execute(
                    text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
                    {"lock_key": lock_key},
                )

                stmt = (
                    select(DailyMessages)
                    .where(
                        DailyMessages.chat_id == chat_id,
                        DailyMessages.user_id == user_id,
                        DailyMessages.date == date,
                    )
                    .order_by(DailyMessages.id)
                )
                result = await session.execute(stmt)
                records = list(result.scalars().all())

                if records:
                    record = records[0]
                    duplicate_count = sum(item.message_count for item in records[1:])
                    record.message_count += 1 + duplicate_count
                    record.username = username

                    if duplicate_count:
                        duplicate_ids = [item.id for item in records[1:]]
                        await session.execute(
                            delete(DailyMessages).where(DailyMessages.id.in_(duplicate_ids))
                        )
                else:
                    session.add(
                        DailyMessages(
                            chat_id=chat_id,
                            user_id=user_id,
                            username=username,
                            message_count=1,
                            date=date,
                        )
                    )

                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Ошибка записи количества сообщений: {e}")

    @classmethod
    async def add_swear(
        cls,
        chat_id,
        user_id,
        username,
        swears,
        date,
        found_words: list[str],
        neutral_count: int = 0,
        neutral_words: list[str] | None = None,
    ):
        async with async_session_maker() as session:
            try:
                neutral_words = neutral_words or []
                lock_key = f"{chat_id}:{user_id}:{date.isoformat()}"
                await session.execute(
                    text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
                    {"lock_key": lock_key},
                )

                stmt = (
                    select(BadWords)
                    .where(
                        BadWords.chat_id == chat_id,
                        BadWords.user_id == user_id,
                        BadWords.date == date,
                    )
                    .order_by(BadWords.id)
                )
                result = await session.execute(stmt)
                records = list(result.scalars().all())

                if records:
                    record = records[0]
                    duplicate_count = sum(item.badwords_count for item in records[1:])
                    duplicate_neutral_count = sum(item.neutral_count for item in records[1:])
                    record.badwords_count += swears
                    record.neutral_count += neutral_count
                    record.username = username

                    if duplicate_count or duplicate_neutral_count:
                        record.badwords_count += duplicate_count
                        record.neutral_count += duplicate_neutral_count
                        duplicate_ids = [item.id for item in records[1:]]
                        await session.execute(
                            delete(BadWords).where(BadWords.id.in_(duplicate_ids))
                        )
                else:
                    record = BadWords(
                        chat_id=chat_id,
                        user_id=user_id,
                        username=username,
                        badwords_count=swears,
                        neutral_count=neutral_count,
                        date=date,
                    )
                    session.add(record)

                for word in found_words:
                    log_entry = SwearLog(
                        chat_id=chat_id,
                        user_id=user_id,
                        username=username,
                        word=word,
                        category="swear",
                        timestamp=datetime.now(TZ_KYIV),
                    )
                    session.add(log_entry)

                for word in neutral_words:
                    log_entry = SwearLog(
                        chat_id=chat_id,
                        user_id=user_id,
                        username=username,
                        word=word,
                        category="neutral",
                        timestamp=datetime.now(TZ_KYIV),
                    )
                    session.add(log_entry)

                await session.commit()
                logger.info(
                    f"✓ БД: Сохранено {swears} матов и {neutral_count} нейтральных "
                    f"ругательств для {username}"
                )
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
                records = list(result.scalars().all())

                if records:
                    count = sum(record.badwords_count for record in records)
                    logger.debug(f"✓ БД: Найдено {count} матов")
                    return count
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
                records_by_user = {}
                for record in records:
                    existing_record = records_by_user.get(record.user_id)
                    if existing_record:
                        existing_record.badwords_count += record.badwords_count
                        existing_record.neutral_count += record.neutral_count
                    else:
                        records_by_user[record.user_id] = record

                records = list(records_by_user.values())
                logger.debug(f"✓ БД: Получено {len(records)} записей для {date}")
                return records
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Ошибка получения данных за дату: {e}")
                return []

    @classmethod
    async def get_all_for_month(cls, chat_id, year: int, month: int):
        async with async_session_maker() as session:
            try:
                month_start, next_month_start = get_month_bounds(year, month)

                stmt = (
                    select(
                        BadWords.user_id.label("user_id"),
                        func.max(BadWords.username).label("username"),
                        func.sum(BadWords.badwords_count).label("badwords_count"),
                        func.sum(BadWords.neutral_count).label("neutral_count"),
                    )
                    .where(
                        BadWords.chat_id == chat_id,
                        BadWords.date >= month_start,
                        BadWords.date < next_month_start,
                    )
                    .group_by(BadWords.user_id)
                )

                result = await session.execute(stmt)
                records = [
                    SimpleNamespace(
                        user_id=row.user_id,
                        username=row.username,
                        badwords_count=row.badwords_count or 0,
                        neutral_count=row.neutral_count or 0,
                    )
                    for row in result.all()
                ]
                logger.debug(
                    f"✓ БД: Получено {len(records)} месячных записей "
                    f"для {chat_id} за {year}-{month:02d}"
                )
                return records
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Ошибка получения месячных данных: {e}")
                return []

    @classmethod
    async def get_chat_month_summary(cls, chat_id, year: int, month: int):
        async with async_session_maker() as session:
            try:
                month_start, next_month_start = get_month_bounds(year, month)

                totals_stmt = select(
                    func.coalesce(func.sum(BadWords.badwords_count), 0).label("swear_count"),
                    func.coalesce(func.sum(BadWords.neutral_count), 0).label("neutral_count"),
                ).where(
                    BadWords.chat_id == chat_id,
                    BadWords.date >= month_start,
                    BadWords.date < next_month_start,
                )
                totals = (await session.execute(totals_stmt)).one()

                favorite_stmt = (
                    select(SwearLog.word, func.count(SwearLog.id).label("word_count"))
                    .where(
                        SwearLog.chat_id == chat_id,
                        SwearLog.category == "swear",
                        SwearLog.timestamp
                        >= datetime.combine(month_start, time.min).replace(tzinfo=TZ_KYIV),
                        SwearLog.timestamp
                        < datetime.combine(next_month_start, time.min).replace(tzinfo=TZ_KYIV),
                    )
                    .group_by(SwearLog.word)
                    .order_by(func.count(SwearLog.id).desc(), SwearLog.word)
                    .limit(1)
                )
                favorite = (await session.execute(favorite_stmt)).first()

                max_day_stmt = (
                    select(
                        BadWords.date.label("swear_date"),
                        func.sum(BadWords.badwords_count).label("day_count"),
                    )
                    .where(
                        BadWords.chat_id == chat_id,
                        BadWords.date >= month_start,
                        BadWords.date < next_month_start,
                    )
                    .group_by(BadWords.date)
                    .order_by(func.sum(BadWords.badwords_count).desc(), BadWords.date)
                    .limit(1)
                )
                max_day = (await session.execute(max_day_stmt)).first()

                return SimpleNamespace(
                    swear_count=totals.swear_count or 0,
                    neutral_count=totals.neutral_count or 0,
                    favorite_word=favorite.word if favorite else None,
                    max_day=max_day.swear_date if max_day and max_day.day_count else None,
                    max_day_swears=max_day.day_count if max_day else 0,
                )
            except Exception as e:
                logger.error(f"❌ Ошибка получения месячной сводки чата: {e}")
                return SimpleNamespace(
                    swear_count=0,
                    neutral_count=0,
                    favorite_word=None,
                    max_day=None,
                    max_day_swears=0,
                )

    @classmethod
    async def get_user_month_profile(cls, chat_id, user_id, year: int, month: int):
        async with async_session_maker() as session:
            try:
                month_start, next_month_start = get_month_bounds(year, month)
                prev_year, prev_month = get_previous_month(year, month)
                prev_start, prev_next_start = get_month_bounds(prev_year, prev_month)

                current_stmt = select(
                    func.coalesce(func.sum(BadWords.badwords_count), 0).label("swear_count"),
                    func.coalesce(func.sum(BadWords.neutral_count), 0).label("neutral_count"),
                    func.coalesce(func.max(BadWords.badwords_count), 0).label("daily_record"),
                ).where(
                    BadWords.chat_id == chat_id,
                    BadWords.user_id == user_id,
                    BadWords.date >= month_start,
                    BadWords.date < next_month_start,
                )
                current = (await session.execute(current_stmt)).one()

                previous_stmt = select(
                    func.coalesce(func.sum(BadWords.badwords_count), 0).label("swear_count"),
                ).where(
                    BadWords.chat_id == chat_id,
                    BadWords.user_id == user_id,
                    BadWords.date >= prev_start,
                    BadWords.date < prev_next_start,
                )
                previous = (await session.execute(previous_stmt)).one()

                messages_stmt = select(
                    func.coalesce(func.sum(DailyMessages.message_count), 0).label("message_count")
                ).where(
                    DailyMessages.chat_id == chat_id,
                    DailyMessages.user_id == user_id,
                    DailyMessages.date >= month_start,
                    DailyMessages.date < next_month_start,
                )
                messages = (await session.execute(messages_stmt)).one()

                month_start_dt = datetime.combine(month_start, time.min).replace(tzinfo=TZ_KYIV)
                next_month_start_dt = datetime.combine(next_month_start, time.min).replace(
                    tzinfo=TZ_KYIV
                )
                favorite_stmt = (
                    select(SwearLog.word, func.count(SwearLog.id).label("word_count"))
                    .where(
                        SwearLog.chat_id == chat_id,
                        SwearLog.user_id == user_id,
                        SwearLog.category == "swear",
                        SwearLog.timestamp >= month_start_dt,
                        SwearLog.timestamp < next_month_start_dt,
                    )
                    .group_by(SwearLog.word)
                    .order_by(func.count(SwearLog.id).desc(), SwearLog.word)
                    .limit(1)
                )
                favorite = (await session.execute(favorite_stmt)).first()

                unique_stmt = select(func.count(func.distinct(SwearLog.word))).where(
                    SwearLog.chat_id == chat_id,
                    SwearLog.user_id == user_id,
                    SwearLog.category == "swear",
                    SwearLog.timestamp >= month_start_dt,
                    SwearLog.timestamp < next_month_start_dt,
                )
                unique_count = (await session.execute(unique_stmt)).scalar_one()

                return SimpleNamespace(
                    swear_count=current.swear_count or 0,
                    neutral_count=current.neutral_count or 0,
                    daily_record=current.daily_record or 0,
                    previous_swear_count=previous.swear_count or 0,
                    message_count=messages.message_count or 0,
                    favorite_word=favorite.word if favorite else None,
                    favorite_count=favorite.word_count if favorite else 0,
                    unique_swear_count=unique_count or 0,
                )
            except Exception as e:
                logger.error(f"❌ Ошибка получения матного профиля: {e}")
                return SimpleNamespace(
                    swear_count=0,
                    neutral_count=0,
                    daily_record=0,
                    previous_swear_count=0,
                    message_count=0,
                    favorite_word=None,
                    favorite_count=0,
                    unique_swear_count=0,
                )

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
                threshold_date = datetime.now(TZ_KYIV) - timedelta(days=days)

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
        async with async_session_maker() as session:
            try:
                stmt = select(ReportChat.chat_id)
                result = await session.execute(stmt)
                return list(result.scalars().all())
            except Exception as e:
                logger.error(f"❌ Ошибка получения списка чатов: {e}")
                return []

    @classmethod
    async def upsert_bot_chat(cls, chat_id: int, title: str | None, chat_type: str) -> None:
        async with async_session_maker() as session:
            try:
                stmt = select(BotChat).where(BotChat.chat_id == chat_id)
                result = await session.execute(stmt)
                chat = result.scalar_one_or_none()

                if chat:
                    chat.title = title
                    chat.chat_type = chat_type
                    chat.updated_at = datetime.now(TZ_KYIV)
                else:
                    session.add(
                        BotChat(
                            chat_id=chat_id,
                            title=title,
                            chat_type=chat_type,
                            updated_at=datetime.now(TZ_KYIV),
                        )
                    )

                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"❌ Ошибка сохранения чата {chat_id}: {e}")

    @classmethod
    async def get_all_bot_chats(cls) -> list[BotChat]:
        async with async_session_maker() as session:
            try:
                stmt = select(BotChat).order_by(BotChat.title, BotChat.chat_id)
                result = await session.execute(stmt)
                return list(result.scalars().all())
            except Exception as e:
                logger.error(f"❌ Ошибка получения списка известных чатов: {e}")
                return []
