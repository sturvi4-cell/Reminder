#!/usr/bin/env bash
# One-command install/update for Telegram reminder bot.
# Idempotent: first run clones+builds+starts; subsequent runs pull+rebuild+restart.
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/sturvi4-cell/Reminder.git}"
BRANCH="${BRANCH:-main}"
APP_DIR="${APP_DIR:-$HOME/Reminder}"
IMAGE="reminder-bot:latest"
CONTAINER="reminder-bot"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker не установлен. Поставьте: https://docs.docker.com/engine/install/" >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "ERROR: docker недоступен (нужны права или sudo). Попробуйте 'sudo bash install.sh'." >&2
  exit 1
fi

if [ -d "$APP_DIR/.git" ]; then
  echo ">> Обновляю репозиторий в $APP_DIR"
  git -C "$APP_DIR" fetch origin "$BRANCH"
  git -C "$APP_DIR" checkout "$BRANCH"
  git -C "$APP_DIR" pull --ff-only origin "$BRANCH"
else
  echo ">> Клонирую $REPO_URL -> $APP_DIR"
  git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR"

if [ ! -f .env ]; then
  cp .env.example .env
  echo ""
  echo "!! Создан .env из .env.example."
  echo "!! Заполните BOT_TOKEN, OPENROUTER_API_KEY, REGISTRATION_SECRET и запустите снова:"
  echo "   bash install.sh"
  exit 0
fi

mkdir -p "$APP_DIR/data"

echo ">> Собираю образ"
docker build -t "$IMAGE" .

echo ">> Пересаживаю контейнер"
docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
docker run -d \
  --name "$CONTAINER" \
  --restart=unless-stopped \
  -v "$APP_DIR/data:/app/data" \
  --env-file "$APP_DIR/.env" \
  "$IMAGE"

docker image prune -f >/dev/null 2>&1 || true

echo ""
echo ">> Готово."
echo ">> Статус:  docker ps --filter name=$CONTAINER"
echo ">> Логи:    docker logs -f $CONTAINER"
echo ">> Рестарт: docker restart $CONTAINER"
echo ">> Update:  bash install.sh  (повторно — pull + rebuild + restart)"
