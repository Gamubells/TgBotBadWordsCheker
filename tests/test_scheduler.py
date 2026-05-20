from types import SimpleNamespace

from scheduler import format_daily_report


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
