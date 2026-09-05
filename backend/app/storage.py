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

AVATAR_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
AVATAR_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}
MAX_AVATAR_SIZE = 5 * 1024 * 1024

UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "uploads")).resolve()
AVATAR_DIR_NAME = "avatars"


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


def avatar_dir() -> Path:
    directory = UPLOAD_DIR / AVATAR_DIR_NAME
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def avatar_path(stored_name: str) -> Path:
    return (UPLOAD_DIR / AVATAR_DIR_NAME / sanitize_filename(stored_name)).resolve()


def save_avatar(file_stream, original_filename: str) -> str:
    directory = avatar_dir()
    ext = Path(original_filename or "").suffix.lower()
    if ext not in AVATAR_ALLOWED_EXTENSIONS:
        ext = ""
    stored_name = f"{uuid.uuid4().hex}{ext}"
    target = directory / stored_name
    with open(target, "wb") as f:
        shutil.copyfileobj(file_stream, f)
    return stored_name


def delete_avatar(stored_name: str) -> None:
    path = avatar_path(stored_name)
    if path.is_file():
        path.unlink()
