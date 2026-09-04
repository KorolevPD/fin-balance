from pydantic import BaseModel


class UploadResponse(BaseModel):
    filename: str
    stored_name: str
    size_bytes: int
    content_type: str
