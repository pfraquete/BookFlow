"""
BookFlow - Rotas de Preview e Templates
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
import time

from app.config import get_settings, ProjectStatus, RenditionStatus, TEMPLATE_KEYS
from app.services.db import db
from app.services.template_engine import template_engine, apply_book_template
from app.services.storage_client import storage, upload_preview
from app.routes.auth import get_current_user, UserInfo

router = APIRouter(prefix="/projects/{project_id}", tags=["preview"])

# settings carregado quando necessário


# =============================================================================
# SCHEMAS
# =============================================================================

class TemplateInfo(BaseModel):
    key: str
    name: str
    description: str
    category: str
    preview_thumbnail_url: Optional[str] = None

class TemplateListResponse(BaseModel):
    templates: List[TemplateInfo]

class ApplyTemplateRequest(BaseModel):
    template_key: str

class ApplyTemplateResponse(BaseModel):
    success: bool
    message: str
    rendition_id: Optional[str] = None
    preview_url: Optional[str] = None

class PreviewResponse(BaseModel):
    project_id: str
    template_key: str
    template_name: str
    preview_html: Optional[str] = None
    preview_url: Optional[str] = None
    page_count: Optional[int] = None
    word_count: Optional[int] = None


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/preview-templates", response_model=TemplateListResponse)
async def list_templates(
    project_id: str,
    user: UserInfo = Depends(get_current_user)
):
    """
    Lista templates de diagramação disponíveis
    """
    # Verificar projeto
    project = await db.get_project(project_id)
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    if project["user_id"] != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )
    
    # Buscar templates do banco
    templates_db = await db.get_templates()
    
    # Se não houver templates no banco, usar os hardcoded
    if not templates_db:
        templates_info = template_engine.get_available_templates()
    else:
        templates_info = [
            {
                "key": t["key"],
                "name": t["name"],
                "description": t["description"],
                "category": t.get("category", "general"),
                "preview_thumbnail_url": t.get("preview_thumbnail_url")
            }
            for t in templates_db
        ]
    
    return TemplateListResponse(
        templates=[TemplateInfo(**t) for t in templates_info]
    )


@router.post("/apply-template", response_model=ApplyTemplateResponse)
async def apply_template(
    project_id: str,
    data: ApplyTemplateRequest,
    user: UserInfo = Depends(get_current_user)
):
    """
    Aplica um template de diagramação ao livro
    """
    # Verificar projeto
    project = await db.get_project(project_id)
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    if project["user_id"] != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )
    
    # Verificar se projeto está pronto para template
    valid_statuses = [ProjectStatus.PARSED, ProjectStatus.NORMALIZED, ProjectStatus.TEMPLATED]
    if project["status"] not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project must be in one of these statuses to apply template: {valid_statuses}. Current: {project['status']}"
        )
    
    # Validar template
    if data.template_key not in TEMPLATE_KEYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid template. Available: {TEMPLATE_KEYS}"
        )
    
    # Buscar estrutura do livro
    structure = await db.get_book_structure(project_id)
    
    if not structure:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Book structure not found. Please upload a PDF first."
        )
    
    # Usar conteúdo normalizado se disponível, senão o bruto
    content_json = structure.get("content_json")
    if not content_json:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Book content not processed yet"
        )
    
    # Buscar template do banco para config
    template_db = await db.get_template_by_key(data.template_key)
    template_config = template_db.get("config") if template_db else None
    
    try:
        # Aplicar template
        preview_html = apply_book_template(
            content_json=content_json,
            template_key=data.template_key,
            template_config=template_config
        )
        
        # Upload do preview HTML
        preview_path, error = await upload_preview(
            html=preview_html,
            user_id=user.id,
            project_id=project_id,
            template_key=data.template_key
        )
        
        if error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save preview: {error}"
            )
        
        # Obter ID do template
        template_id = template_db["id"] if template_db else None
        
        # Se não tiver template no banco, criar um temporário
        if not template_id:
            # Usar um ID fixo baseado na key
            template_result = await db.client.table("templates").select("id").eq("key", data.template_key).execute()
            if template_result.data:
                template_id = template_result.data[0]["id"]
        
        # Criar rendition
        rendition = await db.create_rendition(
            project_id=project_id,
            template_id=template_id,
            status=RenditionStatus.PREVIEW_GENERATED
        )
        
        # Atualizar rendition com path do preview
        await db.update_rendition(
            rendition_id=rendition["id"],
            preview_html_path=preview_path,
            status=RenditionStatus.PREVIEW_GENERATED
        )
        
        # Atualizar status do projeto
        await db.update_project_status(project_id, ProjectStatus.TEMPLATED)
        
        # Gerar URL de preview
        preview_url, _ = storage.get_signed_url(
            storage.BUCKET_PREVIEWS,
            preview_path,
            expires_in=3600
        )
        
        return ApplyTemplateResponse(
            success=True,
            message=f"Template '{data.template_key}' applied successfully",
            rendition_id=rendition["id"],
            preview_url=preview_url
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply template: {str(e)}"
        )


@router.get("/preview", response_model=PreviewResponse)
async def get_preview(
    project_id: str,
    user: UserInfo = Depends(get_current_user)
):
    """
    Obtém preview da diagramação atual
    """
    # Verificar projeto
    project = await db.get_project(project_id)
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    if project["user_id"] != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )
    
    # Buscar rendition atual
    rendition = await db.get_current_rendition(project_id)
    
    if not rendition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No preview available. Apply a template first."
        )
    
    # Buscar estrutura para estatísticas
    structure = await db.get_book_structure(project_id)
    
    # Obter URL do preview
    preview_url = None
    if rendition.get("preview_html_path"):
        preview_url, _ = storage.get_signed_url(
            storage.BUCKET_PREVIEWS,
            rendition["preview_html_path"],
            expires_in=3600
        )
    
    template_info = rendition.get("templates", {})
    
    return PreviewResponse(
        project_id=project_id,
        template_key=template_info.get("key", "unknown"),
        template_name=template_info.get("name", "Unknown Template"),
        preview_url=preview_url,
        page_count=rendition.get("page_count"),
        word_count=structure.get("word_count") if structure else None
    )


@router.get("/preview/html", response_class=HTMLResponse)
async def get_preview_html(
    project_id: str,
    user: UserInfo = Depends(get_current_user)
):
    """
    Retorna o HTML do preview diretamente (para iframe)
    """
    # Verificar projeto
    project = await db.get_project(project_id)
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    if project["user_id"] != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized"
        )
    
    # Buscar rendition atual
    rendition = await db.get_current_rendition(project_id)
    
    if not rendition or not rendition.get("preview_html_path"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No preview available"
        )
    
    # Baixar HTML do storage
    html_data, error = await storage.download_file(
        storage.BUCKET_PREVIEWS,
        rendition["preview_html_path"]
    )
    
    if error or not html_data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load preview: {error}"
        )
    
    return HTMLResponse(content=html_data.decode('utf-8'))
