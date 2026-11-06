from typing import Any, Literal

from pydantic import BaseModel, Field



class DocumentSection(BaseModel):

    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)



class ExtractedDocument(BaseModel):

    filename: str
    file_type: Literal["txt", "pdf", "docx", "csv", "xls", "xlsx"]
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    sections: list[DocumentSection] = Field(default_factory=list)
