from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core.exceptions import (
    DocumentExtractionError,
    DocumentTooLargeError,
    DocumentValidationError,
)
from app.schemas.document import DocumentUploadResponse
from app.services.document_extraction_service import (
    DocumentExtractionService,
)
from app.services.document_validation_service import (
    DocumentValidationService,
)


document_router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


@document_router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_200_OK,
)
async def upload_document(
    file: UploadFile = File(...),
) -> DocumentUploadResponse:
    try:
        # 1. Validate filename, extension and uploaded file size.
        await DocumentValidationService.validate_upload(file)

        # 2. Read the validated file.
        content = await file.read()

        # 3. Extract document content and metadata.
        extracted_document = (
            DocumentExtractionService.extract_document(
                filename=file.filename or "",
                content=content,
            )
        )

        # 4. Return the complete extraction result.
        return DocumentUploadResponse(
            filename=file.filename or "",
            content_type=file.content_type,
            status="document_extracted",
            extracted_document=extracted_document,
        )

    except DocumentTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        ) from exc

    except DocumentValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except DocumentExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
