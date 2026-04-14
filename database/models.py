from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import BigInteger, Date, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class BadWords(Base):
    __tablename__ = "daily_swears"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger)
    user_id: Mapped[int] = mapped_column(BigInteger)
    username: Mapped[str] = mapped_column(String(255), nullable=True)
    badwords_count: Mapped[int] = mapped_column(Integer, default=0)
    date: Mapped[date] = mapped_column(Date)


class SwearLog(Base):
    __tablename__ = "swear_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger)
    user_id: Mapped[int] = mapped_column(BigInteger)
    username: Mapped[str] = mapped_column(String(255), nullable=True)
    word: Mapped[str] = mapped_column(String(255))
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo("Europe/Kyiv"))
    )


class ReportChat(Base):
    __tablename__ = "report_chats"

    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    subscribed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo("Europe/Kyiv"))
    )
