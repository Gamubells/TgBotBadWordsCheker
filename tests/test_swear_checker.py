import pytest

from bad_words_list import EXACT_WORDS, ROOT_WORDS
from services import check_text_for_swears


def contains_bad_word(text: str) -> bool:
    count, _ = check_text_for_swears(text)
    return count > 0


def test_clean_text():
    assert not contains_bad_word("Привет! Как твои дела сегодня?")


def test_exact_bad_word():
    assert contains_bad_word("Ну ты и чмо")


def test_uppercase_bad_word():
    assert contains_bad_word("ПИДОР, что ты натворил?")


def test_hidden_bad_word():
    assert contains_bad_word("с.у.к.а")
    assert contains_bad_word("п-и-д-о-р")


def test_false_positive():
    assert not contains_bad_word("Он начал громко чмокать губами")
    assert not contains_bad_word("Сукно лежит на столе")
    assert not contains_bad_word("Херсон сегодня солнечный")


def test_punctuation_around():
    assert contains_bad_word("Слушай,сука,хватит")


def test_exact_phrase():
    assert contains_bad_word("Ну это голем пучеглазый")


@pytest.mark.parametrize("word", EXACT_WORDS)
def test_all_exact_words_are_detected(word):
    count, found_words = check_text_for_swears(f"ну {word} тут")

    assert count >= 1
    assert word in found_words


@pytest.mark.parametrize("root", ROOT_WORDS)
def test_all_roots_are_detected(root):
    word = f"{root}овый"

    count, found_words = check_text_for_swears(f"ну {word} тут")

    assert count == 1
    assert found_words == [word]


def test_counts_multiple_swears_in_one_message():
    count, found_words = check_text_for_swears("сука, какой-то дебил и п-и-д-о-р")

    assert count == 3
    assert found_words == ["сука", "дебил", "пидор"]


def test_duplicate_letters_are_normalized():
    count, found_words = check_text_for_swears("суууука")

    assert count == 1
    assert found_words == ["сука"]


def test_leetspeak_is_normalized():
    count, found_words = check_text_for_swears("cyk@")

    assert count == 1
    assert found_words == ["сука"]


def test_word_lists_have_no_duplicates():
    assert len(ROOT_WORDS) == len(set(ROOT_WORDS))
    assert len(EXACT_WORDS) == len(set(EXACT_WORDS))


def test_exact_words_do_not_duplicate_root_coverage():
    covered_exact_words = [
        word
        for word in EXACT_WORDS
        if " " not in word and any(word.startswith(root) for root in ROOT_WORDS)
    ]

    assert covered_exact_words == []


def test_empty_text_is_clean():
    assert check_text_for_swears("") == (0, [])
    assert check_text_for_swears("   ") == (0, [])


def test_exact_phrase_with_extra_spaces_is_detected_once():
    count, found_words = check_text_for_swears("это голем     пучеглазый сегодня")

    assert count == 1
    assert found_words == ["голем     пучеглазый"]


def test_exact_phrase_does_not_double_count_inner_words():
    count, found_words = check_text_for_swears("хуесос кальянщик")

    assert count == 1
    assert found_words == ["хуесос кальянщик"]


def test_exact_phrase_requires_word_boundaries():
    assert check_text_for_swears("големпучеглазый") == (0, [])


def test_mixed_phrase_exact_word_and_root_count_together():
    count, found_words = check_text_for_swears("голем пучеглазый, сука, разьебал")

    assert count == 3
    assert found_words == ["голем пучеглазый", "сука", "разьебал"]


def test_obfuscated_word_with_symbols_counts_once():
    count, found_words = check_text_for_swears("п.и.з.д.е.ц")

    assert count == 1
    assert found_words == ["пиздец"]


def test_normal_word_containing_exact_word_is_not_detected():
    assert check_text_for_swears("сукинсын") == (0, [])


def test_leetspeak_with_uppercase_is_normalized():
    count, found_words = check_text_for_swears("CYK@")

    assert count == 1
    assert found_words == ["сука"]


def test_duplicate_letters_in_root_word_are_normalized():
    count, found_words = check_text_for_swears("пииииздец")

    assert count == 1
    assert found_words == ["пиздец"]


def test_multiple_occurrences_of_same_swear_are_counted():
    count, found_words = check_text_for_swears("сука сука")

    assert count == 2
    assert found_words == ["сука", "сука"]


def test_exact_phrase_across_newline_is_detected():
    count, found_words = check_text_for_swears("голем\nпучеглазый")

    assert count == 1
    assert found_words == ["голем\nпучеглазый"]


def test_exact_phrase_with_punctuation_boundaries_is_detected():
    count, found_words = check_text_for_swears("(голем пучеглазый)!")

    assert count == 1
    assert found_words == ["голем пучеглазый"]


def test_phrase_match_does_not_remove_neighboring_swears():
    count, found_words = check_text_for_swears("сука голем пучеглазый херня")

    assert count == 3
    assert found_words == ["голем пучеглазый", "сука", "херня"]


def test_legal_double_letters_are_not_over_normalized():
    count, found_words = check_text_for_swears("ссанина и фаллос")

    assert count == 2
    assert found_words == ["ссанина", "фаллос"]


def test_leetspeak_digits_are_normalized():
    count, found_words = check_text_for_swears("xyeBo")

    assert count == 1
    assert found_words == ["хуево"]


def test_obfuscated_exact_word_with_underscores_is_detected():
    count, found_words = check_text_for_swears("с_у_к_а")

    assert count == 1
    assert found_words == ["сука"]


def test_obfuscated_two_letter_word_is_not_detected_by_symbol_joiner():
    assert check_text_for_swears("л-о") == (0, [])


def test_numbers_do_not_create_false_positive():
    assert check_text_for_swears("номер 1304") == (0, [])
