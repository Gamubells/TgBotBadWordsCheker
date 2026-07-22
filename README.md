# 🤬 Telegram Swear Moderation Bot

![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)
![aiogram Version](https://img.shields.io/badge/aiogram-3.27-blue.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue.svg)
![Docker](https://img.shields.io/badge/Docker-ready-blue.svg)

**Telegram Swear Moderation Bot** is an asynchronous Telegram moderation bot that detects profanity in group chats, keeps detailed statistics for each user, and sends daily reports.

The bot is designed for performance. It uses asynchronous database access with SQLAlchemy and asyncpg, precompiled regular expressions, and a service-oriented architecture.

## ✨ Key Features

- 🧠 **Smart detection:** Recognizes profane word roots across different inflections as well as exact matches.
- 🛡️ **Evasion resistance:** Detects leetspeak substitutions (for example, `@` instead of `а`) and repeated characters such as `пппиииззздддеееццц`.
- 📊 **Chat subscriptions:** Chats can subscribe to automatic daily statistics reports.
- 🪪 **User profiles:** Users can request a compact monthly summary with their profanity index, most-used swear word, daily record, and monthly style.
- 📈 **Monthly trends:** End-of-month reports compare results with the previous month and highlight the month's most-used swear word and most active day.
- 💎 **Rare finds:** The bot automatically selects three rare words for each chat every month and posts a short message when a user finds one first.
- ⏰ **Task scheduling:** APScheduler sends daily reports at 23:01 Kyiv time.
- 🐳 **Easy deployment:** Ready to run with Docker and Docker Compose.

## 🛠 Technology Stack

- **Language:** Python 3.12
- **Framework:** aiogram 3.x
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy 2.0 (asyncio) + asyncpg
- **Scheduler:** APScheduler
- **Dependency management:** Poetry
- **Infrastructure:** Docker, Docker Compose

## 🚀 Installation and Docker Setup

This is the fastest and recommended way to run the bot on a server.

1. **Clone the repository:**

   ```bash
   git clone https://github.com/Gamubells/telegram-SwearModeration-bot.git
   cd telegram-SwearModeration-bot
   ```

2. **Configure environment variables:**

   Copy the example configuration and add your credentials, including the bot token from [@BotFather](https://t.me/BotFather):

   ```bash
   cp .env.example .env
   ```

   Make sure `DB_HOST=db` is set in `.env` when running with Docker.

3. **Start the containers:**

   ```bash
   docker compose up -d
   ```

4. **Check the logs (optional):**

   ```bash
   docker compose logs -f bot
   ```

## 💻 Local Development

Local development requires PostgreSQL and Poetry.

1. **Install dependencies:**

   ```bash
   poetry install
   ```

2. **Configure the `.env` file:**

   Use `DB_HOST=localhost` for a local database.

3. **Run the bot:**

   ```bash
   poetry run python app.py
   ```

## 📱 Bot Commands

- `/start` — Display a welcome message and verify that the bot is running.
- `/count_swears` — Show your profanity count for today.
- `/profile_swears` — Show your profanity profile for the current month.
- `/logs_swears` — Show a detailed log of detected profanity for the day, including time and message text.
- `/subscribe_swears` — Subscribe the current chat to daily reports sent at 23:01.
- `/unsubscribe_swears` — Unsubscribe the current chat from daily reports.
- `/about_swears` — Show information about the bot and its author.

## 🗂 Project Structure

The project follows separation-of-concerns principles:

- `app.py` — Application entry point and scheduler initialization.
- `handlers/` — Telegram routers and command handlers.
- `services.py` — Business logic, precompiled regular expressions, and text parsing.
- `database/` — SQLAlchemy configuration, models, and CRUD repositories.
- `scheduler.py` — Scheduled report generation and delivery.
- `bad_words_list.py` — Dictionaries and character mappings used for filtering.

## 🐛 Troubleshooting

If you experience database connection or word-counting issues, see [DEBUGGING.md](DEBUGGING.md) for solutions to common problems.
