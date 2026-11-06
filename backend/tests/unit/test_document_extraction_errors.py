import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.exceptions.handlers import register_exception_handlers
from app.core.exceptions import DocumentExtractionError
from app.services.document_extraction_service import (
    DocumentExtractionService,
)


@pytest.mark.parametrize(
    ("filename", "content"),
    [
        ("invalid.txt", b"\xff\xfe\xfa"),
        ("invalid.pdf", b"this is not a valid PDF"),
        ("invalid.docx", b"this is not a valid DOCX"),
        ("invalid.xlsx", b"this is not a valid XLSX"),
        ("invalid.xls", b"this is not a valid XLS"),
        ("invalid.csv", b"name,age\nAlice\n"),
    ],
)
def test_malformed_documents_raise_document_extraction_error(
    filename,
    content,
):
    with pytest.raises(DocumentExtractionError):
        DocumentExtractionService.extract_document(
            filename=filename,
            content=content,
        )


def test_empty_content_raises_document_extraction_error():
    with pytest.raises(
        DocumentExtractionError,
        match="uploaded file is empty",
    ):
        DocumentExtractionService.extract_document(
            filename="empty.txt",
            content=b"",
        )


def test_unsupported_extension_raises_document_extraction_error():
    with pytest.raises(
        DocumentExtractionError,
        match="Unsupported file type",
    ):
        DocumentExtractionService.extract_document(
            filename="document.exe",
            content=b"some content",
        )


def test_document_with_no_readable_text_raises_extraction_error():
    with pytest.raises(
        DocumentExtractionError,
        match="No readable text",
    ):
        DocumentExtractionService.extract_document(
            filename="blank.txt",
            content=b"   \n\n   ",
        )


def test_extraction_exception_returns_safe_http_response():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/test-extraction-error")
    async def trigger_extraction_error():
        raise DocumentExtractionError(
            "The PDF file is invalid or could not be read."
        )

    client = TestClient(app)

    response = client.get("/test-extraction-error")

    assert response.status_code == 422
    assert response.json() == {
        "detail": "The PDF file is invalid or could not be read."
    }

    assert "Traceback" not in response.text
