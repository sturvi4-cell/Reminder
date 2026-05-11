# Reminder Bot

Telegram-бот для напоминаний на естественном языке (русский / azərbaycan / English).
Парсит фразы вроде «сегодня в 3», «завтра в 15:00», «каждый день в 9 утра»,
«sabah saat 15:00 ana zəng et», «every weekday at 8:30 standup» через LLM на
OpenRouter и в нужное время шлёт сообщение с инлайн-клавиатурой.

Если пользователь не нажал **«Принято»** — бот повторяет напоминание
каждые 10 минут (настраивается) до подтверждения.

## Установка / обновление одной командой

```bash
git clone https://github.com/sturvi4-cell/reminder.git ~/Reminder
cd ~/Reminder && bash install.sh
```

Первый запуск создаст `.env` из шаблона и попросит заполнить.
**Повторный запуск той же команды** — `git pull`, ребилд образа и перезапуск
контейнера. Никакого мусора кроме `~/Reminder/` и одного docker-образа.

```bash
bash ~/Reminder/install.sh   # обновление + рестарт
```

## Авторизация

Регистрация по секретному слову. Любой, кто пришлёт боту значение
`REGISTRATION_SECRET` из `.env` одним сообщением, будет зарегистрирован и
получит доступ. До этого бот игнорирует команды и просит секрет.

Поменять секрет — отредактировать `.env` и `docker restart reminder-bot`.
Уже зарегистрированных пользователей это не отключает (они в БД).

## Переменные окружения (`.env`)

| Переменная | Описание |
|---|---|
| `BOT_TOKEN` | Telegram-токен от @BotFather |
| `OPENROUTER_API_KEY` | Ключ OpenRouter |
| `OPENROUTER_MODEL` | Модель (по умолчанию `google/gemini-2.5-flash-lite`) |
| `REGISTRATION_SECRET` | Слово-пароль для регистрации новых пользователей |
| `REPEAT_INTERVAL_MIN` | Интервал повтора (мин), дефолт 10 |
| `TIMEZONE` | Таймзона отображения, дефолт `Asia/Baku` |
| `LOG_LEVEL` | `DEBUG` / `INFO` / `WARNING` |

## Команды бота

- `/start` — приветствие и справка
- `/help` — справка с примерами
- `/list` — все активные напоминания (с кнопкой «Удалить» под каждым)
- `/cancel <id>` — удалить напоминание по ID
- любой свободный текст — создать напоминание

## Примеры формулировок

```
сегодня в 18:00 позвонить маме
завтра в 9 утра планёрка
каждый день в 22:00 принять таблетку
каждый понедельник в 9 утра тренировка
каждый будний день в 8:30 зарядка
через 30 минут проверить духовку

sabah saat 15:00 ana zəng et
hər gün saat 22:00 dərmanı qəbul et
hər bazar ertəsi saat 9-da idman

tomorrow at 9am standup
every weekday at 8:30 morning workout
in 30 minutes check the oven
```

## Управление контейнером

```bash
docker logs -f reminder-bot     # логи
docker restart reminder-bot     # перезапуск
docker stop reminder-bot        # остановить
docker rm -f reminder-bot       # удалить
```

Данные (SQLite) лежат в `./data/bot.db` и переживают пересоздание контейнера.
