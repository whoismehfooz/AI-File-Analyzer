from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import DocumentExtractionError


def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(DocumentExtractionError)
    async def document_extraction_exception_handler(
        request: Request,
        exc: DocumentExtractionError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "detail": str(exc),
            },
        )
