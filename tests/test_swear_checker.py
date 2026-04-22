from utils.swear_checker import contains_bad_word


def test_clean_text():
    assert not contains_bad_word("Привет! Как твои дела сегодня?")


def test_exact_bad_word():
    assert contains_bad_word("Ну ты и чмо")


def test_uppercase_bad_word():
    assert contains_bad_word("ПИДОР, что ты натворил?")


def test_hidden_bad_word():
    """Тест: пользователь пытается спрятать мат символами"""
    assert contains_bad_word("с.у.к.а")
    assert contains_bad_word("п-и-д-о-р")


def test_false_positive():
    """Тест: ложное срабатывание"""
    assert not contains_bad_word("Он начал громко чмокать губами")


def test_punctuation_around():
    """Тест: слово прилеплено к знакам препинания"""
    assert contains_bad_word("Слушай,сука,хватит")
