from database.db import Settings


def test_database_url_escapes_password_special_characters():
    settings = Settings(
        DB_HOST="db",
        DB_PORT=5432,
        DB_USER="user",
        DB_PASS="p@ss:word",
        DB_NAME="name",
        BOT_TOKEN="test-token",
        ADMIN_ID="1",
        DATABASE_URL=None,
    )

    assert settings.DATABASE_URL == ("postgresql+asyncpg://user:p%40ss%3Aword@db:5432/name")
