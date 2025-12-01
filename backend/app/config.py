"""
BookFlow - Configurações do Backend
"""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Configurações da aplicação carregadas de variáveis de ambiente"""
    
    # App
    APP_NAME: str = "BookFlow API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str  # Para operações admin
    
    # Anthropic (Claude)
    ANTHROPIC_API_KEY: str
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"
    CLAUDE_MAX_TOKENS: int = 8192
    CLAUDE_TIMEOUT: int = 120  # segundos
    
    # Storage
    UPLOAD_MAX_SIZE_MB: int = 100
    ALLOWED_MIME_TYPES: list = ["application/pdf"]
    
    # Paths
    TEMP_DIR: str = "/tmp/bookflow"
    
    # CORS
    CORS_ORIGINS: list = ["http://localhost:3000", "https://*.vercel.app"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Retorna settings cacheado (singleton)"""
    return Settings()


# Constantes de status
class ProjectStatus:
    CREATED = "created"
    UPLOADED = "uploaded"
    EXTRACTING = "extracting"
    PARSED = "parsed"
    NORMALIZING = "normalizing"
    NORMALIZED = "normalized"
    TEMPLATED = "templated"
    APPROVED = "approved"
    EXPORTING = "exporting"
    EXPORTED = "exported"
    ERROR = "error"


class RenditionStatus:
    PENDING = "pending"
    PREVIEW_GENERATING = "preview_generating"
    PREVIEW_GENERATED = "preview_generated"
    APPROVED = "approved"
    PDF_GENERATING = "pdf_generating"
    PDF_GENERATED = "pdf_generated"
    ERROR = "error"


# Templates keys
TEMPLATE_KEYS = [
    "minimalist",
    "classic",
    "editorial",
    "academic",
    "fantasy",
    "business"
]
