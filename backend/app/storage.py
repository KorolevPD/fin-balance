import os
import shutil
import uuid
from pathlib import Path

ALLOWED_EXTENSION = ".csv"
ALLOWED_CONTENT_TYPES = {
    "text/csv",
    "text/plain",
    "application/csv",
    "application/vnd.ms-excel",
    "application/octet-stream",
}

UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "uploads")).resolve()


def validate_filename(filename: str) -> bool:
    return filename.lower().endswith(ALLOWED_EXTENSION)


def sanitize_filename(filename: str) -> str:
    return Path(filename).name


def save_upload(file_stream, original_filename: str) -> tuple[Path, str]:
    upload_dir = UPLOAD_DIR
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = sanitize_filename(original_filename or "")
    stored_name = f"{uuid.uuid4().hex}_{safe_name}" if safe_name else uuid.uuid4().hex
    target = upload_dir / stored_name
    with open(target, "wb") as f:
        shutil.copyfileobj(file_stream, f)
    return target, stored_name
