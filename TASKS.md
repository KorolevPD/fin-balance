# Журнал задач проекта

Последнее обновление: 2026-09-05T16:42:23Z

## Текущая задача

T-037

## Список задач

| ID | Задача | Детали реализации | Владелец | Статус | Прогресс | Последний файл выполнения | Точный следующий шаг |
|---|---|---|---|---|---:|---|---|
| T-001 | Инициализация Docker Compose | Создать docker-compose.yml с сервисами: backend (FastAPI), frontend (React), db (PostgreSQL), nginx, bot (aiogram). Базовые Dockerfile для каждого сервиса. | основной агент | DONE | 4/4 | docs/agent/tasks/T-001/20260904T150000Z_opencode_a02.md | — |
| T-002 | Базовый CI | Настроить GitHub Actions workflow: lint (ruff для Python) + тесты на push. eslint для JS отложен до появления React-фронтенда (T-011+). | основной агент | DONE | 2/2 | docs/agent/tasks/T-002/20260904T152007Z_main_a01.md | eslint для JS добавить в T-011+ |
| T-003 | Структура репозитория | Создать каталоги: backend/, frontend/, bot/, nginx/, docs/, tests/. Переместить существующие файлы. | основной агент | DONE | 3/3 | docs/agent/tasks/T-003/20260904T153100Z_opencode_a01.md | — |
| T-004 | Модели данных Backend | SQLAlchemy модели: User, Family, FamilyMember, Transaction, Category, UserCorrection. Миграции через Alembic. | backend-агент | DONE | 4/4 | docs/agent/tasks/T-004/20260904T161735Z_backend_a01.md | — |
| T-005 | Auth (JWT) | Регистрация, вход, JWT-токены. Эндпоинты: /register, /login, /me. | backend-агент | DONE | 3/3 | docs/agent/tasks/T-005/20260904T165040Z_opencode_a01.md | — |
| T-006 | CRUD семей | Эндпоинты: создание семьи, генерация invite_code, присоединение по коду, список участников. | backend-агент | DONE | 4/4 | docs/agent/tasks/T-006/20260904T171113Z_opencode_a01.md | — |
| T-007 | Загрузка CSV | Эндпоинт POST /upload: приём файла, валидация формата, сохранение во временное хранилище. | backend-агент | DONE | 3/3 | docs/agent/tasks/T-007/20260904T171611Z_backend_a01.md | — |
| T-008 | Парсер CSV | Универсальный парсер + поддержка 1-2 банков. Извлечение: дата, сумма, описание, тип операции. | backend-агент | DONE | 4/4 | docs/agent/tasks/T-008/20260904T175240Z_opencode_a01.md | — |
| T-009 | Правила категоризации | Словарь категорий + правила ключевых слов. Автоматическое присвоение категорий при парсинге. | backend-агент | DONE | 3/3 | docs/agent/tasks/T-009/20260905T054803Z_opencode_a01.md | — |
| T-010 | Сохранение транзакций | Создание записей Transaction в БД с привязкой к family_id и user_id. Обработка дублей. | backend-агент | DONE | 3/3 | docs/agent/tasks/T-010/20260905T064955Z_opencode_a01.md | — |
| T-011 | Авторизация Frontend | Страницы: логин, регистрация. Сохранение JWT в localStorage. Роутинг. | frontend-агент | DONE | 4/4 | docs/agent/tasks/T-011/20260904T180000Z_frontend_a01.md | — |
| T-012 | Управление семьёй | Страницы: создание семьи, ввод invite_code, список участников. | frontend-агент | DONE | 3/3 | docs/agent/tasks/T-012/20260904T174436Z_frontend_a01.md | — |
| T-013 | Загрузка файлов | Компонент загрузки CSV с drag-and-drop. Отображение прогресса и результата. | frontend-агент | DONE | 5/5 | docs/agent/tasks/T-013/20260905T091618Z_opencode_a02.md | — |
| T-014 | Дашборд | Страница: общая сумма, разбивка по категориям (таблица + график), список операций, топ-5 получателей. Зависит от бэкенд-API T-010 для данных. | frontend-агент | DONE | 4/4 | docs/agent/tasks/T-014/20260905T060000Z_frontend_a01.md | Ручная проверка данных после реализации T-010 |
| T-015 | Редактирование операций | Модальное окно из списка операций дашборда: изменение названия и категории. PATCH /families/{id}/transactions/{tid}. Категории — константа, зеркало правила T-009. | frontend-агент | DONE | 3/3 | docs/agent/tasks/T-015/20260905T080000Z_frontend_a01.md | Ручная проверка сохранения после реализации PATCH в T-010 |
| T-016 | Базовый Telegram-бот | aiogram: /start, привязка аккаунта, основные хэндлеры. | bot-агент | DONE | 3/3 | docs/agent/tasks/T-016/20260905T071416Z_bot_a01.md | Ожидание T-017 (загрузка через бота) |
| T-017 | Загрузка через бота | Приём документа (CSV) через бота, передача в backend API. | bot-агент | DONE | 3/3 | docs/agent/tasks/T-017/20260905T084726Z_bot_a01.md | Ожидание T-018 (сводка /summary) |
| T-018 | Сводка расходов | Команда /summary: запрос агрегатов из backend, форматирование ответа. | bot-агент | DONE | 3/3 | docs/agent/tasks/T-018/20260905T092214Z_bot_a01.md | Проверка diff, затем ветка + PR |
| T-019 | nginx reverse-proxy | Конфигурация nginx: статический фронт, проксирование /api и /bot. | infra-агент | DONE | 3/3 | docs/agent/tasks/T-019/20260905T071835Z_main_a01.md | T-020: интеграция всех сервисов и проверка `docker compose up` |
| T-020 | Сборка Docker Compose | Интеграция всех сервисов, проверка `docker compose up`. | infra-агент | DONE | 2/2 | docs/agent/tasks/T-020/20260905T075806Z_main_a01.md | T-021: сквозное ручное тестирование полного стека |
| T-021 | Сквозные сценарии | Ручное тестирование: регистрация → семья → загрузка → дашборд → бот. | тестировщик | TODO | 0/5 | — | — |
| T-022 | Исправление багов | Фикс критических ошибок, найденных при тестировании. | основной агент | TODO | 0/0 | — | — |
| T-023 | Hotfix: docker compose up | CRLF в entrypoint.sh (.gitattributes, eol=lf) + недостающий импорт bot в backend/main.py. Проверено: стек поднимается, API/SPA через nginx работают. | основной агент | DONE | 4/4 | docs/agent/tasks/T-023/20260905T082000Z_main_a01.md | PR #20 на ревью координатора |
| T-024 | Hotfix: дашборд и правка операций | Backend: GET /families/{id}/summary (агрегации) и PATCH /families/{id}/transactions/{tid} (название+категория, UserCorrection). Эндпоинты заложены в T-010/T-014/T-015, но не были реализованы. Проверено end-to-end через nginx. | основной агент | IN_PROGRESS | 4/4 | docs/agent/tasks/T-024/20260905T083000Z_main_a01.md | Проверка diff, затем ветка + PR |
| T-025 | Hotfix: кнопка «Загрузить» некликабельна | Frontend: исправлено условие disabled кнопки в Upload.js (progress === null → progress !== null). После выбора CSV кнопка активна, на время загрузки блокируется. Проверено: npm run check — Compiled successfully. | основной агент | DONE | 2/2 | docs/agent/tasks/T-024/20260905T094252Z_main_a02.md | Проверка diff, затем ветка + PR |
| T-031 | Форма просмотра/редактирования профиля и фото | Backend: колонка User.avatar + миграция 004, PATCH /auth/me (имя), POST /auth/me/avatar (валидация типа/размера), GET /auth/me/avatar/{stored_name}. Frontend: страница Profile (имя + фото, расширяемая по полям), роут /profile, ссылка и аватар в шапке, AuthContext.updateUser. Проверено: pytest 85 passed (11 новых), ruff clean, npm run check — Compiled successfully. | основной агент | DONE | 6/6 | docs/agent/tasks/T-031/20260905T122753Z_opencode_a01.md | Проверка diff, затем ветка + PR |
| T-032 | Кликабельное имя пользователя в шапке | Frontend: из nav убран пункт «Профиль», имя пользователя в .user-info стало ссылкой на /profile (класс user-info-name), мобильное скрытие обновлено. Проверено: npm run check — Compiled successfully. | основной агент | DONE | 3/3 | docs/agent/tasks/T-032/20260905T125912Z_opencode_a01.md | Проверка diff, затем ветка + PR |
| T-033 | Загрузка операций из PDF | Backend: парсер PDF-выписки Сбербанка (examples/sber.pdf) через pypdf + диспетч парсера по расширению в POST /families/{id}/transactions/import. Frontend: вкладка «Загрузить» принимает CSV и PDF, импорт в семью, отладочный список операций. Проверено: pytest 90 passed (5 новых), ruff clean, npm run check — Compiled successfully. | основной агент | DONE | 3/3 | docs/agent/tasks/T-033/20260905T142308Z_main_a01.md | Проверка diff, затем ветка + PR |
| T-034 | Аналитика «доход/расход» и веб-импорт выписки | Backend: колонка Transaction.type (income/expense, default expense) + миграция 005, save_transactions пишет тип, TransactionOut отдаёт type, аналитика считает total_amount/by_category/top_payees/monthly/family_members только по расходам. Frontend: Upload.js выбирает семью (/families/my) и импортирует через POST /families/{id}/transactions/import, показывает parsed/created/duplicates. Доп. фикс: загрузка файла без семьи — форма видна всегда, при отсутствии семей автосоздаётся семья «Мои финансы». Проверено: pytest 89 passed (новые тесты: тип в сервисе/роутере/аналитике), ruff clean по затронутым файлам, npm run check — Compiled successfully. | основной агент | DONE | 5/5 | docs/agent/tasks/T-034/20260905T153500Z_opencode_a02.md | Проверка diff, затем ветка + PR |
| T-035 | Реальный дашборд по ссылке «Дашборд» | Frontend: DemoDashboard.js при переходе на /dashboard проверяет /families/my и summary каждой семьи; если найдены операции (total_amount>0 или by_category/uploaded_files не пусты) — редирект на реальный дашборд /family/{id}/dashboard, иначе — «Примерный дашборд». Проверено: npm run check — Compiled successfully. | основной агент | DONE | 3/3 | docs/agent/tasks/T-035/20260905T150457Z_opencode_a01.md | Проверка diff, затем ветка + PR |
| T-036 | Знак и цвет сумм операций | Frontend: в списках операций (Dashboard, Upload, DemoDashboard) суммы показываются со знаком: «+» для пополнений (`type == income`) и «−» для вычетов (`type == expense`). Пополнения — зелёным (`.amount-income`, #16a34a), вычеты — красным (`.amount-expense`, #dc2626). Основано на поле `type`, которое backend уже отдаёт в `TransactionOut`. Проверено: npm run check — Compiled successfully. | основной агент | DONE | 3/3 | docs/agent/tasks/T-036/20260905T160920Z_opencode_a01.md | PR #38 уже влит в main |
| T-037 | Сортировка операций по категории на дашборде | Frontend: на дашборде семьи (Dashboard.js) операции по умолчанию идут «сначала новые» (дата по убыванию). Клик по заголовку «Категория» сортирует список по категории (повторный клик — обратное направление), заголовки «Дата» и «Категория» кликабельны, справа всегда показан треугольник ▼ (активная колонка — ▲/▼ цветом) и aria-sort. Проверено: npm run check — Compiled successfully, ручная проверка сортировки через API + Node на реальных данных. | основной агент | DONE | 4/4 | docs/agent/tasks/T-037/20260905T164223Z_opencode_a02.md | Проверка diff, затем ветка + PR |

Допустимые статусы: `TODO`, `IN_PROGRESS`, `BLOCKED`, `DONE`.

## Текущий блокер

Нет.

## Правила обновления

- `TASKS.md` конкретизирует этапы из `PLAN.md`, но не дублирует весь стратегический план.
- Во время выполнения агент пишет в собственный timestamp-файл.
- Центральный файл обновляет один координатор после проверки `git diff` и тестов.
- Прогресс указывается как `выполненные критерии / всего`, например `2/4`.
- Поле `Последний файл выполнения` указывает на самый свежий проверенный файл в `docs/agent/tasks/<TASK-ID>/`.
