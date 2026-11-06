import csv
import zipfile
import openpyxl
import xlrd
from io import BytesIO, StringIO
from pathlib import PurePath
from typing import Any, Callable

import pymupdf
import pandas as pd
from docx import Document as DocxDocument
from pydantic import ValidationError

from app.core.config import settings

from app.schemas.extracted_document import (
    DocumentSection,
    ExtractedDocument,
)

from app.core.exceptions import DocumentExtractionError

class DocumentExtractionService:
    SUPPORTED_EXTENSIONS = frozenset(
        {"txt", "pdf", "docx", "csv", "xls", "xlsx"}
    )

    @staticmethod
    def _check_extracted_character_limit(
        sections: list[DocumentSection],
    ) -> None:
        total_characters = sum(
            len(section.content)
            for section in sections
        )

        if total_characters > settings.MAX_EXTRACTED_CHARACTERS:
            raise DocumentExtractionError(
                "The document exceeds the maximum extracted text limit."
            )

    @staticmethod
    def _check_section_count(
        sections: list[DocumentSection],
        maximum: int,
        document_type: str,
    ) -> None:
        if len(sections) > maximum:
            raise DocumentExtractionError(
                f"The {document_type} document exceeds the "
                "maximum supported section count."
            )

    @staticmethod
    def _validate_docx_archive(content: bytes) -> None:
        max_uncompressed_bytes = (
            settings.MAX_DOCX_UNCOMPRESSED_MB * 1024 * 1024
        )

        try:
            with zipfile.ZipFile(BytesIO(content)) as archive:
                entries = archive.infolist()

                if len(entries) > settings.MAX_DOCX_ARCHIVE_FILES:
                    raise DocumentExtractionError(
                        "The DOCX file contains too many archive entries."
                    )

                required_files = {
                    "[Content_Types].xml",
                    "word/document.xml",
                }

                archive_names = {
                    entry.filename for entry in entries
                }

                if not required_files.issubset(archive_names):
                    raise DocumentExtractionError(
                        "The DOCX file is missing required document data."
                    )

                total_uncompressed = sum(
                    entry.file_size for entry in entries
                )

                if total_uncompressed > max_uncompressed_bytes:
                    raise DocumentExtractionError(
                        "The DOCX file exceeds the maximum "
                        "uncompressed archive size."
                    )

                total_compressed = sum(
                    entry.compress_size for entry in entries
                )

                if total_uncompressed > 0:
                    compression_ratio = (
                        total_uncompressed
                        / max(total_compressed, 1)
                    )

                    if (
                        compression_ratio
                        > settings.MAX_DOCX_COMPRESSION_RATIO
                    ):
                        raise DocumentExtractionError(
                            "The DOCX file has an unsafe "
                            "compression ratio."
                        )

        except DocumentExtractionError:
            raise
        except (
            zipfile.BadZipFile,
            OSError,
            RuntimeError,
        ) as exc:
            raise DocumentExtractionError(
                "The DOCX file is invalid or could not be read."
            ) from exc

    @staticmethod
    def _validate_excel_limits(
        content: bytes,
        extension: str,
    ) -> None:
        total_cells = 0

        try:
            if extension == "xlsx":
                workbook = openpyxl.load_workbook(
                    BytesIO(content),
                    read_only=True,
                    data_only=True,
                )

                try:
                    worksheets = workbook.worksheets

                    if len(worksheets) > settings.MAX_EXCEL_SHEETS:
                        raise DocumentExtractionError(
                            "The Excel file exceeds the maximum "
                            f"worksheet count of {settings.MAX_EXCEL_SHEETS}."
                        )

                    for worksheet in worksheets:
                        row_count = worksheet.max_row or 0
                        column_count = worksheet.max_column or 0

                        if row_count > settings.MAX_EXCEL_ROWS_PER_SHEET:
                            raise DocumentExtractionError(
                                "An Excel worksheet exceeds the "
                                "maximum supported row count."
                            )

                        if (
                            column_count
                            > settings.MAX_EXCEL_COLUMNS_PER_SHEET
                        ):
                            raise DocumentExtractionError(
                                "An Excel worksheet exceeds the "
                                "maximum supported column count."
                            )

                        total_cells += row_count * column_count

                        if total_cells > settings.MAX_EXCEL_TOTAL_CELLS:
                            raise DocumentExtractionError(
                                "The Excel file exceeds the maximum "
                                "supported total cell count."
                            )

                finally:
                    workbook.close()

            elif extension == "xls":
                workbook = xlrd.open_workbook(
                    file_contents=content,
                    on_demand=True,
                )

                try:
                    if (
                        workbook.nsheets
                        > settings.MAX_EXCEL_SHEETS
                    ):
                        raise DocumentExtractionError(
                            "The Excel file exceeds the maximum "
                            f"worksheet count of {settings.MAX_EXCEL_SHEETS}."
                        )

                    for sheet_index in range(workbook.nsheets):
                        worksheet = workbook.sheet_by_index(sheet_index)

                        if (
                            worksheet.nrows
                            > settings.MAX_EXCEL_ROWS_PER_SHEET
                        ):
                            raise DocumentExtractionError(
                                "An Excel worksheet exceeds the "
                                "maximum supported row count."
                            )

                        if (
                            worksheet.ncols
                            > settings.MAX_EXCEL_COLUMNS_PER_SHEET
                        ):
                            raise DocumentExtractionError(
                                "An Excel worksheet exceeds the "
                                "maximum supported column count."
                            )

                        total_cells += (
                            worksheet.nrows * worksheet.ncols
                        )

                        if (
                            total_cells
                            > settings.MAX_EXCEL_TOTAL_CELLS
                        ):
                            raise DocumentExtractionError(
                                "The Excel file exceeds the maximum "
                                "supported total cell count."
                            )

                finally:
                    workbook.release_resources()

            else:
                raise DocumentExtractionError(
                    "Unsupported Excel format."
                )

        except DocumentExtractionError:
            raise
        except Exception as exc:
            raise DocumentExtractionError(
                "The Excel file is invalid or could not be inspected."
            ) from exc

    @classmethod
    def extract_document(
        cls,
        filename: str,
        content: bytes,
    ) -> ExtractedDocument:
        if not filename or not filename.strip():
            raise DocumentExtractionError(
                "A filename is required."
            )

        if not content:
            raise DocumentExtractionError(
                "The uploaded file is empty."
            )

        safe_filename = PurePath(
            filename.replace("\\", "/")
        ).name

        if not safe_filename or safe_filename in {".", ".."}:
            raise DocumentExtractionError(
                "A valid filename is required."
            )

        extension = (
            safe_filename.rsplit(".", 1)[-1].lower()
            if "." in safe_filename
            else ""
        )

        if extension not in cls.SUPPORTED_EXTENSIONS:
            raise DocumentExtractionError(
                "Unsupported file type. Allowed formats: "
                "TXT, PDF, DOCX, CSV, XLS, XLSX."
            )

        extractors: dict[
            str,
            Callable[[bytes], tuple[list[DocumentSection], dict[str, Any]]],
        ] = {
            "txt": cls._extract_txt,
            "pdf": cls._extract_pdf,
            "docx": cls._extract_docx,
            "csv": cls._extract_csv,
            "xls": lambda raw: cls._extract_excel(raw, "xls"),
            "xlsx": lambda raw: cls._extract_excel(raw, "xlsx"),
        }

        sections, source_metadata = extractors[extension](content)

        cls._check_extracted_character_limit(sections)

        normalized_sections = []
        for section in sections:
            normalized_text = cls._normalize_text(section.content)

            if normalized_text:
                normalized_sections.append(
                    DocumentSection(
                        content=normalized_text,
                        metadata=section.metadata,
                    )
                )

        if not normalized_sections:
            raise DocumentExtractionError(
                "No readable text was found in the uploaded document."
            )

        normalized_content = "\n\n".join(
            section.content for section in normalized_sections
        )

        metadata: dict[str, Any] = {
            **source_metadata,
            "character_count": len(normalized_content),
            "section_count": len(normalized_sections),
        }

        try:
            return ExtractedDocument(
                filename=safe_filename,
                file_type=extension,
                content=normalized_content,
                metadata=metadata,
                sections=normalized_sections,
            )
        except ValidationError as exc:
            raise DocumentExtractionError(
                "The extracted document could not be represented."
            ) from exc

    @staticmethod
    def _extract_txt(
        content: bytes,
    ) -> tuple[list[DocumentSection], dict[str, Any]]:
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise DocumentExtractionError(
                "The TXT file must use valid UTF-8 text encoding."
            ) from exc

        return (
            [DocumentSection(content=text)],
            {"encoding": "utf-8"},
        )

    @staticmethod
    def _extract_pdf(
        content: bytes,
    ) -> tuple[list[DocumentSection], dict[str, Any]]:
        try:
            with pymupdf.open(stream=content, filetype="pdf") as pdf:
                if pdf.is_encrypted:
                    raise DocumentExtractionError(
                        "Password-protected PDF files are not supported."
                    )

                page_count = len(pdf)

                if page_count > settings.MAX_PDF_PAGES:
                    raise DocumentExtractionError(
                        f"The PDF exceeds the maximum supported "
                        f"page count of {settings.MAX_PDF_PAGES}."
                    )
                sections = [
                    DocumentSection(
                        content=page.get_text(),
                        metadata={"page_number": page_number},
                    )
                    for page_number, page in enumerate(pdf, start=1)
                ]

        except DocumentExtractionError:
            raise
        except (pymupdf.FileDataError, RuntimeError, ValueError) as exc:
            raise DocumentExtractionError(
                "The PDF file is invalid or could not be read."
            ) from exc

        if page_count == 0:
            raise DocumentExtractionError(
                "The PDF file contains no pages."
            )

        return sections, {"page_count": page_count}

    @staticmethod
    def _extract_docx(
        content: bytes,
    ) -> tuple[list[DocumentSection], dict[str, Any]]:
        try:
            document = DocxDocument(BytesIO(content))

            DocumentExtractionService._validate_docx_archive(content)

        except Exception as exc:
            raise DocumentExtractionError(
                "The DOCX file is invalid or could not be read."
            ) from exc

        sections: list[DocumentSection] = []

        for paragraph_number, paragraph in enumerate(
            document.paragraphs,
            start=1,
        ):
            if paragraph.text.strip():
                sections.append(
                    DocumentSection(
                        content=paragraph.text,
                        metadata={
                            "block_type": "paragraph",
                            "paragraph_number": paragraph_number,
                        },
                    )
                )

        for table_number, table in enumerate(document.tables, start=1):
            for row_number, row in enumerate(table.rows, start=1):
                values = [
                    cell.text.strip().replace("\n", " ")
                    for cell in row.cells
                ]

                row_text = " | ".join(
                    f"column_{column_number}: {value}"
                    for column_number, value in enumerate(values, start=1)
                    if value
                )

                if row_text:
                    sections.append(
                        DocumentSection(
                            content=row_text,
                            metadata={
                                "block_type": "table_row",
                                "table_number": table_number,
                                "row_number": row_number,
                            },
                        )
                    )

        return sections, {
            "paragraph_count": len(document.paragraphs),
            "table_count": len(document.tables),
        }

    @staticmethod
    def _extract_csv(
        content: bytes,
    ) -> tuple[list[DocumentSection], dict[str, Any]]:
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise DocumentExtractionError(
                "The CSV file must use valid UTF-8 text encoding."
            ) from exc

        try:
            reader = csv.reader(StringIO(text, newline=""), strict=True)
            raw_headers = next(reader, None)


            if not raw_headers or not any(
                header.strip() for header in raw_headers
            ):
                raise DocumentExtractionError(
                    "The CSV file must contain column headers."
                )

            headers = []
            for index, header in enumerate(raw_headers, start=1):
                normalized_header = header.strip()
                headers.append(
                    normalized_header or f"column_{index}"
                )

            if len(headers) > settings.MAX_CSV_COLUMNS:
                raise DocumentExtractionError(
                    "The CSV file exceeds the maximum supported "
                    f"column count of {settings.MAX_CSV_COLUMNS}."
                )

            sections: list[DocumentSection] = []

            for row_number, row in enumerate(reader, start=1):
                if row_number > settings.MAX_CSV_ROWS:
                    raise DocumentExtractionError(
                        "The CSV file exceeds the maximum supported "
                        f"row count of {settings.MAX_CSV_ROWS}."
                    )

                if not any(value.strip() for value in row):
                    continue

                # Do not silently discard cells or invent missing values.
                if len(row) != len(headers):
                    raise DocumentExtractionError(
                        f"CSV row {row_number + 1} has {len(row)} fields; "
                        f"expected {len(headers)}."
                    )

                fields = [
                    f"{header}: {value.strip()}"
                    for header, value in zip(headers, row)
                    if value.strip()
                ]

                if fields:
                    sections.append(
                        DocumentSection(
                            content=" | ".join(fields),
                            metadata={"row_number": row_number},
                        )
                    )

        except csv.Error as exc:
            raise DocumentExtractionError(
                "The CSV file contains malformed CSV data."
            ) from exc

        if not sections:
            raise DocumentExtractionError(
                "The CSV file contains no readable data rows."
            )

        return sections, {
            "row_count": len(sections),
            "column_count": len(headers),
            "column_names": headers,
        }

    @staticmethod
    def _extract_excel(
        content: bytes,
        extension: str,
    ) -> tuple[list[DocumentSection], dict[str, Any]]:
        if extension not in {"xls", "xlsx"}:
            raise DocumentExtractionError("Unsupported Excel format.")

        engine = "xlrd" if extension == "xls" else "openpyxl"

        try:
            DocumentExtractionService._validate_excel_limits(
                content,
                extension,
            )

            sheets = pd.read_excel(
                BytesIO(content),
                sheet_name=None,
                dtype=object,
                engine=engine,
            )
        except Exception as exc:
            raise DocumentExtractionError(
                "The Excel file is invalid or could not be read."
            ) from exc

        sections: list[DocumentSection] = []
        sheet_metadata: list[dict[str, Any]] = []

        for sheet_name, dataframe in sheets.items():
            headers = [
                str(column).strip()
                for column in dataframe.columns
            ]
            row_count = 0

            for row_number, values in enumerate(
                dataframe.itertuples(index=False, name=None),
                start=1,
            ):
                fields = []

                for header, value in zip(headers, values):
                    if value is None or pd.isna(value):
                        continue

                    value_text = str(value).strip()
                    if value_text:
                        fields.append(f"{header}: {value_text}")

                if fields:
                    sections.append(
                        DocumentSection(
                            content=" | ".join(fields),
                            metadata={
                                "sheet_name": str(sheet_name),
                                "row_number": row_number,
                            },
                        )
                    )
                    row_count += 1

            sheet_metadata.append(
                {
                    "sheet_name": str(sheet_name),
                    "column_names": headers,
                    "row_count": row_count,
                }
            )

        if not sections:
            raise DocumentExtractionError(
                "The Excel file contains no readable data rows."
            )

        return sections, {
            "sheet_count": len(sheets),
            "sheets": sheet_metadata,
        }

    @staticmethod
    def _normalize_text(text: str) -> str:
        normalized_lines = (
            text.replace("\r\n", "\n")
            .replace("\r", "\n")
            .split("\n")
        )

        return "\n".join(
            line.rstrip() for line in normalized_lines
        ).strip()
