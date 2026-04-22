import re


BAD_WORDS = {"чмо", "пидор", "сука"}


def contains_bad_word(text: str) -> bool:
    if not text:
        return False

    text_lower = text.lower()

    for word in BAD_WORDS:
        pattern_body = r"[\W_]*".join(list(word))

        pattern = rf"\b{pattern_body}\b"

        if re.search(pattern, text_lower):
            return True

    return False
