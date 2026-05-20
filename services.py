import re
from dataclasses import dataclass

from bad_words_list import EXACT_WORDS, LEETSPEAK_MAP, NEUTRAL_WORDS, ROOT_WORDS


WORD_PATTERN = re.compile(r"[а-яёa-z0-9]+")
NON_WORD_CHAR_PATTERN = re.compile(r"[^а-яёa-z0-9]")
DUPLICATE_PATTERN = re.compile(r"(.)\1+")
OBFUSCATED_WORD_PATTERN = re.compile(
    r"(?<![а-яёa-z0-9])(?:[а-яёa-z0-9][^а-яёa-z0-9\s]+){2,}[а-яёa-z0-9](?![а-яёa-z0-9])"
)


@dataclass(frozen=True)
class SwearCheckResult:
    swear_count: int
    swear_words: list[str]
    neutral_count: int
    neutral_words: list[str]


def _compile_phrase_patterns(words: tuple[str, ...]) -> tuple[re.Pattern, ...]:
    return tuple(
        re.compile(
            rf"(?<![а-яёa-z0-9]){r'\s+'.join(map(re.escape, phrase.split()))}"
            rf"(?![а-яёa-z0-9])"
        )
        for phrase in words
        if " " in phrase
    )


EXACT_WORDS_SET = {word for word in EXACT_WORDS if " " not in word}
NEUTRAL_WORDS_SET = {word for word in NEUTRAL_WORDS if " " not in word}
EXACT_WORD_ALIASES = {
    word.translate(LEETSPEAK_MAP): word
    for word in EXACT_WORDS_SET
    if word.translate(LEETSPEAK_MAP) != word
}
NEUTRAL_WORD_ALIASES = {
    word.translate(LEETSPEAK_MAP): word
    for word in NEUTRAL_WORDS_SET
    if word.translate(LEETSPEAK_MAP) != word
}
EXACT_PHRASE_PATTERNS = _compile_phrase_patterns(EXACT_WORDS)
NEUTRAL_PHRASE_PATTERNS = _compile_phrase_patterns(NEUTRAL_WORDS)


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


def _find_word(
    word: str,
    *,
    exact_words: set[str],
    aliases: dict[str, str],
    include_roots: bool = False,
) -> str | None:
    if word in aliases:
        return aliases[word]

    if word in exact_words:
        return word

    if include_roots and _is_bad_word(word):
        return word

    normalized_word = _normalize_word(word)
    if normalized_word in aliases:
        return aliases[normalized_word]

    if normalized_word in exact_words:
        return normalized_word

    if include_roots and normalized_word != word and _is_bad_word(normalized_word):
        return normalized_word

    return None


def check_text_for_swears_detailed(text: str) -> SwearCheckResult:
    if not text:
        return SwearCheckResult(0, [], 0, [])

    text = text.lower().translate(LEETSPEAK_MAP)

    swear_phrase_matches = []
    for pattern in EXACT_PHRASE_PATTERNS:
        swear_phrase_matches.extend(match.group(0) for match in pattern.finditer(text))
        text = pattern.sub(" ", text)

    neutral_phrase_matches = []
    for pattern in NEUTRAL_PHRASE_PATTERNS:
        neutral_phrase_matches.extend(match.group(0) for match in pattern.finditer(text))
        text = pattern.sub(" ", text)

    words = WORD_PATTERN.findall(text)
    obfuscated_words = [
        NON_WORD_CHAR_PATTERN.sub("", match.group(0))
        for match in OBFUSCATED_WORD_PATTERN.finditer(text)
    ]

    swear_words = []
    neutral_words = []

    swear_words.extend(swear_phrase_matches)
    neutral_words.extend(neutral_phrase_matches)

    for word in words + obfuscated_words:
        swear_word = _find_word(
            word,
            exact_words=EXACT_WORDS_SET,
            aliases=EXACT_WORD_ALIASES,
            include_roots=True,
        )
        if swear_word:
            swear_words.append(swear_word)
            continue

        neutral_word = _find_word(
            word,
            exact_words=NEUTRAL_WORDS_SET,
            aliases=NEUTRAL_WORD_ALIASES,
        )
        if neutral_word:
            neutral_words.append(neutral_word)

    return SwearCheckResult(
        swear_count=len(swear_words),
        swear_words=swear_words,
        neutral_count=len(neutral_words),
        neutral_words=neutral_words,
    )


def check_text_for_swears(text: str) -> tuple[int, list[str]]:
    result = check_text_for_swears_detailed(text)

    return result.swear_count, result.swear_words
