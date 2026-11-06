
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    APP_NAME: str = "AI Document Analyzer"
    APP_ENV: str = "development"
    DEBUG: bool = False

    MAX_UPLOAD_SIZE_MB: int = Field(default=15, gt=0)
    MAX_EXTRACTED_CHARACTERS: int = Field(default=6_000_000, gt=0)

    MAX_PDF_PAGES: int = Field(default=250, gt=0)

    MAX_DOCX_UNCOMPRESSED_MB: int = Field(default=100, gt=0)
    MAX_DOCX_COMPRESSION_RATIO: int = Field(default=100, gt=0)
    MAX_DOCX_ARCHIVE_FILES: int = Field(default=10_000, gt=0)

    MAX_CSV_ROWS: int = Field(default=50_000, gt=0)
    MAX_CSV_COLUMNS: int = Field(default=200, gt=0)

    MAX_EXCEL_SHEETS: int = Field(default=20, gt=0)
    MAX_EXCEL_ROWS_PER_SHEET: int = Field(default=50_000, gt=0)
    MAX_EXCEL_COLUMNS_PER_SHEET: int = Field(default=200, gt=0)
    MAX_EXCEL_TOTAL_CELLS: int = Field(default=1_000_000, gt=0)

    ALLOWED_DOCUMENT_EXTENSIONS: str = (
        ".txt,.pdf,.docx,.csv,.xls,.xlsx"
    )

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
