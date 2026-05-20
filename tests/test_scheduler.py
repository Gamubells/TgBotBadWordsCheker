from types import SimpleNamespace

from scheduler import format_daily_report


def test_daily_report_is_sorted_by_swear_count_descending():
    records = [
        SimpleNamespace(username="Second", user_id=2, badwords_count=7),
        SimpleNamespace(username="First", user_id=1, badwords_count=12),
        SimpleNamespace(username="Third", user_id=3, badwords_count=3),
    ]

    report = format_daily_report(records)

    assert report.index("🥇 First — 12") < report.index("🥈 Second — 7")
    assert report.index("🥈 Second — 7") < report.index("🥉 Third — 3")


def test_daily_report_uses_numbered_places_after_top_three():
    records = [
        SimpleNamespace(username=f"User {place}", user_id=place, badwords_count=count)
        for place, count in enumerate([10, 9, 8, 7], start=1)
    ]

    report = format_daily_report(records)

    assert "4. User 4 — 7" in report


def test_daily_report_falls_back_to_user_id_without_username():
    records = [SimpleNamespace(username=None, user_id=123, badwords_count=5)]

    report = format_daily_report(records)

    assert "🥇 123 — 5" in report


def test_daily_report_shows_total_swear_count():
    records = [
        SimpleNamespace(username="First", user_id=1, badwords_count=12),
        SimpleNamespace(username="Second", user_id=2, badwords_count=7),
    ]

    report = format_daily_report(records)

    assert report.endswith("📊 Всего: 19")
