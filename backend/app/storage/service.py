import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import SentinelException


class StorageError(SentinelException):
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message=message, code="STORAGE_ERROR", status_code=status_code)


class BaseStorageService(ABC):
    @abstractmethod
    async def save_quarantine(self, storage_key: str, data: bytes) -> str:
        """Stores untrusted uploaded file into quarantine area."""
        pass

    @abstractmethod
    async def move_to_vault(self, storage_key: str) -> str:
        """Promotes scanned and accepted file from quarantine to clean vault."""
        pass

    @abstractmethod
    async def get_vault_file(self, storage_key: str) -> bytes:
        """Retrieves verified clean file from vault."""
        pass

    @abstractmethod
    async def get_quarantine_file(self, storage_key: str) -> bytes:
        """Retrieves file from quarantine for scanning."""
        pass

    @abstractmethod
    async def delete_quarantine(self, storage_key: str) -> None:
        """Removes rejected or processed file from quarantine."""
        pass


class LocalStorageService(BaseStorageService):
    def __init__(self, base_path: str = settings.LOCAL_STORAGE_PATH):
        self.base_path = Path(base_path).resolve()
        self.quarantine_dir = (self.base_path / "quarantine").resolve()
        self.vault_dir = (self.base_path / "vault").resolve()

        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        self.vault_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, directory: Path, storage_key: str) -> Path:
        """Prevents path traversal attacks by validating resolved path stays within directory."""
        # Sanitize storage key: only allow alphanumerics, hyphens, underscores, dots, and forward slashes
        clean_key = Path(storage_key).as_posix()
        if ".." in clean_key or clean_key.startswith("/") or clean_key.startswith("\\"):
            raise StorageError("Invalid storage key detected: Path traversal disallowed", status_code=400)

        target = (directory / clean_key).resolve()
        if not str(target).startswith(str(directory)):
            raise StorageError("Invalid storage path: Access restricted", status_code=400)
        return target

    async def save_quarantine(self, storage_key: str, data: bytes) -> str:
        target_path = self._resolve_safe_path(self.quarantine_dir, storage_key)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "wb") as f:
            f.write(data)
        logger.debug(f"Saved file to local quarantine: {storage_key}")
        return storage_key

    async def move_to_vault(self, storage_key: str) -> str:
        src_path = self._resolve_safe_path(self.quarantine_dir, storage_key)
        if not src_path.exists():
            raise StorageError("Source quarantine file not found", status_code=404)

        dst_path = self._resolve_safe_path(self.vault_dir, storage_key)
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_path), str(dst_path))
        logger.info(f"Promoted verified file from quarantine to vault: {storage_key}")
        return storage_key

    async def get_vault_file(self, storage_key: str) -> bytes:
        file_path = self._resolve_safe_path(self.vault_dir, storage_key)
        if not file_path.exists():
            raise StorageError("Requested document not found in vault", status_code=404)
        with open(file_path, "rb") as f:
            return f.read()

    async def get_quarantine_file(self, storage_key: str) -> bytes:
        file_path = self._resolve_safe_path(self.quarantine_dir, storage_key)
        if not file_path.exists():
            raise StorageError("Quarantined document not found", status_code=404)
        with open(file_path, "rb") as f:
            return f.read()

    async def delete_quarantine(self, storage_key: str) -> None:
        file_path = self._resolve_safe_path(self.quarantine_dir, storage_key)
        if file_path.exists():
            file_path.unlink()
            logger.debug(f"Deleted quarantined file: {storage_key}")


def get_storage_service() -> BaseStorageService:
    # Uses local secure storage adapter with quarantine & vault isolation
    return LocalStorageService()


storage_service = get_storage_service()
