import io

from fastapi.testclient import TestClient

from main import app
from app.storage import UPLOAD_DIR, validate_filename

client = TestClient(app)


def test_эндпоинт_upload_принимает_csv_файл():
    content = b"date,amount\n2026-09-01,100.0\n"
    files = {"file": ("statement.csv", io.BytesIO(content), "text/csv")}
    response = client.post("/upload", files=files)

    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "statement.csv"
    assert body["size_bytes"] == len(content)
    assert body["content_type"] == "text/csv"
    assert (UPLOAD_DIR / body["stored_name"]).exists()


def test_upload_отклоняет_файл_не_csv():
    file_bytes = io.BytesIO(b"data")
    files = {"file": ("statement.xlsx", file_bytes, "application/octet-stream")}
    response = client.post("/upload", files=files)

    assert response.status_code == 400
    assert "csv" in response.json()["detail"].lower()


def test_upload_отклоняет_неподдерживаемый_mime():
    files = {"file": ("statement.csv", io.BytesIO(b"data"), "image/png")}
    response = client.post("/upload", files=files)

    assert response.status_code == 400
    assert "mime" in response.json()["detail"].lower()


def test_новая_загрузка_не_перезаписывает_предыдущий_файл():
    content = b"date,amount\n2026-09-01,100.0\n"
    first = client.post(
        "/upload", files={"file": ("s.csv", io.BytesIO(content), "text/csv")}
    )
    second = client.post(
        "/upload", files={"file": ("s.csv", io.BytesIO(content), "text/csv")}
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["stored_name"] != second.json()["stored_name"]


def test_validate_filename_true_only_for_csv():
    assert validate_filename("statement.csv")
    assert validate_filename("STATEMENT.CSV")
    assert not validate_filename("statement.txt")
    assert not validate_filename("statement.csv.exe")
    assert not validate_filename("")
