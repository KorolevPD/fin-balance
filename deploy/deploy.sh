#!/usr/bin/env bash
#
# Скрипт деплоя FinBalance на сервере.
# Запускается на сервере через GitHub Actions (SSH). Получает секреты
# аргументами и записывает их в .env, после чего собирает и поднимает стек.
#
# Использование (локально, для отладки на сервере):
#   bash deploy/deploy.sh SECRET_KEY POSTGRES_USER POSTGRES_PASSWORD \
#        POSTGRES_DB AI_KEY_ENCRYPTION_KEY GEMINI_API_KEY BOT_TOKEN \
#        DEPLOY_DOMAIN CERTBOT_EMAIL
#
# DEPLOY_DOMAIN (8-й аргумент) — если задан, выпускается/обновляется
# SSL-сертификат Let's Encrypt (certbot) для домена.
# CERTBOT_EMAIL (9-й аргумент) — email для уведомлений Let's Encrypt.
#
set -euo pipefail

SECRET_KEY="${1:-}"
POSTGRES_USER="${2:-postgres}"
POSTGRES_PASSWORD="${3:-postgres}"
POSTGRES_DB="${4:-finbalance}"
AI_KEY_ENCRYPTION_KEY="${5:-}"
GEMINI_API_KEY="${6:-}"
BOT_TOKEN="${7:-}"
DEPLOY_DOMAIN="${8:-}"
CERTBOT_EMAIL="${9:-}"

APP_DIR="${HOME}/fin-balance"
CERT_DIR="/etc/letsencrypt/live/finbalance"
DC="docker compose -f docker-compose.yml -f docker-compose.prod.yml"

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
DEPLOY_PORT_SSL=${DEPLOY_PORT_SSL:-443}
EOF

# SSL: если сертификата ещё нет — выпускаем его ДО запуска стека
# (standalone слушает порт 80, который пока свободен).
if [ -n "${DEPLOY_DOMAIN}" ] && [ ! -f "${CERT_DIR}/fullchain.pem" ]; then
  echo "FinBalance: выпускаю SSL-сертификат для ${DEPLOY_DOMAIN}..."
  ${DC} stop nginx >/dev/null 2>&1 || true
  certbot certonly \
    --standalone \
    --non-interactive \
    --agree-tos \
    --email "${CERTBOT_EMAIL}" \
    --cert-name finbalance \
    --domains "${DEPLOY_DOMAIN}"
fi

echo "FinBalance: сборка и запуск контейнеров..."

${DC} build
${DC} up -d --remove-orphans

# SSL: продление сертификата (порт 80 занят nginx → останавливаем на время renew).
if [ -n "${DEPLOY_DOMAIN}" ] && [ -f "${CERT_DIR}/fullchain.pem" ]; then
  echo "FinBalance: продлеваю SSL-сертификат для ${DEPLOY_DOMAIN}..."
  ${DC} stop nginx
  certbot renew --non-interactive || true
  ${DC} start nginx
  ${DC} exec nginx nginx -s reload || true
fi

echo "FinBalance: проверка состояния сервисов..."
${DC} ps

echo "FinBalance: деплой завершён."