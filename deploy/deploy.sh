#!/usr/bin/env bash
#
# Скрипт деплоя FinBalance на сервере.
# Запускается на сервере через GitHub Actions (SSH). Получает секреты
# аргументами и записывает их в .env, после чего собирает и поднимает стек.
#
# Использование (локально, для отладки на сервере):
#   bash deploy/deploy.sh SECRET_KEY POSTGRES_USER POSTGRES_PASSWORD \
#        POSTGRES_DB AI_KEY_ENCRYPTION_KEY GEMINI_API_KEY BOT_TOKEN
#
set -euo pipefail

SECRET_KEY="${1:-}"
POSTGRES_USER="${2:-postgres}"
POSTGRES_PASSWORD="${3:-postgres}"
POSTGRES_DB="${4:-finbalance}"
AI_KEY_ENCRYPTION_KEY="${5:-}"
GEMINI_API_KEY="${6:-}"
BOT_TOKEN="${7:-}"

APP_DIR="${HOME}/fin-balance"

if [ ! -d "${APP_DIR}" ]; then
  echo "Ошибка: каталог ${APP_DIR} не найден." >&2
  exit 1
fi

cd "${APP_DIR}"

# Собираем .env из переданных секретов.
cat > .env <<EOF
POSTGRES_USER=${POSTGRES_USER}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_DB=${POSTGRES_DB}
SECRET_KEY=${SECRET_KEY}
AI_KEY_ENCRYPTION_KEY=${AI_KEY_ENCRYPTION_KEY}
GEMINI_API_KEY=${GEMINI_API_KEY}
BOT_TOKEN=${BOT_TOKEN}
DEPLOY_PORT=${DEPLOY_PORT:-80}
EOF

echo "FinBalance: сборка и запуск контейнеров..."

docker compose -f docker-compose.yml -f docker-compose.prod.yml build
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --remove-orphans

echo "FinBalance: проверка состояния сервисов..."
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps

echo "FinBalance: деплой завершён."
