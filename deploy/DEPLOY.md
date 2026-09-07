# Развёртывание FinBalance (CI/CD + сервер)

В этой инструкции описано, **что нужно от вас**, чтобы настроить автоматический
деплой на арендованный сервер через GitHub Actions по SSH, и как устроен пайплайн.

## Что будет работать после настройки

1. При **push / merge в ветку `main`** GitHub Actions автоматически:
   - собирает Docker-образы и разворачивает стек на сервере по SSH;
   - применяет миграции Alembic и перезапускает сервисы.
2. Отдельный workflow **CI** уже есть: линт Python (ruff) и JS-тесты.
3. Серверный Gemini-ключ: если в секретах GitHub заполнен `GEMINI_API_KEY`,
   все пользователи используют его, а поле ввода своего ключа на сайте скрыто.

## Что мне нужно от вас (данные сервера)

Для фактического запуска деплоя предоставьте:

| Параметр | Пример | Зачем |
|---|---|---|
| **IP / хост сервера** | `203.0.113.10` или `app.example.com` | GitHub подключается к серверу |
| **Пользователь SSH** | `ubuntu`, `deploy`, `root` | Пользователь для входа по SSH |
| **SSH-порт** | `22` (или нестандартный) | Порт SSH |
| **Приватный SSH-ключ** | содержимое `~/.ssh/id_rsa` (или новой keypair) | Авторизация GitHub на сервере |
| **ОС сервера** | Ubuntu 22.04 / Debian 12 и т.п. | Требуемые команды установки Docker |
| **Домен** | `app.example.com` | Уже настроен на сервер? под какой Виртуальный хост |
| **Официальный домен должен указывать на IP сервера** | A-запись | Чтобы nginx и SSL работали корректно |

> Пока этих данных нет, деплой **не запускается**. Всё остальное уже готово:
> workflow, скрипт деплоя, переопределения для прод-состава.

## Что нужно сделать на сервере (один раз)

1. Установить **Docker** и **Docker Compose plugin**:
   ```bash
   sudo apt-get update
   sudo apt-get install -y docker.io docker-compose-plugin
   echo 'export PATH=$PATH:/usr/bin/docker' >> ~/.bashrc
   ```
2. Создать пользователя для деплоя (если вход не под root) и добавить его в
   группу `docker`:
   ```bash
   sudo useradd -m -s /bin/bash deploy
   sudo usermod -aG docker deploy
   # Скопировать свой публичный ключ или ключ GitHub Actions
   ```
3. Убедиться, что порт `80` (и `443`, если включаете HTTPS) открыт в
   файрволе/провайдере и свободен.

## Секреты GitHub Actions (Settings → Secrets and variables → Actions)

Создайте следующие **Repository secrets** (все секреты — в GitHub, `.env` на
сервере генерируется при деплое автоматически):

| Secret | Назначение |
|---|---|
| `DEPLOY_HOST` | IP/хост сервера |
| `DEPLOY_USER` | Пользователь SSH |
| `DEPLOY_SSH_PORT` | Порт SSH (например `22`) |
| `DEPLOY_SSH_KEY` | Приватный SSH-ключ (multiline) |
| `SECRET_KEY` | Секрет JWT приложения (случайная длинная строка) |
| `POSTGRES_USER` | Пользователь PostgreSQL |
| `POSTGRES_PASSWORD` | Пароль PostgreSQL |
| `POSTGRES_DB` | Имя базы данных (например `finbalance`) |
| `AI_KEY_ENCRYPTION_KEY` | Ключ шифрования AI-ключей пользователей (AES-GCM) |
| `GEMINI_API_KEY` | **Серверный Gemini-ключ** (пустой = пользователи вводят свой) |
| `BOT_TOKEN` | Токен Telegram-бота (пустой = бот выключен) |
| `DEPLOY_DOMAIN` | **Домен**, указывающий на IP сервера (например `app.example.com`). Если не задан — SSL не выпускается. |
| `CERTBOT_EMAIL` | Email для уведомлений Let's Encrypt (при выпуске сертификата) |

Рекомендуемые значения (сгенерировать):
```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"   # SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"   # AI_KEY_ENCRYPTION_KEY
python -c "import secrets; print(secrets.token_urlsafe(24))"   # POSTGRES_PASSWORD
```

## HTTPS (Let's Encrypt)

SSL выпускается автоматически при деплое, если задан секрет `DEPLOY_DOMAIN`:

1. Сертификат Let's Encrypt выпускается через `certbot` при первом деплое
   (сервис `nginx` временно останавливается, затем поднимается уже по HTTPS).
2. При последующих деплоях сертификат продлевается (`certbot renew`),
   nginx перезагружается.
3. HTTP (порт 80) переадресует на HTTPS (порт 443).

**Требования на сервере (установить один раз):**
```bash
sudo apt-get update
sudo apt-get install -y certbot
```

Порт `443` должен быть открыт в файрволе/провайдере, а домен — указывать на
IP этого сервера (A-запись).

**Ручное продление** (если деплой долго не запускался):
```bash
sudo certbot renew
```

## Файлы деплоя

- `.github/workflows/deploy.yml` — workflow деплоя (push в `main` + ручной запуск).
- `deploy/deploy.sh` — скрипт на сервере: пишет `.env`, выпускает/обновляет
  SSL-сертификат, собирает и поднимает стек.
- `docker-compose.prod.yml` — переопределения для продакшена (без `--reload`,
  без bind-mount, только nginx наружу; монтирует `/etc/letsencrypt`).
- `nginx/nginx.conf` — HTTP→HTTPS: ACME-challenge на 80, сайт на 443.
