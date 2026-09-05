from fastapi import APIRouter

router = APIRouter(prefix="/demo", tags=["demo"])


@router.get("/dashboard", summary="Примерный дашборд с моковыми данными")
def demo_dashboard():
    return {
        "family_members": [
            {"name": "Анна Иванова", "total_expenses": 45230.50},
            {"name": "Пётр Иванов", "total_expenses": 38710.25},
            {"name": "Мария Иванова", "total_expenses": 12450.00},
        ],
        "categories": [
            {"category": "Продукты", "amount": 32500.00},
            {"category": "Транспорт", "amount": 18900.50},
            {"category": "Жильё", "amount": 15000.00},
            {"category": "Развлечения", "amount": 12340.25},
            {"category": "Одежда", "amount": 9870.00},
            {"category": "Здоровье", "amount": 7650.00},
            {"category": "Прочее", "amount": 5130.00},
        ],
        "uploaded_files": [
            {
                "filename": "сбербанк_январь_2026.csv",
                "period_start": "2026-01-03",
                "period_end": "2026-01-31",
                "operations_count": 142,
            },
            {
                "filename": "сбербанк_февраль_2026.csv",
                "period_start": "2026-02-01",
                "period_end": "2026-02-28",
                "operations_count": 128,
            },
            {
                "filename": "тinkoff_январь.csv",
                "period_start": "2026-01-05",
                "period_end": "2026-01-29",
                "operations_count": 87,
            },
        ],
    }
