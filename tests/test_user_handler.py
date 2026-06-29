from handlers.user_handler import format_log_word, parse_say_command


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
