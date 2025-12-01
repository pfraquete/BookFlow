"""
BookFlow - Cliente de Banco de Dados (Supabase)
"""
from supabase import create_client, Client
from functools import lru_cache
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache()
def get_supabase_client() -> Optional[Client]:
    """Retorna cliente Supabase cacheado, ou None se não configurado"""
    settings = get_settings()
    if not settings.validate_supabase():
        logger.warning("Supabase not configured. Database operations will fail.")
        return None
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_ROLE_KEY  # Service role para bypass RLS quando necessário
    )


def get_user_client(access_token: str) -> Optional[Client]:
    """Retorna cliente Supabase com token do usuário (respeita RLS)"""
    settings = get_settings()
    if not settings.validate_supabase():
        logger.warning("Supabase not configured. User client unavailable.")
        return None
    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    client.auth.set_session(access_token, "")
    return client


class DatabaseService:
    """Serviço de acesso ao banco de dados"""

    def __init__(self, client: Optional[Client] = None):
        self.client = client if client is not None else get_supabase_client()
        if self.client is None:
            logger.warning("DatabaseService initialized without Supabase client")
    
    # =========================================================================
    # PROJECTS
    # =========================================================================
    
    async def create_project(self, user_id: str, title: str, original_filename: Optional[str] = None) -> Dict[str, Any]:
        """Cria um novo projeto"""
        data = {
            "user_id": user_id,
            "title": title,
            "original_filename": original_filename,
            "status": "created"
        }
        result = self.client.table("projects").insert(data).execute()
        return result.data[0] if result.data else None
    
    async def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Busca projeto por ID"""
        result = self.client.table("projects").select("*").eq("id", project_id).execute()
        return result.data[0] if result.data else None
    
    async def get_user_projects(self, user_id: str) -> List[Dict[str, Any]]:
        """Lista projetos do usuário"""
        result = self.client.table("projects")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .execute()
        return result.data or []
    
    async def update_project_status(self, project_id: str, status: str, error_message: Optional[str] = None) -> bool:
        """Atualiza status do projeto"""
        data = {"status": status}
        if error_message:
            data["error_message"] = error_message
        result = self.client.table("projects").update(data).eq("id", project_id).execute()
        return len(result.data) > 0
    
    async def delete_project(self, project_id: str) -> bool:
        """Deleta projeto (cascade deleta uploads, structures, renditions)"""
        result = self.client.table("projects").delete().eq("id", project_id).execute()
        return len(result.data) > 0
    
    # =========================================================================
    # UPLOADS
    # =========================================================================
    
    async def create_upload(
        self,
        project_id: str,
        storage_path: str,
        original_filename: str,
        file_size_bytes: int,
        pages_count: Optional[int] = None
    ) -> Dict[str, Any]:
        """Registra upload de PDF"""
        data = {
            "project_id": project_id,
            "storage_path": storage_path,
            "original_filename": original_filename,
            "file_size_bytes": file_size_bytes,
            "pages_count": pages_count
        }
        result = self.client.table("uploads").insert(data).execute()
        return result.data[0] if result.data else None
    
    async def get_project_upload(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Busca upload do projeto"""
        result = self.client.table("uploads")\
            .select("*")\
            .eq("project_id", project_id)\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        return result.data[0] if result.data else None
    
    # =========================================================================
    # BOOK STRUCTURES
    # =========================================================================
    
    async def create_book_structure(
        self,
        project_id: str,
        raw_text: Optional[str] = None,
        raw_html: Optional[str] = None,
        content_json: Optional[Dict] = None,
        extraction_metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Cria estrutura do livro"""
        data = {
            "project_id": project_id,
            "raw_text": raw_text,
            "raw_html": raw_html,
            "content_json": content_json,
            "extraction_metadata": extraction_metadata or {}
        }
        result = self.client.table("book_structures").insert(data).execute()
        return result.data[0] if result.data else None
    
    async def get_book_structure(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Busca estrutura do livro"""
        result = self.client.table("book_structures")\
            .select("*")\
            .eq("project_id", project_id)\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        return result.data[0] if result.data else None
    
    async def update_book_structure(
        self,
        structure_id: str,
        normalized_html: Optional[str] = None,
        content_json: Optional[Dict] = None,
        word_count: Optional[int] = None,
        chapter_count: Optional[int] = None
    ) -> bool:
        """Atualiza estrutura com conteúdo normalizado"""
        data = {}
        if normalized_html is not None:
            data["normalized_html"] = normalized_html
        if content_json is not None:
            data["content_json"] = content_json
        if word_count is not None:
            data["word_count"] = word_count
        if chapter_count is not None:
            data["chapter_count"] = chapter_count
        
        result = self.client.table("book_structures").update(data).eq("id", structure_id).execute()
        return len(result.data) > 0
    
    # =========================================================================
    # TEMPLATES
    # =========================================================================
    
    async def get_templates(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Lista templates disponíveis"""
        query = self.client.table("templates").select("*")
        if active_only:
            query = query.eq("is_active", True)
        result = query.order("sort_order").execute()
        return result.data or []
    
    async def get_template_by_key(self, key: str) -> Optional[Dict[str, Any]]:
        """Busca template por chave"""
        result = self.client.table("templates")\
            .select("*")\
            .eq("key", key)\
            .eq("is_active", True)\
            .execute()
        return result.data[0] if result.data else None
    
    # =========================================================================
    # RENDITIONS
    # =========================================================================
    
    async def create_rendition(
        self,
        project_id: str,
        template_id: str,
        status: str = "pending"
    ) -> Dict[str, Any]:
        """Cria nova rendition"""
        # Marca renditions anteriores como não-current
        self.client.table("renditions")\
            .update({"is_current": False})\
            .eq("project_id", project_id)\
            .execute()
        
        data = {
            "project_id": project_id,
            "template_id": template_id,
            "status": status,
            "is_current": True
        }
        result = self.client.table("renditions").insert(data).execute()
        return result.data[0] if result.data else None
    
    async def get_current_rendition(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Busca rendition atual do projeto"""
        result = self.client.table("renditions")\
            .select("*, templates(*)")\
            .eq("project_id", project_id)\
            .eq("is_current", True)\
            .execute()
        return result.data[0] if result.data else None
    
    async def update_rendition(
        self,
        rendition_id: str,
        status: Optional[str] = None,
        preview_html_path: Optional[str] = None,
        final_pdf_path: Optional[str] = None,
        page_count: Optional[int] = None,
        file_size_bytes: Optional[int] = None,
        render_duration_ms: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """Atualiza rendition"""
        data = {}
        if status:
            data["status"] = status
        if preview_html_path:
            data["preview_html_path"] = preview_html_path
        if final_pdf_path:
            data["final_pdf_path"] = final_pdf_path
        if page_count:
            data["page_count"] = page_count
        if file_size_bytes:
            data["file_size_bytes"] = file_size_bytes
        if render_duration_ms:
            data["render_duration_ms"] = render_duration_ms
        if error_message:
            data["error_message"] = error_message
        if status == "approved":
            data["approved_at"] = datetime.utcnow().isoformat()
        
        result = self.client.table("renditions").update(data).eq("id", rendition_id).execute()
        return len(result.data) > 0
    
    async def get_project_renditions(self, project_id: str) -> List[Dict[str, Any]]:
        """Lista todas renditions do projeto"""
        result = self.client.table("renditions")\
            .select("*, templates(key, name)")\
            .eq("project_id", project_id)\
            .order("created_at", desc=True)\
            .execute()
        return result.data or []
    
    # =========================================================================
    # AI LOGS
    # =========================================================================
    
    async def log_ai_interaction(
        self,
        project_id: Optional[str],
        step: str,
        request_summary: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        success: bool = True,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None
    ) -> None:
        """Registra log de interação com IA"""
        data = {
            "project_id": project_id,
            "step": step,
            "request_summary": request_summary[:500] if request_summary else None,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "success": success,
            "error_message": error_message,
            "duration_ms": duration_ms
        }
        try:
            self.client.table("logs_ai").insert(data).execute()
        except Exception as e:
            logger.error(f"Failed to log AI interaction: {e}")


# Instância lazy (não conecta na importação)
_db_instance: Optional[DatabaseService] = None

def get_db() -> DatabaseService:
    """Retorna instância singleton do DatabaseService"""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseService()
    return _db_instance


class _LazyDB:
    """Wrapper lazy para DatabaseService"""
    def __getattr__(self, name):
        return getattr(get_db(), name)

# Exportar como 'db' para manter compatibilidade
db = _LazyDB()
