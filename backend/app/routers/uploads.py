from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.storage import (
    ALLOWED_CONTENT_TYPES,
    save_upload,
    validate_filename,
)
from app.schemas import UploadResponse

router = APIRouter(tags=["upload"])


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_csv(file: UploadFile = File(...)):
    filename = file.filename or ""
    if not validate_filename(filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Допускаются только CSV-файлы с расширением .csv",
        )

    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Недопустимый MIME-тип файла: {content_type or 'не указан'}",
        )

    path, stored_name = save_upload(file.file, filename)
    return UploadResponse(
        filename=filename,
        stored_name=stored_name,
        size_bytes=path.stat().st_size,
        content_type=content_type,
    )
