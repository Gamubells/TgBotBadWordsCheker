from prometheus_client import Counter


MESSAGES_TOTAL = Counter("bot_messages_total", "Общее количество полученных текстовых сообщений")

SWEARS_TOTAL = Counter("bot_swears_total", "Общее количество заблокированных матерных слов")
