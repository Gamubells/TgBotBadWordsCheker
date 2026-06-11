from datetime import date
from types import SimpleNamespace

from scheduler import format_daily_report, format_monthly_report, is_last_day_of_month


def test_daily_report_is_sorted_by_swear_count_descending():
    records = [
        SimpleNamespace(username="Second", user_id=2, badwords_count=7, neutral_count=2),
        SimpleNamespace(username="First", user_id=1, badwords_count=12, neutral_count=4),
        SimpleNamespace(username="Third", user_id=3, badwords_count=3, neutral_count=1),
    ]

    report = format_daily_report(records)

    assert report.index("🥇 First — 12") < report.index("🥈 Second — 7")
    assert report.index("🥈 Second — 7") < report.index("🥉 Third — 3")


def test_daily_report_uses_numbered_places_after_top_three():
    records = [
        SimpleNamespace(
            username=f"User {place}",
            user_id=place,
            badwords_count=count,
            neutral_count=0,
        )
        for place, count in enumerate([10, 9, 8, 7], start=1)
    ]

    report = format_daily_report(records)

    assert "4. User 4 — 7" in report


def test_daily_report_falls_back_to_user_id_without_username():
    records = [SimpleNamespace(username=None, user_id=123, badwords_count=5, neutral_count=0)]

    report = format_daily_report(records)

    assert "🥇 123 — 5" in report


def test_daily_report_shows_total_counts():
    records = [
        SimpleNamespace(username="First", user_id=1, badwords_count=12, neutral_count=4),
        SimpleNamespace(username="Second", user_id=2, badwords_count=7, neutral_count=2),
    ]

    report = format_daily_report(records)

    assert "📊 Всего матов: 19" in report
    assert report.endswith("🟡 Нейтральных ругательств: 6")


def test_daily_report_does_not_rank_neutral_only_records():
    records = [
        SimpleNamespace(username="Neutral", user_id=1, badwords_count=0, neutral_count=4),
    ]

    report = format_daily_report(records)

    assert "Сегодня матов не было." in report
    assert "🥇 Neutral — 0" not in report
    assert "📊 Всего матов: 0" in report
    assert report.endswith("🟡 Нейтральных ругательств: 4")


def test_last_day_of_month_detects_regular_and_leap_months():
    assert is_last_day_of_month(date(2026, 6, 30))
    assert is_last_day_of_month(date(2024, 2, 29))
    assert not is_last_day_of_month(date(2026, 6, 29))
    assert not is_last_day_of_month(date(2025, 2, 27))


def test_monthly_report_is_sorted_by_swear_count_descending():
    records = [
        SimpleNamespace(username="Second", user_id=2, badwords_count=21, neutral_count=5),
        SimpleNamespace(username="First", user_id=1, badwords_count=35, neutral_count=8),
        SimpleNamespace(username="Third", user_id=3, badwords_count=9, neutral_count=1),
    ]

    report = format_monthly_report(records, 2026, 6)

    assert report.startswith("🏆 Матный рейтинг месяца 06.2026")
    assert report.index("🥇 First — 35") < report.index("🥈 Second — 21")
    assert report.index("🥈 Second — 21") < report.index("🥉 Third — 9")
    assert "📊 Всего матов за месяц: 65" in report
    assert report.endswith("🟡 Нейтральных ругательств за месяц: 14")


def test_monthly_report_handles_month_without_swears():
    records = [
        SimpleNamespace(username="Neutral", user_id=1, badwords_count=0, neutral_count=4),
    ]

    report = format_monthly_report(records, 2026, 6)

    assert "В этом месяце матов не было." in report
    assert "🥇 Neutral — 0" not in report
    assert "📊 Всего матов за месяц: 0" in report
    assert report.endswith("🟡 Нейтральных ругательств за месяц: 4")
