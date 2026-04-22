from utils.swear_checker import contains_bad_word


def test_clean_text():
    """Проверка обычного, чистого сообщения"""
    assert contains_bad_word("Привет! Как твои дела сегодня?") == False


def test_exact_bad_word():
    """Проверка точного совпадения плохого слова"""
    assert contains_bad_word("Ну ты и чмо") == True


def test_uppercase_bad_word():
    """Проверка слова, написанного ЗАГЛАВНЫМИ буквами (или ЗаБоРчИкОм)"""
    assert contains_bad_word("ПИДОР, что ты натворил?") == True
    assert contains_bad_word("СУКА, забыл ключи") == True


def test_empty_text():
    """Проверка пустого сообщения (чтобы бот не падал, если прислали просто картинку без текста)"""
    assert contains_bad_word("") == False
    assert contains_bad_word(None) == False


def test_hidden_bad_word():
    """Тест: пользователь пытается спрятать мат символами"""
    assert contains_bad_word("с.у.к.а") == True
    assert contains_bad_word("п-и-д-о-р") == True


def test_false_positive():
    """Тест: ложное срабатывание. Слово 'чмокать' содержит 'чмо', но это не мат."""
    assert contains_bad_word("Он начал громко чмокать губами") == False


def test_punctuation_around():
    """Тест: слово прилеплено к знакам препинания"""
    assert contains_bad_word("Слушай,сука,хватит") == True
