
from io import BytesIO

import pymupdf
import pandas as pd
import pytest
import xlwt
from docx import Document as DocxDocument

from app.services.document_extraction_service import (
    DocumentExtractionService,
)



def create_pdf(pages: list[str]) -> bytes:
    document = pymupdf.open()

    for page_text in pages:
        page = document.new_page()
        page.insert_text((72, 72), page_text)

    output = BytesIO()
    document.save(output)
    document.close()

    return output.getvalue()


def create_encrypted_pdf() -> bytes:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "Secret document")

    output = BytesIO()
    document.save(
        output,
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        owner_pw="owner-password",
        user_pw="user-password",
    )
    document.close()

    return output.getvalue()


def create_docx(
    paragraphs: list[str] | None = None,
    table_rows: list[list[str]] | None = None,
) -> bytes:
    document = DocxDocument()

    for paragraph in paragraphs or []:
        document.add_paragraph(paragraph)

    if table_rows:
        table = document.add_table(
            rows=len(table_rows),
            cols=len(table_rows[0]),
        )

        for row_index, row_values in enumerate(table_rows):
            for column_index, value in enumerate(row_values):
                table.cell(row_index, column_index).text = value

    output = BytesIO()
    document.save(output)

    return output.getvalue()


def create_xlsx(sheets: dict[str, list[list]]) -> bytes:
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for sheet_name, rows in sheets.items():
            if not rows:
                dataframe = pd.DataFrame()
            else:
                headers = rows[0]
                records = rows[1:]
                dataframe = pd.DataFrame(
                    records,
                    columns=headers,
                )

            dataframe.to_excel(
                writer,
                sheet_name=sheet_name,
                index=False,
            )

    return output.getvalue()


def create_xls(sheets: dict[str, list[list]]) -> bytes:
    workbook = xlwt.Workbook()

    for sheet_name, rows in sheets.items():
        worksheet = workbook.add_sheet(sheet_name)

        for row_index, row_values in enumerate(rows):
            for column_index, value in enumerate(row_values):
                worksheet.write(row_index, column_index, value)

    output = BytesIO()
    workbook.save(output)

    return output.getvalue()



def test_extract_document_rejects_missing_filename():
    with pytest.raises(ValueError, match="A filename is required"):
        DocumentExtractionService.extract_document(
            filename="",
            content=b"Some content",
        )


@pytest.mark.parametrize("filename", ["", " ", "   "])
def test_extract_document_rejects_blank_filename(filename):
    with pytest.raises(ValueError, match="A filename is required"):
        DocumentExtractionService.extract_document(
            filename=filename,
            content=b"Some content",
        )


def test_extract_document_rejects_empty_content():
    with pytest.raises(ValueError, match="uploaded file is empty"):
        DocumentExtractionService.extract_document(
            filename="report.txt",
            content=b"",
        )


@pytest.mark.parametrize(
    "filename",
    [
        "report.exe",
        "report.png",
        "report",
        "report.",
    ],
)
def test_extract_document_rejects_unsupported_extensions(filename):
    with pytest.raises(ValueError, match="Unsupported file type"):
        DocumentExtractionService.extract_document(
            filename=filename,
            content=b"Some content",
        )


def test_extract_document_normalizes_uppercase_extension():
    result = DocumentExtractionService.extract_document(
        filename="REPORT.TXT",
        content=b"Hello world",
    )

    assert result.filename == "REPORT.TXT"
    assert result.file_type == "txt"
    assert result.content == "Hello world"


@pytest.mark.parametrize(
    "filename",
    [
        "folder/report.txt",
        "folder\\report.txt",
        "../../folder/report.txt",
        "C:\\documents\\report.txt",
    ],
)
def test_extract_document_sanitizes_filename_paths(filename):
    result = DocumentExtractionService.extract_document(
        filename=filename,
        content=b"Hello world",
    )

    assert result.filename == "report.txt"


def test_extract_document_rejects_filename_without_valid_basename():
    with pytest.raises(ValueError, match="A valid filename is required"):
        DocumentExtractionService.extract_document(
            filename=".",
            content=b"Hello world",
        )


def test_supported_extensions_contains_all_six_formats():
    assert DocumentExtractionService.SUPPORTED_EXTENSIONS == {
        "txt",
        "pdf",
        "docx",
        "csv",
        "xls",
        "xlsx",
    }



def test_extract_txt_returns_text_and_encoding_metadata():
    result = DocumentExtractionService.extract_document(
        filename="notes.txt",
        content=b"First line\nSecond line",
    )

    assert result.file_type == "txt"
    assert result.content == "First line\nSecond line"
    assert result.metadata["encoding"] == "utf-8"
    assert result.metadata["section_count"] == 1
    assert result.sections[0].content == result.content


def test_extract_txt_supports_utf8_bom():
    result = DocumentExtractionService.extract_document(
        filename="notes.txt",
        content=b"\xef\xbb\xbfHello from UTF-8 BOM",
    )

    assert result.content == "Hello from UTF-8 BOM"
    assert result.metadata["encoding"] == "utf-8"


def test_extract_txt_rejects_invalid_utf8():
    with pytest.raises(ValueError, match="valid UTF-8"):
        DocumentExtractionService.extract_document(
            filename="notes.txt",
            content=b"\xff\xfe\xfa",
        )


def test_extract_txt_rejects_whitespace_only_content():
    with pytest.raises(ValueError, match="No readable text"):
        DocumentExtractionService.extract_document(
            filename="notes.txt",
            content=b"   \n   \n\t",
        )



def test_extract_pdf_extracts_multiple_pages():
    pdf_content = create_pdf(
        [
            "First page content",
            "Second page content",
        ]
    )

    result = DocumentExtractionService.extract_document(
        filename="report.pdf",
        content=pdf_content,
    )

    assert result.file_type == "pdf"
    assert len(result.sections) == 2
    assert result.sections[0].content == "First page content"
    assert result.sections[1].content == "Second page content"
    assert result.sections[0].metadata["page_number"] == 1
    assert result.sections[1].metadata["page_number"] == 2
    assert result.metadata["page_count"] == 2
    assert result.metadata["section_count"] == 2


def test_extract_pdf_rejects_malformed_pdf():
    with pytest.raises(ValueError, match="invalid or could not be read"):
        DocumentExtractionService.extract_document(
            filename="broken.pdf",
            content=b"This is not a PDF file",
        )


def test_extract_pdf_rejects_encrypted_pdf():
    with pytest.raises(
        ValueError,
        match="Password-protected PDF",
    ):
        DocumentExtractionService.extract_document(
            filename="private.pdf",
            content=create_encrypted_pdf(),
        )


def test_extract_pdf_rejects_pdf_without_readable_text():
    result = create_pdf(["   \n   "])

    with pytest.raises(ValueError, match="No readable text"):
        DocumentExtractionService.extract_document(
            filename="blank.pdf",
            content=result,
        )



def test_extract_docx_extracts_paragraphs():
    result = DocumentExtractionService.extract_document(
        filename="report.docx",
        content=create_docx(
            paragraphs=[
                "First paragraph",
                "Second paragraph",
            ]
        ),
    )

    assert result.file_type == "docx"
    assert len(result.sections) == 2
    assert result.sections[0].content == "First paragraph"
    assert result.sections[1].content == "Second paragraph"
    assert result.sections[0].metadata == {
        "block_type": "paragraph",
        "paragraph_number": 1,
    }
    assert result.sections[1].metadata == {
        "block_type": "paragraph",
        "paragraph_number": 2,
    }
    assert result.metadata["paragraph_count"] == 2
    assert result.metadata["table_count"] == 0


def test_extract_docx_extracts_table_rows():
    result = DocumentExtractionService.extract_document(
        filename="table.docx",
        content=create_docx(
            table_rows=[
                ["Name", "Role"],
                ["Mehfooz", "Student"],
            ]
        ),
    )

    assert len(result.sections) == 2
    assert result.sections[0].content == (
        "column_1: Name | column_2: Role"
    )
    assert result.sections[1].content == (
        "column_1: Mehfooz | column_2: Student"
    )
    assert result.sections[0].metadata == {
        "block_type": "table_row",
        "table_number": 1,
        "row_number": 1,
    }
    assert result.sections[1].metadata["row_number"] == 2
    assert result.metadata["table_count"] == 1


def test_extract_docx_extracts_paragraphs_and_tables():
    result = DocumentExtractionService.extract_document(
        filename="mixed.docx",
        content=create_docx(
            paragraphs=["Document introduction"],
            table_rows=[
                ["Product", "Price"],
                ["Keyboard", "1000"],
            ],
        ),
    )

    assert len(result.sections) == 3
    assert result.sections[0].content == "Document introduction"
    assert result.sections[1].metadata["block_type"] == "table_row"
    assert result.sections[2].metadata["block_type"] == "table_row"


def test_extract_docx_rejects_malformed_document():
    with pytest.raises(ValueError, match="invalid or could not be read"):
        DocumentExtractionService.extract_document(
            filename="broken.docx",
            content=b"Not a DOCX document",
        )


def test_extract_docx_rejects_document_without_readable_content():
    result = DocumentExtractionService.extract_document if False else None
    empty_docx = create_docx()

    with pytest.raises(ValueError, match="No readable text"):
        DocumentExtractionService.extract_document(
            filename="empty.docx",
            content=empty_docx,
        )



def test_extract_csv_preserves_header_value_relationships():
    result = DocumentExtractionService.extract_document(
        filename="people.csv",
        content=(
            b"name,role\n"
            b"Mehfooz,Student\n"
            b"Alex,Developer\n"
        ),
    )

    assert result.file_type == "csv"
    assert len(result.sections) == 2
    assert result.sections[0].content == (
        "name: Mehfooz | role: Student"
    )
    assert result.sections[1].content == (
        "name: Alex | role: Developer"
    )
    assert result.sections[0].metadata["row_number"] == 1
    assert result.sections[1].metadata["row_number"] == 2
    assert result.metadata["row_count"] == 2
    assert result.metadata["column_count"] == 2
    assert result.metadata["column_names"] == ["name", "role"]


def test_extract_csv_supports_utf8_bom():
    result = DocumentExtractionService.extract_document(
        filename="people.csv",
        content=(
            b"\xef\xbb\xbfname,role\n"
            b"Mehfooz,Student\n"
        ),
    )

    assert result.sections[0].content == (
        "name: Mehfooz | role: Student"
    )


def test_extract_csv_supports_quoted_commas():
    result = DocumentExtractionService.extract_document(
        filename="quotes.csv",
        content=(
            b"name,description\n"
            b'Mehfooz,"Backend, Python developer"\n'
        ),
    )

    assert result.sections[0].content == (
        "name: Mehfooz | description: Backend, Python developer"
    )


def test_extract_csv_ignores_blank_rows():
    result = DocumentExtractionService.extract_document(
        filename="people.csv",
        content=(
            b"name,role\n"
            b"Mehfooz,Student\n"
            b",\n"
            b"Alex,Developer\n"
        ),
    )

    assert len(result.sections) == 2
    assert result.metadata["row_count"] == 2


def test_extract_csv_generates_names_for_blank_headers():
    result = DocumentExtractionService.extract_document(
        filename="data.csv",
        content=(
            b"name,,city\n"
            b"Mehfooz,18,Delhi\n"
        ),
    )

    assert result.metadata["column_names"] == [
        "name",
        "column_2",
        "city",
    ]
    assert result.sections[0].content == (
        "name: Mehfooz | column_2: 18 | city: Delhi"
    )


@pytest.mark.parametrize(
    "content",
    [
        b"\n",
        b",,\n",
    ],
)
def test_extract_csv_rejects_missing_or_blank_headers(content):
    with pytest.raises(ValueError, match="column headers"):
        DocumentExtractionService.extract_document(
            filename="empty.csv",
            content=content,
        )


def test_extract_csv_rejects_inconsistent_row_columns():
    with pytest.raises(ValueError, match="fields; expected"):
        DocumentExtractionService.extract_document(
            filename="broken.csv",
            content=(
                b"name,role\n"
                b"Mehfooz,Student,Extra\n"
            ),
        )


def test_extract_csv_rejects_malformed_quoting():
    with pytest.raises(ValueError, match="malformed CSV"):
        DocumentExtractionService.extract_document(
            filename="broken.csv",
            content=(
                b'name,description\n'
                b'Mehfooz,"unfinished description\n'
            ),
        )


def test_extract_csv_rejects_invalid_utf8():
    with pytest.raises(ValueError, match="valid UTF-8"):
        DocumentExtractionService.extract_document(
            filename="broken.csv",
            content=b"name,role\n\xff,\xfe",
        )


def test_extract_csv_rejects_header_only_file():
    with pytest.raises(ValueError, match="no readable data rows"):
        DocumentExtractionService.extract_document(
            filename="headers.csv",
            content=b"name,role\n",
        )



def test_extract_xlsx_extracts_rows_and_metadata():
    content = create_xlsx(
        {
            "Employees": [
                ["name", "role"],
                ["Mehfooz", "Student"],
                ["Alex", "Developer"],
            ]
        }
    )

    result = DocumentExtractionService.extract_document(
        filename="employees.xlsx",
        content=content,
    )

    assert result.file_type == "xlsx"
    assert len(result.sections) == 2
    assert result.sections[0].content == (
        "name: Mehfooz | role: Student"
    )
    assert result.sections[0].metadata == {
        "sheet_name": "Employees",
        "row_number": 1,
    }
    assert result.metadata["sheet_count"] == 1
    assert result.metadata["sheets"][0]["sheet_name"] == "Employees"
    assert result.metadata["sheets"][0]["column_names"] == [
        "name",
        "role",
    ]
    assert result.metadata["sheets"][0]["row_count"] == 2


def test_extract_xlsx_supports_multiple_sheets():
    content = create_xlsx(
        {
            "Employees": [
                ["name", "role"],
                ["Mehfooz", "Student"],
            ],
            "Departments": [
                ["department", "location"],
                ["Engineering", "Delhi"],
            ],
        }
    )

    result = DocumentExtractionService.extract_document(
        filename="company.xlsx",
        content=content,
    )

    assert result.metadata["sheet_count"] == 2
    assert len(result.sections) == 2
    assert result.sections[0].metadata["sheet_name"] == "Employees"
    assert result.sections[1].metadata["sheet_name"] == "Departments"


def test_extract_xlsx_skips_empty_cells():
    content = create_xlsx(
        {
            "Data": [
                ["name", "role", "city"],
                ["Mehfooz", None, "Delhi"],
            ]
        }
    )

    result = DocumentExtractionService.extract_document(
        filename="data.xlsx",
        content=content,
    )

    assert result.sections[0].content == (
        "name: Mehfooz | city: Delhi"
    )


def test_extract_xlsx_preserves_numeric_values():
    content = create_xlsx(
        {
            "Scores": [
                ["name", "score"],
                ["Mehfooz", 95],
            ]
        }
    )

    result = DocumentExtractionService.extract_document(
        filename="scores.xlsx",
        content=content,
    )

    assert result.sections[0].content == (
        "name: Mehfooz | score: 95"
    )


def test_extract_xlsx_rejects_malformed_workbook():
    with pytest.raises(ValueError, match="invalid or could not be read"):
        DocumentExtractionService.extract_document(
            filename="broken.xlsx",
            content=b"Not an XLSX workbook",
        )


def test_extract_xlsx_rejects_workbook_without_readable_rows():
    content = create_xlsx(
        {
            "Empty": [
                ["name", "role"],
            ]
        }
    )

    with pytest.raises(ValueError, match="no readable data rows"):
        DocumentExtractionService.extract_document(
            filename="empty.xlsx",
            content=content,
        )


def test_extract_xls_extracts_rows_and_metadata():
    content = create_xls(
        {
            "Employees": [
                ["name", "role"],
                ["Mehfooz", "Student"],
                ["Alex", "Developer"],
            ]
        }
    )

    result = DocumentExtractionService.extract_document(
        filename="employees.xls",
        content=content,
    )

    assert result.file_type == "xls"
    assert len(result.sections) == 2
    assert result.sections[0].content == (
        "name: Mehfooz | role: Student"
    )
    assert result.sections[0].metadata == {
        "sheet_name": "Employees",
        "row_number": 1,
    }
    assert result.metadata["sheet_count"] == 1
    assert result.metadata["sheets"][0]["column_names"] == [
        "name",
        "role",
    ]
    assert result.metadata["sheets"][0]["row_count"] == 2


def test_extract_xls_supports_multiple_sheets():
    content = create_xls(
        {
            "Employees": [
                ["name", "role"],
                ["Mehfooz", "Student"],
            ],
            "Departments": [
                ["department", "location"],
                ["Engineering", "Delhi"],
            ],
        }
    )

    result = DocumentExtractionService.extract_document(
        filename="company.xls",
        content=content,
    )

    assert result.metadata["sheet_count"] == 2
    assert len(result.sections) == 2
    assert result.sections[0].metadata["sheet_name"] == "Employees"
    assert result.sections[1].metadata["sheet_name"] == "Departments"


def test_extract_xls_rejects_malformed_workbook():
    with pytest.raises(ValueError, match="invalid or could not be read"):
        DocumentExtractionService.extract_document(
            filename="broken.xls",
            content=b"Not an XLS workbook",
        )


def test_extract_xls_rejects_workbook_without_readable_rows():
    content = create_xls(
        {
            "Empty": [
                ["name", "role"],
            ]
        }
    )

    with pytest.raises(ValueError, match="no readable data rows"):
        DocumentExtractionService.extract_document(
            filename="empty.xls",
            content=content,
        )



def test_normalize_text_converts_line_endings_and_trims_whitespace():
    result = DocumentExtractionService._normalize_text(
        "  First line  \r\nSecond line   \rThird line\t\n"
    )

    assert result == "First line\nSecond line\nThird line"


def test_extract_document_normalizes_content_and_calculates_metadata():
    result = DocumentExtractionService.extract_document(
        filename="notes.txt",
        content=b"  First line  \r\nSecond line   \r",
    )

    assert result.content == "First line\nSecond line"
    assert result.metadata["character_count"] == len(result.content)
    assert result.metadata["section_count"] == len(result.sections)


def test_extract_document_joins_multiple_sections_with_blank_line():
    content = create_pdf(
        [
            "First page",
            "Second page",
        ]
    )

    result = DocumentExtractionService.extract_document(
        filename="report.pdf",
        content=content,
    )

    assert result.content == "First page\n\nSecond page"


def test_extract_document_preserves_section_metadata():
    result = DocumentExtractionService.extract_document(
        filename="notes.txt",
        content=b"Hello world",
    )

    assert result.sections[0].metadata == {}
    assert isinstance(result.metadata, dict)
    assert isinstance(result.sections, list)
