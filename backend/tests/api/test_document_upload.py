
import pytest

from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_upload_txt_document_successfully(client):
    response = client.post(
        "/documents/upload",
        files={
            "file": (
                "example.txt",
                b"Hello, this is a document for analysis.",
                "text/plain",
            )
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["filename"] == "example.txt"
    assert data["content_type"] == "text/plain"
    assert data["status"] == "document_extracted"

    extracted = data["extracted_document"]

    assert extracted["filename"] == "example.txt"
    assert extracted["file_type"] == "txt"
    assert extracted["content"] == (
        "Hello, this is a document for analysis."
    )

    assert extracted["metadata"]["encoding"] == "utf-8"
    assert extracted["metadata"]["section_count"] == 1

    assert len(extracted["sections"]) == 1
    assert extracted["sections"][0]["content"] == (
        "Hello, this is a document for analysis."
    )


def test_upload_rejects_unsupported_extension(client):
    response = client.post(
        "/documents/upload",
        files={
            "file": (
                "document.exe",
                b"not a supported document",
                "application/octet-stream",
            )
        },
    )

    assert response.status_code == 400

    assert "Unsupported file type" in response.json()["detail"]


def test_upload_rejects_empty_file(client):
    response = client.post(
        "/documents/upload",
        files={
            "file": (
                "empty.txt",
                b"",
                "text/plain",
            )
        },
    )

    assert response.status_code == 400

    assert response.json()["detail"] == (
        "The uploaded file is empty."
    )


def test_upload_returns_422_for_extraction_failure(client):
    response = client.post(
        "/documents/upload",
        files={
            "file": (
                "invalid.txt",
                b"\xff\xfe\xfa",
                "text/plain",
            )
        },
    )

    assert response.status_code == 422

    assert response.json()["detail"] == (
        "The TXT file must use valid UTF-8 text encoding."
    )


def test_upload_returns_extracted_sections_and_metadata(client):
    content = (
        b"name,age\n"
        b"Alice,20\n"
        b"Bob,22\n"
    )

    response = client.post(
        "/documents/upload",
        files={
            "file": (
                "people.csv",
                content,
                "text/csv",
            )
        },
    )

    assert response.status_code == 200

    extracted = response.json()["extracted_document"]

    assert extracted["file_type"] == "csv"
    assert extracted["metadata"]["column_count"] == 2
    assert extracted["metadata"]["column_names"] == [
        "name",
        "age",
    ]

    assert extracted["metadata"]["row_count"] == 2

    assert len(extracted["sections"]) == 2

    assert extracted["sections"][0]["metadata"]["row_number"] == 1
    assert extracted["sections"][1]["metadata"]["row_number"] == 2
