from fastapi import FastAPI

from app.core.config import settings

from app.api.routes.document import document_router
from app.exceptions.handlers import register_exception_handlers

app = FastAPI(
    title=settings.APP_NAME,
    description="A document analyzer",
    version="v1.0.0",
    contact={
        "name":"Mehfooz",
        "email":"mehfooz.sde@gmail.com"
    },
    license_info={
        "name":"MIT"
    },
    debug=settings.DEBUG
)


app.include_router(document_router)
register_exception_handlers(app)


@app.get("/health")
async def health_check():
    return {
        "status":"healthy",
        "service":settings.APP_NAME,
        "environment":settings.APP_ENV,
        "version":app.version
    }
