
import pytest
from pydantic import ValidationError

from app.schemas.document import DocumentUploadResponse
from app.schemas.extracted_document import (
    DocumentSection,
    ExtractedDocument,
)



class TestDocumentUploadResponse:
    def test_valid_upload_response(self):
        extracted_document = ExtractedDocument(
            filename="report.pdf",
            file_type="pdf",
            content="Extracted document content.",
        )

        response = DocumentUploadResponse(
            filename="report.pdf",
            content_type="application/pdf",
            status="document_extracted",
            extracted_document=extracted_document,
        )

        assert response.filename == "report.pdf"
        assert response.content_type == "application/pdf"
        assert response.status == "document_extracted"
        assert response.extracted_document == extracted_document

    def test_optional_content_type_accepts_none(self):
        extracted_document = ExtractedDocument(
            filename="report.pdf",
            file_type="pdf",
            content="Extracted document content.",
        )

        response = DocumentUploadResponse(
            filename="report.pdf",
            content_type=None,
            status="document_extracted",
            extracted_document=extracted_document,
        )

        assert response.filename == "report.pdf"
        assert response.content_type is None
        assert response.status == "document_extracted"
        assert response.extracted_document == extracted_document

    def test_required_status_field(self):
        extracted_document = ExtractedDocument(
            filename="report.pdf",
            file_type="pdf",
            content="Extracted document content.",
        )

        with pytest.raises(ValidationError):
            DocumentUploadResponse(
                filename="report.pdf",
                content_type="application/pdf",
                extracted_document=extracted_document,
            )

    def test_required_fields_cannot_be_omitted(self):
        extracted_document = ExtractedDocument(
            filename="report.pdf",
            file_type="pdf",
            content="Extracted document content.",
        )

        with pytest.raises(ValidationError):
            DocumentUploadResponse(
                content_type="application/pdf",
                status="document_extracted",
                extracted_document=extracted_document,
            )


class TestDocumentSection:
    def test_valid_document_section(self):
        section = DocumentSection(
            content="This is extracted document content.",
            metadata={"page_number": 1},
        )

        assert section.content == "This is extracted document content."
        assert section.metadata == {"page_number": 1}

    def test_metadata_defaults_to_empty_dictionary(self):
        section = DocumentSection(
            content="Extracted content."
        )

        assert section.metadata == {}

    def test_default_metadata_is_independent(self):
        first = DocumentSection(content="First section.")
        second = DocumentSection(content="Second section.")

        first.metadata["page_number"] = 1

        assert second.metadata == {}


class TestExtractedDocument:
    def test_valid_extracted_document(self):
        document = ExtractedDocument(
            filename="report.pdf",
            file_type="pdf",
            content="Extracted document content.",
            metadata={"page_count": 1},
            sections=[
                DocumentSection(
                    content="Page one content.",
                    metadata={"page_number": 1},
                )
            ],
        )

        assert document.filename == "report.pdf"
        assert document.file_type == "pdf"
        assert document.content == "Extracted document content."
        assert document.metadata == {"page_count": 1}
        assert len(document.sections) == 1
        assert document.sections[0].content == "Page one content."

    @pytest.mark.parametrize(
        "file_type",
        ["txt", "pdf", "docx", "csv", "xls", "xlsx"],
    )
    def test_all_supported_file_types(self, file_type: str):
        document = ExtractedDocument(
            filename=f"report.{file_type}",
            file_type=file_type,
            content="Extracted content.",
        )

        assert document.file_type == file_type

    def test_unsupported_file_type_is_rejected(self):
        with pytest.raises(ValidationError):
            ExtractedDocument(
                filename="report.png",
                file_type="png",
                content="Extracted content.",
            )

    def test_metadata_and_sections_have_defaults(self):
        document = ExtractedDocument(
            filename="report.txt",
            file_type="txt",
            content="Extracted content.",
        )

        assert document.metadata == {}
        assert document.sections == []

    def test_default_values_are_independent(self):
        first = ExtractedDocument(
            filename="first.txt",
            file_type="txt",
            content="First document.",
        )
        second = ExtractedDocument(
            filename="second.txt",
            file_type="txt",
            content="Second document.",
        )

        first.metadata["source"] = "upload"
        first.sections.append(
            DocumentSection(content="First section.")
        )

        assert second.metadata == {}
        assert second.sections == []

    def test_nested_section_validation(self):
        document = ExtractedDocument(
            filename="report.pdf",
            file_type="pdf",
            content="Extracted content.",
            sections=[
                {
                    "content": "Page one.",
                    "metadata": {"page_number": 1},
                }
            ],
        )

        assert isinstance(document.sections[0], DocumentSection)
        assert document.sections[0].metadata["page_number"] == 1
