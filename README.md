# Reminder Bot

Telegram-бот для напоминаний на естественном русском языке.
Парсит фразы вроде «сегодня в 3», «завтра в 15:00», «каждый день в 9 утра»
через LLM на OpenRouter и в нужное время шлёт сообщение с инлайн-клавиатурой.
Если пользователь не нажал **«Принято»** — бот повторяет напоминание
каждые 10 минут (настраивается).

## Установка / обновление (одна команда)

```bash
curl -fsSL https://raw.githubusercontent.com/sturvi4-cell/reminder/main/install.sh -o install.sh && bash install.sh
```

или вручную:

```bash
git clone https://github.com/sturvi4-cell/reminder.git
cd reminder
bash install.sh
```

Первый запуск создаст `.env` из шаблона и попросит заполнить.
Повторный запуск `bash install.sh` сделает `git pull`, ребилд образа и перезапуск контейнера.

## Переменные окружения (`.env`)

| Переменная | Описание |
|---|---|
| `BOT_TOKEN` | Telegram-токен от @BotFather |
| `OPENROUTER_API_KEY` | Ключ OpenRouter |
| `OPENROUTER_MODEL` | Модель (по умолчанию `google/gemini-2.5-flash-lite`) |
| `WHITELIST_USER_IDS` | Telegram user ID через запятую |
| `WHITELIST_USERNAMES` | Telegram username через запятую (без @) |
| `REPEAT_INTERVAL_MIN` | Интервал повтора (мин), дефолт 10 |
| `TIMEZONE` | Таймзона отображения, дефолт `Asia/Baku` |
| `LOG_LEVEL` | `DEBUG` / `INFO` / `WARNING` |

## Команды бота

- `/start` — регистрация
- `/help` — справка и примеры
- `/list` — все активные напоминания (с кнопкой «Удалить»)
- `/cancel <id>` — удалить напоминание по ID
- любой свободный текст — создать напоминание

## Примеры

```
сегодня в 18:00 позвонить маме
завтра в 9 утра планёрка
каждый день в 22:00 принять таблетку
каждый понедельник в 9 утра тренировка
каждый будний день в 8:30 зарядка
через 30 минут проверить духовку
```

## Управление контейнером

```bash
docker logs -f reminder-bot     # логи
docker restart reminder-bot     # перезапуск
docker stop reminder-bot        # остановить
docker rm -f reminder-bot       # удалить
```

Данные (SQLite) лежат в `./data/bot.db` и переживают пересоздание контейнера.
