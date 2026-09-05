#!/bin/sh
set -e

echo "FinBalance backend: ожидание готовности базы данных..."
python - <<'PY'
import os
import time

from sqlalchemy import create_engine, text

url = os.environ.get("DATABASE_URL", "")
engine = create_engine(url)
for attempt in range(30):
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("FinBalance backend: база данных готова")
        break
    except Exception as exc:  # noqa: BLE001
        print(
            f"FinBalance backend: база недоступна "
            f"(попытка {attempt + 1}/30): {exc.__class__.__name__}"
        )
        time.sleep(2)
else:
    raise SystemExit(
        "FinBalance backend: база данных недоступна после 60 секунд"
    )
PY

echo "FinBalance backend: применение миграций Alembic..."
alembic upgrade head

exec "$@"