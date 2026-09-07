#!/usr/bin/env bash
#
# Скрипт деплоя FinBalance на сервере.
# Запускается на сервере через GitHub Actions (SSH). Получает секреты
# аргументами и записывает их в .env, после чего собирает и поднимает стек.
#
# Использование (локально, для отладки на сервере):
#   bash deploy/deploy.sh SECRET_KEY POSTGRES_USER POSTGRES_PASSWORD \
#        POSTGRES_DB AI_KEY_ENCRYPTION_KEY GIGACHAT_API_KEY BOT_TOKEN \
#        DEPLOY_DOMAIN CERTBOT_EMAIL GIGACHAT_CA_BUNDLE
#
# DEPLOY_DOMAIN (8-й аргумент) — если задан, выпускается/обновляется
# SSL-сертификат Let's Encrypt (certbot) для домена.
# CERTBOT_EMAIL (9-й аргумент) — email для уведомлений Let's Encrypt.
# GIGACHAT_CA_BUNDLE (10-й аргумент) — путь к PEM-файлу с корневым
# сертификатом НУЦ Минцифры ВНУТРИ контейнера.
# Значение должно совпадать с правой частью монтирования в compose.
# Если задан, деплой проверяет наличие файла на хосте и fail-fast завершается.
#
set -euo pipefail

SECRET_KEY="${1:-}"
POSTGRES_USER="${2:-postgres}"
POSTGRES_PASSWORD="${3:-postgres}"
POSTGRES_DB="${4:-finbalance}"
AI_KEY_ENCRYPTION_KEY="${5:-}"
GIGACHAT_API_KEY="${6:-}"
BOT_TOKEN="${7:-}"
DEPLOY_DOMAIN="${8:-}"
CERTBOT_EMAIL="${9:-}"
GIGACHAT_CA_BUNDLE="${10:-}"

APP_DIR="${HOME}/fin-balance"
CERT_DIR="/etc/letsencrypt/live/finbalance"
DC="docker compose -f docker-compose.yml -f docker-compose.prod.yml"

# certbot пишет в /etc/letsencrypt и биндит порт 80 — нужны права root.
SUDO=""
if [ "$(id -u)" -ne 0 ]; then
  if command -v sudo >/dev/null 2>&1; then
    SUDO="sudo"
  else
    echo "Ошибка: certbot требуется выполнить от root, но sudo недоступен." >&2
    exit 1
  fi
fi

if [ ! -d "${APP_DIR}" ]; then
  echo "Ошибка: каталог ${APP_DIR} не найден." >&2
  exit 1
fi

cd "${APP_DIR}"

# Если GIGACHAT_CA_BUNDLE задан — проверяем, что файл сертификата есть на хосте.
# Без этой проверки Docker создаст ДИРЕКТОРИЮ вместо файла, и TLS будет молча
# отклоняться (verify=<directory>).
GIGACHAT_HOST_CERT="/etc/ssl/gigachat-ca.pem"
if [ -n "${GIGACHAT_CA_BUNDLE}" ] && [ ! -s "${GIGACHAT_HOST_CERT}" ]; then
  echo "FinBalance: ошибка — GIGACHAT_CA_BUNDLE задан, но файл ${GIGACHAT_HOST_CERT} не найден или пуст." >&2
  echo "Получите корневой сертификат НУЦ Минцифры и сохраните его на сервере:" >&2
  echo "  sudo openssl s_client -showcerts -connect ngw.devices.sberbank.ru:9443 -servername ngw.devices.sberbank.ru -tls1_2 </dev/null 2>/dev/null | python3 -c \"import sys,re; c=re.findall(r'-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----',sys.stdin.read(),re.S); open('/etc/ssl/gigachat-ca.pem','w').write(c[-1]+chr(10))\"" >&2
  exit 1
fi

# Собираем .env из переданных секретов.
cat > .env <<EOF
POSTGRES_USER=${POSTGRES_USER}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_DB=${POSTGRES_DB}
SECRET_KEY=${SECRET_KEY}
AI_KEY_ENCRYPTION_KEY=${AI_KEY_ENCRYPTION_KEY}
GIGACHAT_API_KEY=${GIGACHAT_API_KEY}
BOT_TOKEN=${BOT_TOKEN}
DEPLOY_PORT=${DEPLOY_PORT:-80}
DEPLOY_PORT_SSL=${DEPLOY_PORT_SSL:-443}
GIGACHAT_CA_BUNDLE=${GIGACHAT_CA_BUNDLE}
EOF

# SSL: выпуск/продление сертификата выполняем ДО запуска стека,
# пока порт 80 свободен (standalone-режим certbot).
if [ -n "${DEPLOY_DOMAIN}" ]; then
  if [ -z "${CERTBOT_EMAIL}" ]; then
    echo "FinBalance: предупреждение — задан DEPLOY_DOMAIN, но не задан CERTBOT_EMAIL; SSL пропускается." >&2
  elif [ ! -f "${CERT_DIR}/fullchain.pem" ]; then
    echo "FinBalance: выпускаю SSL-сертификат для ${DEPLOY_DOMAIN}..."
    ${DC} stop nginx >/dev/null 2>&1 || true
    ${SUDO} certbot certonly \
      --standalone \
      --non-interactive \
      --agree-tos \
      --email "${CERTBOT_EMAIL}" \
      --cert-name finbalance \
      --domains "${DEPLOY_DOMAIN}"
  else
    echo "FinBalance: продлеваю SSL-сертификат для ${DEPLOY_DOMAIN}..."
    ${DC} stop nginx >/dev/null 2>&1 || true
    ${SUDO} certbot renew --non-interactive || true
  fi
fi

echo "FinBalance: сборка и запуск контейнеров..."

${DC} build
${DC} up -d --remove-orphans

# После подъёма nginx перечитывает сертификат.
${DC} exec nginx nginx -s reload || true

echo "FinBalance: проверка состояния сервисов..."
${DC} ps

echo "FinBalance: деплой завершён."
