"""
BookFlow - API Principal
Sistema de Diagramação de Livros
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging

from app.config import get_settings

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia ciclo de vida da aplicação"""
    settings = get_settings()
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    os.makedirs(settings.TEMP_DIR, exist_ok=True)
    yield
    logger.info("Shutting down...")


def create_app() -> FastAPI:
    """Factory function para criar a aplicação FastAPI"""
    settings = get_settings()
    
    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="API para diagramação automática de livros com IA",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan
    )
    
    # CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Exception handlers
    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = []
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(x) for x in error["loc"]),
                "message": error["msg"],
                "type": error["type"]
            })
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "Validation error", "errors": errors}
        )
    
    @application.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal server error",
                "message": str(exc) if settings.DEBUG else "An unexpected error occurred"
            }
        )
    
    # Health check
    @application.get("/health")
    async def health_check():
        s = get_settings()
        return {"status": "healthy", "app": s.APP_NAME, "version": s.APP_VERSION}
    
    @application.get("/")
    async def root():
        s = get_settings()
        return {"app": s.APP_NAME, "version": s.APP_VERSION, "docs": "/docs" if s.DEBUG else "disabled"}
    
    # Templates públicos
    @application.get("/api/v1/templates")
    async def list_all_templates():
        from app.services.template_engine import TemplateEngine
        engine = TemplateEngine()
        return {"templates": engine.get_available_templates()}
    
    # Incluir routers
    from app.routes import projects, upload, preview, export
    application.include_router(projects.router, prefix="/api/v1")
    application.include_router(upload.router, prefix="/api/v1")
    application.include_router(preview.router, prefix="/api/v1")
    application.include_router(export.router, prefix="/api/v1")
    
    return application


# Criar app - só executa get_settings quando o módulo for realmente usado
app = create_app()


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
