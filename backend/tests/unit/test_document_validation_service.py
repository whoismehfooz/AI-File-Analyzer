from io import BytesIO

import pytest
from fastapi import UploadFile

from app.core.config import settings
from app.services import DocumentExtractionService, DocumentValidationService
from app.core.exceptions import (
    DocumentValidationError,
    DocumentTooLargeError
)

def create_upload_file(
    filename: str,
    content: bytes = b"test document content",
) -> UploadFile:
    return UploadFile(
        filename=filename,
        file=BytesIO(content),
    )



def test_allowed_extensions_normalizes_configuration(monkeypatch):
    monkeypatch.setattr(
        settings,
        "ALLOWED_DOCUMENT_EXTENSIONS",
        " .TXT, .PDF, .DocX, , .CSV ",
    )

    extensions = DocumentValidationService.allowed_extensions()

    assert extensions == {".txt", ".pdf", ".docx", ".csv"}


def test_allowed_extensions_returns_empty_set_for_empty_configuration(
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "ALLOWED_DOCUMENT_EXTENSIONS",
        " , , ",
    )

    assert DocumentValidationService.allowed_extensions() == set()



@pytest.mark.parametrize(
    "extension",
    [".txt", ".pdf", ".docx"],
)
@pytest.mark.asyncio
async def test_validate_upload_accepts_supported_extensions(
    extension,
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "ALLOWED_DOCUMENT_EXTENSIONS",
        ".txt,.pdf,.docx",
    )

    upload = create_upload_file(f"report{extension}")

    result = await DocumentValidationService.validate_upload(upload)

    assert result is None
    assert upload.file.tell() == 0


@pytest.mark.parametrize(
    "filename",
    [
        "report.TXT",
        "report.PDF",
        "report.DOCX",
    ],
)
@pytest.mark.asyncio
async def test_validate_upload_accepts_uppercase_extensions(
    filename,
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "ALLOWED_DOCUMENT_EXTENSIONS",
        ".txt,.pdf,.docx",
    )

    upload = create_upload_file(filename)

    await DocumentValidationService.validate_upload(upload)

    assert upload.file.tell() == 0


@pytest.mark.parametrize(
    "filename",
    [
        "report.exe",
        "report.png",
        "report.csv",
        "report",
        "report.",
    ],
)
@pytest.mark.asyncio
async def test_validate_upload_rejects_unsupported_extensions(
    filename,
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "ALLOWED_DOCUMENT_EXTENSIONS",
        ".txt,.pdf,.docx",
    )

    upload = create_upload_file(filename)

    with pytest.raises(ValueError, match="Unsupported file type"):
        await DocumentValidationService.validate_upload(upload)



@pytest.mark.parametrize(
    "filename",
    [
        None,
        "",
        "   ",
    ],
)
@pytest.mark.asyncio
async def test_validate_upload_rejects_missing_or_blank_filenames(filename):
    upload = create_upload_file("placeholder.txt")
    upload.filename = filename

    with pytest.raises(ValueError, match="A filename is required"):
        await DocumentValidationService.validate_upload(upload)


@pytest.mark.parametrize(
    "filename",
    [
        "folder/report.txt",
        "folder\\report.txt",
        "../../folder/report.txt",
        "C:\\documents\\report.txt",
    ],
)
@pytest.mark.asyncio
async def test_validate_upload_checks_extension_of_filename_basename(
    filename,
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "ALLOWED_DOCUMENT_EXTENSIONS",
        ".txt",
    )

    upload = create_upload_file(filename)

    await DocumentValidationService.validate_upload(upload)

    assert upload.file.tell() == 0


@pytest.mark.asyncio
async def test_validate_upload_accepts_file_at_exact_size_limit(monkeypatch):
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 1)
    monkeypatch.setattr(
        settings,
        "ALLOWED_DOCUMENT_EXTENSIONS",
        ".txt",
    )

    content = b"x" * (1024 * 1024)
    upload = create_upload_file("large.txt", content)

    await DocumentValidationService.validate_upload(upload)

    assert upload.file.tell() == 0


@pytest.mark.asyncio
async def test_validate_upload_rejects_file_above_size_limit(monkeypatch):
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 1)
    monkeypatch.setattr(
        settings,
        "ALLOWED_DOCUMENT_EXTENSIONS",
        ".txt",
    )

    content = b"x" * (1024 * 1024 + 1)
    upload = create_upload_file("oversized.txt", content)

    with pytest.raises(
        ValueError,
        match="File exceeds the 1 MB limit",
    ):
        await DocumentValidationService.validate_upload(upload)

    assert upload.file.tell() == 0



@pytest.mark.asyncio
async def test_validate_upload_resets_file_pointer_after_success(monkeypatch):
    monkeypatch.setattr(
        settings,
        "ALLOWED_DOCUMENT_EXTENSIONS",
        ".txt",
    )
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 1)

    upload = create_upload_file(
        "report.txt",
        b"Some document content.",
    )

    await DocumentValidationService.validate_upload(upload)

    assert upload.file.tell() == 0
    assert await upload.read() == b"Some document content."


@pytest.mark.asyncio
async def test_validate_upload_resets_file_pointer_after_size_error(monkeypatch):
    monkeypatch.setattr(
        settings,
        "ALLOWED_DOCUMENT_EXTENSIONS",
        ".txt",
    )
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 1)

    content = b"x" * (1024 * 1024 + 1)
    upload = create_upload_file("oversized.txt", content)

    with pytest.raises(ValueError):
        await DocumentValidationService.validate_upload(upload)

    assert upload.file.tell() == 0


@pytest.mark.asyncio
async def test_validate_upload_handles_multiple_read_chunks(monkeypatch):
    monkeypatch.setattr(
        settings,
        "ALLOWED_DOCUMENT_EXTENSIONS",
        ".txt",
    )
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 2)

    content = b"x" * (1024 * 1024 + 100)
    upload = create_upload_file("report.txt", content)

    await DocumentValidationService.validate_upload(upload)

    assert upload.file.tell() == 0



def test_extract_document_handles_large_txt_file():
    filename = "large_document.txt"
    content = (
        "This is a large document used for extraction testing.\n" * 100_000
    ).encode("utf-8")

    extracted = DocumentExtractionService.extract_document(
        filename=filename,
        content=content,
    )

    assert extracted.filename == filename
    assert extracted.file_type == "txt"
    assert extracted.content.startswith("This is a large document")
    assert extracted.content.endswith("testing.")
    assert extracted.metadata["character_count"] == len(extracted.content)
    assert extracted.metadata["section_count"] == len(extracted.sections)



def test_extract_document_preserves_unicode_and_normalizes_whitespace():
    filename = "unicode_document.txt"
    content = (
        "  नमस्ते दुनिया  \r\n"
        "مرحبا بالعالم   \r"
        "こんにちは世界\t\n"
        "Café 🚀  "
    ).encode("utf-8")

    extracted = DocumentExtractionService.extract_document(
        filename=filename,
        content=content,
    )

    assert extracted.content == (
        "नमस्ते दुनिया\n"
        "مرحبا بالعالم\n"
        "こんにちは世界\n"
        "Café 🚀"
    )
    assert extracted.metadata["character_count"] == len(extracted.content)


def test_extract_csv_handles_large_number_of_rows_and_columns():
    headers = [f"column_{index}" for index in range(30)]
    rows = [
        [f"row_{row_index}_value_{column_index}" for column_index in range(30)]
        for row_index in range(5_000)
    ]

    csv_content = "\n".join(
        [
            ",".join(headers),
            *(",".join(row) for row in rows),
        ]
    ).encode("utf-8")

    extracted = DocumentExtractionService.extract_document(
        filename="large_dataset.csv",
        content=csv_content,
    )

    assert extracted.filename == "large_dataset.csv"
    assert extracted.file_type == "csv"
    assert "column_0" in extracted.content
    assert "column_29" in extracted.content
    assert "row_0_value_0" in extracted.content
    assert "row_4999_value_29" in extracted.content
    assert extracted.metadata["character_count"] == len(extracted.content)
    assert extracted.metadata["section_count"] == len(extracted.sections)



@pytest.mark.parametrize(
    "filename",
    [
        "folder/",
        ".",
        "..",
    ],
)
@pytest.mark.asyncio
async def test_validate_upload_rejects_invalid_basenames(
    filename,
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "ALLOWED_DOCUMENT_EXTENSIONS",
        ".txt",
    )

    upload = create_upload_file(filename)

    with pytest.raises(ValueError, match="A valid filename is required"):
        await DocumentValidationService.validate_upload(upload)


@pytest.mark.parametrize(
    "filename",
    [
        "report\x00.txt",
        "report\n.txt",
        "report\t.txt",
        "report\x7f.txt",
    ],
)
@pytest.mark.asyncio
async def test_validate_upload_rejects_control_characters(filename):
    upload = create_upload_file(filename)

    with pytest.raises(
        ValueError,
        match="filename contains invalid characters",
    ):
        await DocumentValidationService.validate_upload(upload)


@pytest.mark.parametrize(
    "filename",
    [
        "report.",
        "report",
        "report.exe",
    ],
)
@pytest.mark.asyncio
async def test_validate_upload_rejects_filenames_without_allowed_extension(
    filename,
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "ALLOWED_DOCUMENT_EXTENSIONS",
        ".txt,.pdf",
    )

    upload = create_upload_file(filename)

    with pytest.raises(ValueError, match="Unsupported file type"):
        await DocumentValidationService.validate_upload(upload)


@pytest.mark.asyncio
async def test_validate_upload_rejects_empty_file(monkeypatch):
    monkeypatch.setattr(
        settings,
        "ALLOWED_DOCUMENT_EXTENSIONS",
        ".txt",
    )

    upload = create_upload_file("empty.txt", b"")

    with pytest.raises(ValueError, match="uploaded file is empty"):
        await DocumentValidationService.validate_upload(upload)

    assert upload.file.tell() == 0


@pytest.mark.asyncio
async def test_validate_upload_resets_file_pointer_after_empty_file_error(monkeypatch):
    monkeypatch.setattr(
        settings,
        "ALLOWED_DOCUMENT_EXTENSIONS",
        ".txt",
    )

    upload = create_upload_file("empty.txt", b"")

    with pytest.raises(ValueError):
        await DocumentValidationService.validate_upload(upload)

    assert upload.file.tell() == 0



@pytest.mark.asyncio
async def test_unsupported_extension_raises_document_validation_error(monkeypatch):
    monkeypatch.setattr(
        settings,
        "ALLOWED_DOCUMENT_EXTENSIONS",
        ".txt,.pdf,.docx,.csv,.xls,.xlsx",
    )

    upload = create_upload_file("malware.exe")

    with pytest.raises(DocumentValidationError):
        await DocumentValidationService.validate_upload(upload)


@pytest.mark.asyncio
async def test_oversized_upload_raises_document_too_large_error(monkeypatch):
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 1)
    monkeypatch.setattr(
        settings,
        "ALLOWED_DOCUMENT_EXTENSIONS",
        ".txt",
    )

    content = b"x" * (1024 * 1024 + 1)
    upload = create_upload_file("large.txt", content)

    with pytest.raises(DocumentTooLargeError):
        await DocumentValidationService.validate_upload(upload)

    assert upload.file.tell() == 0


@pytest.mark.asyncio
async def test_empty_upload_raises_document_validation_error(monkeypatch):
    monkeypatch.setattr(
        settings,
        "ALLOWED_DOCUMENT_EXTENSIONS",
        ".txt",
    )

    upload = create_upload_file("empty.txt", b"")

    with pytest.raises(DocumentValidationError):
        await DocumentValidationService.validate_upload(upload)

    assert upload.file.tell() == 0
