import re

from bad_words_list import EXACT_WORDS, LEETSPEAK_MAP, ROOT_WORDS


WORD_PATTERN = re.compile(r"[а-яёa-z0-9]+")
NON_WORD_CHAR_PATTERN = re.compile(r"[^а-яёa-z0-9]")
DUPLICATE_PATTERN = re.compile(r"(.)\1+")
OBFUSCATED_WORD_PATTERN = re.compile(
    r"(?<![а-яёa-z0-9])(?:[а-яёa-z0-9][^а-яёa-z0-9\s]+){2,}[а-яёa-z0-9](?![а-яёa-z0-9])"
)
EXACT_PHRASES = tuple(word for word in EXACT_WORDS if " " in word)
EXACT_WORDS_SET = {word for word in EXACT_WORDS if " " not in word}
EXACT_WORD_ALIASES = {
    word.translate(LEETSPEAK_MAP): word
    for word in EXACT_WORDS_SET
    if word.translate(LEETSPEAK_MAP) != word
}
EXACT_PHRASE_PATTERNS = tuple(
    re.compile(rf"(?<![а-яёa-z0-9]){r'\s+'.join(map(re.escape, phrase.split()))}(?![а-яёa-z0-9])")
    for phrase in EXACT_PHRASES
)


def _normalize_word(word: str) -> str:
    return DUPLICATE_PATTERN.sub(r"\1", word)


def _is_bad_word(word: str) -> bool:
    if word in EXACT_WORDS_SET:
        return True

    for root in ROOT_WORDS:
        if not word.startswith(root):
            continue

        return True

    return False


def _find_bad_word(word: str) -> str | None:
    if word in EXACT_WORD_ALIASES:
        return EXACT_WORD_ALIASES[word]

    if _is_bad_word(word):
        return word

    normalized_word = _normalize_word(word)
    if normalized_word in EXACT_WORD_ALIASES:
        return EXACT_WORD_ALIASES[normalized_word]

    if normalized_word != word and _is_bad_word(normalized_word):
        return normalized_word

    return None


def check_text_for_swears(text: str) -> tuple[int, list[str]]:
    if not text:
        return 0, []

    text = text.lower().translate(LEETSPEAK_MAP)

    phrase_matches = []
    for pattern in EXACT_PHRASE_PATTERNS:
        phrase_matches.extend(match.group(0) for match in pattern.finditer(text))
        text = pattern.sub(" ", text)

    words = WORD_PATTERN.findall(text)
    obfuscated_words = [
        NON_WORD_CHAR_PATTERN.sub("", match.group(0))
        for match in OBFUSCATED_WORD_PATTERN.finditer(text)
    ]

    badwords_count = 0
    found_words = []

    for phrase in phrase_matches:
        badwords_count += 1
        found_words.append(phrase)

    for word in words + obfuscated_words:
        bad_word = _find_bad_word(word)
        if bad_word:
            badwords_count += 1
            found_words.append(bad_word)

    return badwords_count, found_words
