import hashlib
from typing import Tuple
from pathlib import Path
from pydantic import BaseModel
from app.core.config import settings
from app.core.exceptions import SentinelException


class FileValidationError(SentinelException):
    def __init__(self, message: str, details: dict = None):
        super().__init__(
            message=message,
            code="FILE_VALIDATION_ERROR",
            status_code=400,
            details=details,
        )


class ValidatedFileMetadata(BaseModel):
    detected_mime: str
    sha256_hash: str
    file_size: int
    original_filename: str


MAGIC_SIGNATURES = [
    (b"%PDF-", "application/pdf"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
]


def detect_file_signature(data: bytes) -> str:
    """Inspects raw byte headers to identify actual file MIME type."""
    if not data:
        raise FileValidationError("Uploaded file is empty (0 bytes)")

    for magic, mime in MAGIC_SIGNATURES:
        if data.startswith(magic):
            return mime

    raise FileValidationError(
        "File signature verification failed: File content does not match accepted regulatory formats (PDF, JPEG, PNG)"
    )


def validate_uploaded_file(
    filename: str,
    declared_content_type: str,
    data: bytes,
) -> ValidatedFileMetadata:
    """
    Performs comprehensive security and integrity validation on untrusted uploaded bytes:
    1. Size constraint check
    2. Filename extension validation
    3. Magic byte signature verification
    4. Signature vs declared MIME alignment
    5. SHA-256 digest computation
    """
    # 1. Size Check
    file_size = len(data)
    if file_size > settings.MAX_UPLOAD_SIZE_BYTES:
        raise FileValidationError(
            f"File exceeds statutory upload limit of {settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MB",
            {"size_bytes": file_size, "max_allowed": settings.MAX_UPLOAD_SIZE_BYTES},
        )
    if file_size == 0:
        raise FileValidationError("Uploaded file is empty")

    # 2. Extension Check
    ext = Path(filename).suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise FileValidationError(
            f"File extension '{ext}' is not permitted. Permitted extensions: {settings.ALLOWED_EXTENSIONS}",
            {"extension": ext, "allowed": settings.ALLOWED_EXTENSIONS},
        )

    # 3. Magic byte signature inspection
    detected_mime = detect_file_signature(data)

    # 4. Declared vs Detected MIME sanity check
    # Normalize image/jpg to image/jpeg
    norm_declared = "image/jpeg" if declared_content_type in ("image/jpg", "image/pjpeg") else declared_content_type
    if norm_declared not in settings.ALLOWED_MIME_TYPES:
        raise FileValidationError(
            f"Declared MIME type '{declared_content_type}' is not supported for regulatory scrutiny.",
            {"declared_mime": declared_content_type},
        )

    if detected_mime != norm_declared:
        raise FileValidationError(
            f"MIME type mismatch: Declared '{declared_content_type}' but byte signature detected '{detected_mime}'. Upload rejected for tampering prevention.",
            {"declared": declared_content_type, "detected": detected_mime},
        )

    # 5. SHA-256 Digest
    sha256_hash = hashlib.sha256(data).hexdigest()

    return ValidatedFileMetadata(
        detected_mime=detected_mime,
        sha256_hash=sha256_hash,
        file_size=file_size,
        original_filename=Path(filename).name,  # Clean path traversal in name
    )
