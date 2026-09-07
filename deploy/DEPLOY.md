# Развёртывание FinBalance (CI/CD + сервер)

В этой инструкции описано, **что нужно от вас**, чтобы настроить автоматический
деплой на арендованный сервер через GitHub Actions по SSH, и как устроен пайплайн.

## Что будет работать после настройки

1. При **push / merge в ветку `main`** GitHub Actions автоматически:
   - собирает SPA-**фронтенд на GitHub runner** (сервер не выполняет `npm ci` /
     `npm run build` — на слабой машине это самая долгая часть деплоя);
   - переносит исходники и готовые статики `frontend/build` на сервер по SSH;
   - собирает Docker-образы (nginx — тонкий, из готовых статиков) и разворачивает
     стек, применяет миграции Alembic и перезапускает сервисы.
2. Отдельный workflow **CI** уже есть: линт Python (ruff), **Python-тесты (pytest)** и JS-тесты/сборка фронтенда.
3. Серверный GigaChat-ключ: если в секретах GitHub заполнен `GIGACHAT_API_KEY`
   (Authorization Key из личного кабинета Сбера), все пользователи используют его,
   а раздел «AI-ассистент» в профиле скрывается.

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
| `GIGACHAT_API_KEY` | **Серверный GigaChat-ключ** (Authorization Key из личного кабинета Сбера; пустой = пользователи вводят свой ключ в профиле) |
| `BOT_TOKEN` | Токен Telegram-бота (пустой = бот выключен) |
| `DEPLOY_DOMAIN` | **Домен**, указывающий на IP сервера (например `app.example.com`). Если не задан — SSL не выпускается. |
| `CERTBOT_EMAIL` | Email для уведомлений Let's Encrypt (при выпуске сертификата) |

Рекомендуемые значения (сгенерировать):
```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"   # SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"   # AI_KEY_ENCRYPTION_KEY
python -c "import secrets; print(secrets.token_urlsafe(24))"   # POSTGRES_PASSWORD
```

## Требования GigaChat API

- Ключ `GIGACHAT_API_KEY` — это **Authorization Key** из проекта GigaChat API в
  личном кабинете Сбера (Studio → Настройки API → «Получить ключ»).
- Для доступа к `*.sberbank.ru` / `*.giga.chat` бэкенду нужны корневые
  сертификаты НУЦ Минцифры. Их нет в стандартном trust-store (certifi / Debian),
  поэтому TLS-запросы падают с `[SSL: CERTIFICATE_VERIFY_FAILED] ... self-signed
  certificate in certificate chain`.

### Как исправить (проверка TLS остаётся включённой)

**Для продакшена (Docker на сервере):**

1. **На сервере (один раз, от root):** положите корневой сертификат НУЦ Минцифры
   в `/etc/ssl/gigachat-ca.pem`:
   ```bash
   sudo openssl s_client -showcerts -connect ngw.devices.sberbank.ru:9443 \
     -servername ngw.devices.sberbank.ru -tls1_2 </dev/null 2>/dev/null \
     | sudo python3 -c "import sys,re; c=re.findall(r'-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----',sys.stdin.read(),re.S); open('/etc/ssl/gigachat-ca.pem','w').write(c[-1]+'\n')"
   ```
   Если `openssl s_client` не поднимает хендшейк (GOST TLS) — скачайте PEM
   корня «НУЦ Минцифры России» с официального распространителя доверенных
   корней (e-trust.gosuslugi.ru / сайт НУЦ) и сохраните как
   `/etc/ssl/gigachat-ca.pem`.

2. **GitHub Secrets:** создайте/проверьте секрет `GIGACHAT_CA_BUNDLE` со
   значением `/etc/ssl/certs/gigachat-ca.pem` (путь **внутри контейнера**,
   совпадает с правой частью монтирования в compose).

3. **Монтирование** уже настроено в `docker-compose.prod.yml` (сервис `backend`).
   Скрипт `deploy.sh` проверяет наличие файла на хосте (`/etc/ssl/gigachat-ca.pem`)
   и при его отсутствии fail-fast завершается с инструкцией.

4. **Проверка после деплоя:**
   ```bash
   docker compose exec backend printenv GIGACHAT_CA_BUNDLE  # → /etc/ssl/certs/gigachat-ca.pem
   docker compose exec backend python -c "import httpx; httpx.post('https://ngw.devices.sberbank.ru:9443/api/v2/oauth', verify='/etc/ssl/certs/gigachat-ca.pem', timeout=15)"
   ```
   Если команда не упала с SSL-ошибкой — всё готово.

**Для локальной разработки (не Docker):**

Задайте переменную окружения `GIGACHAT_CA_BUNDLE=<абсолютный путь к .pem>`.
Backend использует её только для GigaChat-запросов — общий trust-store не
меняется.

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

`certbot` на сервере выполняется через `sudo`, если деплой-пользователь не root
(скрипт определяет это автоматически — нужен sudo без запроса пароля).

Порт `443` должен быть открыт в файрволе/провайдере, а домен — указывать на
IP этого сервера (A-запись).

**Ручное продление** (если деплой долго не запускался):
```bash
sudo certbot renew
```

## Файлы деплоя

- `.github/workflows/deploy.yml` — workflow деплоя (push в `main` + ручной запуск).
  Собирает SPA на GitHub runner и передаёт готовые статики на сервер.
- `deploy/deploy.sh` — скрипт на сервере: пишет `.env`, выпускает/обновляет
  SSL-сертификат, собирает и поднимает стек.
- `docker-compose.prod.yml` — переопределения для продакшена (без `--reload`,
  без bind-mount, только nginx наружу; монтирует `/etc/letsencrypt`).
- `nginx/Dockerfile.prod` — тонкий nginx-образ из готовых статиков
  `frontend/build` (без node-стадии — сервер не собирает фронтенд).
- `nginx/nginx.conf` — HTTP→HTTPS: ACME-challenge на 80, сайт на 443.

**Почему так быстро?** Сборка Create React App (`npm run build`) — самая тяжёлая
часть деплоя и на машине 1 vCPU / 1 ГБ RAM занимает минуты (риск OOM). Она вынесена
на GitHub runner, а на сервер едет только готовый `frontend/build` (несколько МБ),
из которого nginx-образ собирается за секунды.
