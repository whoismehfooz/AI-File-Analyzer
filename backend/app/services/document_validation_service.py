from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import (
    DocumentValidationError,
    DocumentTooLargeError
)

class DocumentValidationService:

    @staticmethod
    def allowed_extensions() -> set[str]:
        return {
            extension.strip().lower()
            for extension in settings.ALLOWED_DOCUMENT_EXTENSIONS.split(",")
            if extension.strip()
        }

    @staticmethod
    def _get_filename_extension(filename: str) -> str:
        basename = filename.replace("\\", "/").rsplit("/", 1)[-1]

        if not basename or basename in {".", ".."}:
            raise DocumentValidationError(
                "A valid filename is required."
            )

        if "." not in basename or basename.endswith("."):
            return ""

        return f".{basename.rsplit('.', 1)[-1].lower()}"

    @classmethod
    async def validate_upload(cls, file: UploadFile) -> None:
        filename = file.filename

        if not filename or not filename.strip():
            raise DocumentValidationError(
                "A filename is required."
            )

        if any(ord(character) < 32 or ord(character) == 127 for character in filename):
            raise DocumentValidationError(
                "The filename contains invalid characters."
            )

        extension = cls._get_filename_extension(filename)

        allowed_extensions = cls.allowed_extensions()

        if extension not in allowed_extensions:
            allowed_formats = ", ".join(
                sorted(
                    extension.removeprefix(".").upper()
                    for extension in allowed_extensions
                )
            )

            if not allowed_formats:
                allowed_formats = "none configured"

            raise DocumentValidationError(
                f"Unsupported file type. "
                f"Allowed formats: {allowed_formats}."
            )

        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        total_bytes = 0

        try:
            while True:
                chunk = await file.read(1024 * 1024)

                if not chunk:
                    break

                total_bytes += len(chunk)

                if total_bytes > max_bytes:
                    raise DocumentTooLargeError(
                        f"File exceeds the "
                        f"{settings.MAX_UPLOAD_SIZE_MB} MB limit."
                    )

            if total_bytes == 0:
                raise DocumentValidationError("The uploaded file is empty.")

        finally:
            await file.seek(0)
