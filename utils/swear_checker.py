from services import check_text_for_swears


BAD_WORDS = {"чмо", "пидор", "сука"}


def contains_bad_word(text: str) -> bool:
    badwords_count, _ = check_text_for_swears(text)
    return badwords_count > 0
