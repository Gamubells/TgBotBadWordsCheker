from prometheus_client import Counter, Gauge


MESSAGES_TOTAL = Counter("bot_messages_total", "Общее количество полученных текстовых сообщений")

SWEARS_TOTAL = Counter("bot_swears_total", "Общее количество заблокированных матерных слов")

ACTIVE_SUBSCRIPTIONS = Gauge(
    "bot_active_subscriptions", "Текущее количество чатов с подпиской на отчеты"
)
