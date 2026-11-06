from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.extracted_document import ExtractedDocument


class DocumentUploadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str
    content_type: str | None = None
    status: Literal["document_extracted"]
    extracted_document: ExtractedDocument
