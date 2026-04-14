import re

from bad_words_list import EXACT_WORDS, LEETSPEAK_MAP, ROOT_WORDS


WORD_PATTERN = re.compile(r"[а-яёa-z0-9]+")
DUPLICATE_PATTERN = re.compile(r"(.)\1+")


def check_text_for_swears(text: str) -> tuple[int, list[str]]:
    if not text:
        return 0, []

    text = text.lower().translate(LEETSPEAK_MAP)

    words = WORD_PATTERN.findall(text)

    badwords_count = 0
    found_words = []

    processed_words = [DUPLICATE_PATTERN.sub(r"\1", w) for w in words]

    for word in processed_words:
        if word in EXACT_WORDS:
            badwords_count += 1
            found_words.append(word)
            continue

        for root in ROOT_WORDS:
            if word.startswith(root):
                badwords_count += 1
                found_words.append(word)
                break

    return badwords_count, found_words
