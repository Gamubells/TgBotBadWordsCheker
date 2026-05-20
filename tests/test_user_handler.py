from handlers.user_handler import format_log_word


def test_format_log_word_marks_neutral_words():
    assert format_log_word("дурак", "neutral") == "🟡 дурак"


def test_format_log_word_leaves_swear_words_unmarked():
    assert format_log_word("сука", "swear") == "сука"


def test_format_log_word_escapes_html():
    assert format_log_word("<word>", "neutral") == "🟡 &lt;word&gt;"
