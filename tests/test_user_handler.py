import asyncio
from types import SimpleNamespace

from handlers.user_handler import (
    _is_admin_or_private_chat,
    choose_profile_style,
    format_chat_comparison,
    format_log_word,
    format_profile_report,
    get_month_rare_words,
    parse_say_command,
)


def test_admin_check_fails_closed_on_telegram_error():
    class FailingBot:
        async def get_chat_member(self, chat_id, user_id):
            raise RuntimeError("Telegram unavailable")

    message = SimpleNamespace(
        bot=FailingBot(),
        chat=SimpleNamespace(id=-100123, type="group"),
        from_user=SimpleNamespace(id=42),
    )

    assert asyncio.run(_is_admin_or_private_chat(message)) is False


def test_format_log_word_marks_neutral_words():
    assert format_log_word("дурак", "neutral") == "🟡 дурак"


def test_format_log_word_leaves_swear_words_unmarked():
    assert format_log_word("сука", "swear") == "сука"


def test_format_log_word_escapes_html():
    assert format_log_word("<word>", "neutral") == "🟡 &lt;word&gt;"


def test_parse_say_command_with_numeric_chat_id():
    assert parse_say_command("/say -1001234567890 Всем привет") == (
        -1001234567890,
        "Всем привет",
    )


def test_parse_say_command_with_public_chat_username():
    assert parse_say_command("/say @my_chat Всем привет") == ("@my_chat", "Всем привет")


def test_parse_say_command_rejects_missing_target_or_text():
    assert parse_say_command("/say") == (None, "")
    assert parse_say_command("/say -1001234567890") == (None, "")
    assert parse_say_command("/say chat_name text") == (None, "")


def test_profile_report_is_compact_and_shows_main_stats():
    profile = SimpleNamespace(
        swear_count=47,
        neutral_count=12,
        daily_record=11,
        previous_swear_count=38,
        message_count=560,
        favorite_word="сука",
        favorite_count=19,
        unique_swear_count=6,
        chat_swear_counts=[47, 8, 12, 80],
    )

    report = format_profile_report("Gamubells", 2026, 7, profile)

    assert "🪪 <b>Матный профиль</b>" in report
    assert "👤 Gamubells" in report
    assert "📅 Июль 2026" in report
    assert "🔥 Матов: <b>47</b>" in report
    assert "🟡 Мягких: <b>12</b>" in report
    assert "📊 Всего ругательств: <b>59</b>" in report
    assert "💬 Индекс: <b>8.4%</b>" in report
    assert "❤️ Любимый мат: <b>сука</b>" in report
    assert "🏆 Рекорд дня: <b>11</b>" in report
    assert "📈 К прошлому месяцу: <b>+24%</b>" in report
    assert "📍 Ты материшься больше 67% чата" in report


def test_profile_report_handles_empty_profile():
    profile = SimpleNamespace(
        swear_count=0,
        neutral_count=0,
        daily_record=0,
        previous_swear_count=0,
        message_count=0,
        favorite_word=None,
        favorite_count=0,
        unique_swear_count=0,
        chat_swear_counts=[],
    )

    report = format_profile_report("Kostya", 2026, 7, profile)

    assert "💬 Индекс: <b>0%</b>" in report
    assert "❤️ Любимый мат: <b>пока нет</b>" in report
    assert "📈 К прошлому месяцу: <b>0%</b>" in report
    assert "📍 Пока не с кем сравнить в этом месяце" in report
    assert "🎭 Стиль: <b>😇 Почти святой</b>" in report


def test_profile_style_prefers_neutral_toxic_when_neutral_is_higher():
    profile = SimpleNamespace(
        swear_count=2,
        neutral_count=7,
        previous_swear_count=0,
        favorite_count=1,
        unique_swear_count=2,
    )

    assert choose_profile_style(profile, swear_index=2.5) == "🟡 Интеллигентный токсик"


def test_profile_style_detects_favorite_word_dominance():
    profile = SimpleNamespace(
        swear_count=20,
        neutral_count=1,
        previous_swear_count=0,
        favorite_count=9,
        unique_swear_count=5,
    )

    assert choose_profile_style(profile, swear_index=4.0) == "❤️ Верный классике"


def test_chat_comparison_detects_less_than_chat():
    assert format_chat_comparison(5, [5, 8, 10, 1]) == "📍 Ты материшься меньше 67% чата"


def test_chat_comparison_detects_middle_position():
    assert format_chat_comparison(5, [5, 8, 1]) == "📍 Ты примерно в середине чата"


def test_chat_comparison_keeps_other_users_with_same_count():
    assert format_chat_comparison(5, [5, 5, 1]) == "📍 Ты материшься больше 50% чата"


def test_month_rare_words_are_stable():
    words = get_month_rare_words(chat_id=-100123, year=2026, month=7)

    assert get_month_rare_words(chat_id=-100123, year=2026, month=7) == words
    assert len(words) == 3
    assert len(set(words)) == 3
    assert all(isinstance(word, str) and word for word in words)


def test_month_rare_words_change_between_months():
    assert get_month_rare_words(chat_id=-100123, year=2026, month=7) != get_month_rare_words(
        chat_id=-100123,
        year=2026,
        month=8,
    )
