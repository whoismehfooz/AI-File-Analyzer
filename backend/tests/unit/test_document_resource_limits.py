import csv
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import openpyxl
import pytest

from app.core.config import settings
from app.exceptions.handlers import register_exception_handlers
from app.core.exceptions import DocumentExtractionError
from app.services.document_extraction_service import (
    DocumentExtractionService,
)


def test_pdf_page_limit_is_enforced(monkeypatch):
    class FakePDF:
        is_encrypted = False

        def __len__(self):
            return settings.MAX_PDF_PAGES + 1

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    monkeypatch.setattr(
        "app.services.document_extraction_service.pymupdf.open",
        lambda **kwargs: FakePDF(),
    )

    with pytest.raises(
        DocumentExtractionError,
        match="maximum supported page count",
    ):
        DocumentExtractionService._extract_pdf(b"fake-pdf")


def test_docx_archive_rejects_missing_required_files():
    buffer = BytesIO()

    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("random.txt", "not a docx")

    with pytest.raises(
        DocumentExtractionError,
        match="missing required document data",
    ):
        DocumentExtractionService._validate_docx_archive(
            buffer.getvalue()
        )


def test_docx_archive_rejects_too_many_entries(monkeypatch):
    monkeypatch.setattr(
        settings,
        "MAX_DOCX_ARCHIVE_FILES",
        2,
    )

    buffer = BytesIO()

    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "content")
        archive.writestr("word/document.xml", "document")
        archive.writestr("extra.xml", "extra")

    with pytest.raises(
        DocumentExtractionError,
        match="too many archive entries",
    ):
        DocumentExtractionService._validate_docx_archive(
            buffer.getvalue()
        )

def test_docx_uncompressed_size_limit_is_enforced(monkeypatch):
    monkeypatch.setattr(
        settings,
        "MAX_DOCX_UNCOMPRESSED_MB",
        1,
    )

    buffer = BytesIO()

    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "content")
        archive.writestr("word/document.xml", "A" * (2 * 1024 * 1024))

    with pytest.raises(
        DocumentExtractionError,
        match="uncompressed archive size",
    ):
        DocumentExtractionService._validate_docx_archive(
            buffer.getvalue()
        )


def test_docx_compression_ratio_limit_is_enforced(monkeypatch):
    monkeypatch.setattr(
        settings,
        "MAX_DOCX_COMPRESSION_RATIO",
        2,
    )

    buffer = BytesIO()

    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "content")
        archive.writestr("word/document.xml", "A" * 100_000)

    with pytest.raises(
        DocumentExtractionError,
        match="compression ratio",
    ):
        DocumentExtractionService._validate_docx_archive(
            buffer.getvalue()
        )



def test_csv_column_limit_is_enforced(monkeypatch):
    monkeypatch.setattr(settings, "MAX_CSV_COLUMNS", 2)

    content = b"name,age,city\nAlice,20,Delhi\n"

    with pytest.raises(
        DocumentExtractionError,
        match="maximum supported column count",
    ):
        DocumentExtractionService._extract_csv(content)


def test_csv_row_limit_is_enforced(monkeypatch):
    monkeypatch.setattr(settings, "MAX_CSV_ROWS", 1)

    content = b"name\nAlice\nBob\n"

    with pytest.raises(
        DocumentExtractionError,
        match="maximum supported row count",
    ):
        DocumentExtractionService._extract_csv(content)


def test_excel_sheet_limit_is_enforced(monkeypatch):
    monkeypatch.setattr(settings, "MAX_EXCEL_SHEETS", 1)

    workbook = openpyxl.Workbook()
    workbook.create_sheet("Second")

    buffer = BytesIO()
    workbook.save(buffer)
    workbook.close()

    with pytest.raises(
        DocumentExtractionError,
        match="worksheet count",
    ):
        DocumentExtractionService._validate_excel_limits(
            buffer.getvalue(),
            "xlsx",
        )


def test_excel_row_limit_is_enforced(monkeypatch):
    monkeypatch.setattr(
        settings,
        "MAX_EXCEL_ROWS_PER_SHEET",
        1,
    )

    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.append(["name"])
    worksheet.append(["Alice"])
    worksheet.append(["Bob"])

    buffer = BytesIO()
    workbook.save(buffer)
    workbook.close()

    with pytest.raises(
        DocumentExtractionError,
        match="maximum supported row count",
    ):
        DocumentExtractionService._validate_excel_limits(
            buffer.getvalue(),
            "xlsx",
        )


def test_excel_column_limit_is_enforced(monkeypatch):
    monkeypatch.setattr(
        settings,
        "MAX_EXCEL_COLUMNS_PER_SHEET",
        1,
    )

    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.append(["name", "age"])

    buffer = BytesIO()
    workbook.save(buffer)
    workbook.close()

    with pytest.raises(
        DocumentExtractionError,
        match="maximum supported column count",
    ):
        DocumentExtractionService._validate_excel_limits(
            buffer.getvalue(),
            "xlsx",
        )


def test_excel_total_cell_limit_is_enforced(monkeypatch):
    monkeypatch.setattr(
        settings,
        "MAX_EXCEL_TOTAL_CELLS",
        2,
    )

    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.append(["name", "age"])
    worksheet.append(["Alice", 20])

    buffer = BytesIO()
    workbook.save(buffer)
    workbook.close()

    with pytest.raises(
        DocumentExtractionError,
        match="maximum supported total cell count",
    ):
        DocumentExtractionService._validate_excel_limits(
            buffer.getvalue(),
            "xlsx",
        )


def test_extracted_character_limit_is_enforced(monkeypatch):
    monkeypatch.setattr(
        settings,
        "MAX_EXTRACTED_CHARACTERS",
        5,
    )

    with pytest.raises(
        DocumentExtractionError,
        match="maximum extracted text limit",
    ):
        DocumentExtractionService.extract_document(
            filename="long.txt",
            content=b"123456",
        )
