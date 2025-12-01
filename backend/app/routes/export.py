"""
BookFlow - Rotas de Export (Geração de PDF Final)
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from pydantic import BaseModel
from typing import Optional
import time

from app.config import get_settings, ProjectStatus, RenditionStatus
from app.services.db import db
from app.services.storage_client import storage, upload_export
from app.services.pdf_renderer import render_book_pdf
from app.routes.auth import get_current_user, UserInfo

router = APIRouter(prefix="/projects/{project_id}", tags=["export"])

# settings carregado quando necessário


# =============================================================================
# SCHEMAS
# =============================================================================

class ApproveResponse(BaseModel):
    success: bool
    message: str
    status: str
    download_url: Optional[str] = None
    page_count: Optional[int] = None
    file_size_bytes: Optional[int] = None

class ExportStatusResponse(BaseModel):
    project_id: str
    status: str
    message: str
    download_url: Optional[str] = None
    page_count: Optional[int] = None
    file_size_bytes: Optional[int] = None


# =============================================================================
# BACKGROUND TASKS
# =============================================================================

async def generate_pdf_task(
    project_id: str,
    user_id: str,
    rendition_id: str,
    preview_html_path: str,
    book_title: str
):
    """
    Gera PDF final em background
    """
    start_time = time.time()
    
    try:
        # Baixar HTML do storage
        html_data, error = await storage.download_file(
            storage.BUCKET_PREVIEWS,
            preview_html_path
        )
        
        if error or not html_data:
            raise Exception(f"Failed to load preview HTML: {error}")
        
        html_content = html_data.decode('utf-8')
        
        # Renderizar PDF
        pdf_path, page_count, file_size, error = render_book_pdf(html_content)
        
        if error:
            raise Exception(f"PDF rendering failed: {error}")
        
        # Upload do PDF final
        storage_path, error = await upload_export(
            pdf_path=pdf_path,
            user_id=user_id,
            project_id=project_id,
            title=book_title
        )
        
        if error:
            raise Exception(f"Failed to upload PDF: {error}")
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Atualizar rendition
        await db.update_rendition(
            rendition_id=rendition_id,
            status=RenditionStatus.PDF_GENERATED,
            final_pdf_path=storage_path,
            page_count=page_count,
            file_size_bytes=file_size,
            render_duration_ms=duration_ms
        )
        
        # Atualizar status do projeto
        await db.update_project_status(project_id, ProjectStatus.EXPORTED)
        
        # Limpar arquivo temporário
        import os
        if pdf_path and os.path.exists(pdf_path):
            os.unlink(pdf_path)
            
    except Exception as e:
        # Atualizar com erro
        await db.update_rendition(
            rendition_id=rendition_id,
            status=RenditionStatus.ERROR,
            error_message=str(e)
        )
        await db.update_project_status(
            project_id,
            ProjectStatus.ERROR,
            error_message=f"PDF export failed: {str(e)}"
        )


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/approve", response_model=ApproveResponse)
async def approve_and_export(
    project_id: str,
    background_tasks: BackgroundTasks,
    user: UserInfo = Depends(get_current_user)
):
    """
    Aprova a diagramação e inicia a geração do PDF final
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
    
    # Verificar status
    if project["status"] not in [ProjectStatus.TEMPLATED, ProjectStatus.APPROVED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project must have a template applied first. Current status: {project['status']}"
        )
    
    # Buscar rendition atual
    rendition = await db.get_current_rendition(project_id)
    
    if not rendition:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No template applied. Apply a template first."
        )
    
    if not rendition.get("preview_html_path"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Preview not generated. Apply a template first."
        )
    
    # Verificar se já está exportando ou exportado
    if rendition["status"] == RenditionStatus.PDF_GENERATING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PDF is already being generated. Please wait."
        )
    
    if rendition["status"] == RenditionStatus.PDF_GENERATED and rendition.get("final_pdf_path"):
        # Já exportado, retornar URL
        download_url, _ = storage.get_signed_url(
            storage.BUCKET_EXPORTS,
            rendition["final_pdf_path"],
            expires_in=86400  # 24 horas
        )
        
        return ApproveResponse(
            success=True,
            message="PDF already generated",
            status=ProjectStatus.EXPORTED,
            download_url=download_url,
            page_count=rendition.get("page_count"),
            file_size_bytes=rendition.get("file_size_bytes")
        )
    
    # Marcar como aprovado e iniciando geração
    await db.update_rendition(
        rendition_id=rendition["id"],
        status=RenditionStatus.PDF_GENERATING
    )
    await db.update_project_status(project_id, ProjectStatus.EXPORTING)
    
    # Iniciar geração em background
    background_tasks.add_task(
        generate_pdf_task,
        project_id=project_id,
        user_id=user.id,
        rendition_id=rendition["id"],
        preview_html_path=rendition["preview_html_path"],
        book_title=project["title"]
    )
    
    return ApproveResponse(
        success=True,
        message="PDF generation started. Check status for download link.",
        status=ProjectStatus.EXPORTING
    )


@router.get("/export-status", response_model=ExportStatusResponse)
async def get_export_status(
    project_id: str,
    user: UserInfo = Depends(get_current_user)
):
    """
    Verifica status da exportação e retorna link de download se pronto
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
        return ExportStatusResponse(
            project_id=project_id,
            status="no_template",
            message="No template applied yet"
        )
    
    # Mapear status para mensagem
    status_messages = {
        RenditionStatus.PENDING: "Awaiting processing",
        RenditionStatus.PREVIEW_GENERATING: "Generating preview...",
        RenditionStatus.PREVIEW_GENERATED: "Preview ready. Approve to generate PDF.",
        RenditionStatus.APPROVED: "Approved. Starting PDF generation...",
        RenditionStatus.PDF_GENERATING: "Generating PDF... This may take a few minutes.",
        RenditionStatus.PDF_GENERATED: "PDF ready for download!",
        RenditionStatus.ERROR: f"Error: {rendition.get('error_message', 'Unknown error')}"
    }
    
    current_status = rendition["status"]
    message = status_messages.get(current_status, "Unknown status")
    
    download_url = None
    if current_status == RenditionStatus.PDF_GENERATED and rendition.get("final_pdf_path"):
        download_url, _ = storage.get_signed_url(
            storage.BUCKET_EXPORTS,
            rendition["final_pdf_path"],
            expires_in=86400  # 24 horas
        )
    
    return ExportStatusResponse(
        project_id=project_id,
        status=current_status,
        message=message,
        download_url=download_url,
        page_count=rendition.get("page_count"),
        file_size_bytes=rendition.get("file_size_bytes")
    )


@router.get("/download")
async def get_download_link(
    project_id: str,
    user: UserInfo = Depends(get_current_user)
):
    """
    Gera link de download temporário para o PDF final
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
    
    if project["status"] != ProjectStatus.EXPORTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PDF not ready yet"
        )
    
    # Buscar rendition
    rendition = await db.get_current_rendition(project_id)
    
    if not rendition or not rendition.get("final_pdf_path"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF not found"
        )
    
    # Gerar URL assinada
    download_url, error = storage.get_signed_url(
        storage.BUCKET_EXPORTS,
        rendition["final_pdf_path"],
        expires_in=86400  # 24 horas
    )
    
    if error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate download link: {error}"
        )
    
    return {
        "download_url": download_url,
        "filename": f"{project['title']}.pdf",
        "expires_in_seconds": 86400,
        "page_count": rendition.get("page_count"),
        "file_size_bytes": rendition.get("file_size_bytes")
    }
