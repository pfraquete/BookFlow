"""
BookFlow - Rotas de Upload
"""
import os
import tempfile
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, status
from pydantic import BaseModel
from typing import Optional

from app.config import get_settings, ProjectStatus
from app.services.db import db
from app.services.storage_client import upload_original_pdf
from app.services.pdf_extractor import extract_pdf
from app.services.structure_normalizer_ai import normalize_book_structure
from app.routes.auth import get_current_user, UserInfo

router = APIRouter(prefix="/projects/{project_id}", tags=["upload"])

# settings carregado quando necessário


# =============================================================================
# SCHEMAS
# =============================================================================

class UploadResponse(BaseModel):
    success: bool
    message: str
    upload_id: Optional[str] = None
    pages_count: Optional[int] = None
    status: str


class ProcessingStatusResponse(BaseModel):
    project_id: str
    status: str
    message: str
    progress: Optional[int] = None
    error: Optional[str] = None


# =============================================================================
# BACKGROUND TASKS
# =============================================================================

async def process_pdf_pipeline(
    project_id: str,
    user_id: str,
    pdf_path: str,
    original_filename: str
):
    """
    Pipeline de processamento do PDF em background
    
    1. Extrai conteúdo do PDF
    2. Salva estrutura bruta
    3. Normaliza com IA
    4. Atualiza status
    """
    try:
        # Atualizar status: extraindo
        await db.update_project_status(project_id, ProjectStatus.EXTRACTING)
        
        # 1. Extrair conteúdo do PDF
        content_json, raw_html = extract_pdf(pdf_path)
        
        # Atualizar status: parsed
        await db.update_project_status(project_id, ProjectStatus.PARSED)
        
        # 2. Salvar estrutura bruta
        structure = await db.create_book_structure(
            project_id=project_id,
            raw_html=raw_html,
            content_json=content_json,
            extraction_metadata={
                "original_filename": original_filename,
                "extractor_version": "1.0"
            }
        )
        
        # Atualizar status: normalizando
        await db.update_project_status(project_id, ProjectStatus.NORMALIZING)
        
        # 3. Normalizar com IA
        normalized_json, normalized_html, error = await normalize_book_structure(
            raw_html=raw_html,
            content_json=content_json,
            project_id=project_id
        )
        
        if error:
            # Falha na normalização, mas mantém o conteúdo bruto
            await db.update_project_status(
                project_id, 
                ProjectStatus.PARSED,
                error_message=f"AI normalization failed: {error}"
            )
            return
        
        # 4. Atualizar estrutura com conteúdo normalizado
        word_count = normalized_json.get("metadata", {}).get("word_count", 0)
        chapter_count = len(normalized_json.get("chapters", []))
        
        await db.update_book_structure(
            structure_id=structure["id"],
            normalized_html=normalized_html,
            content_json=normalized_json,
            word_count=word_count,
            chapter_count=chapter_count
        )
        
        # 5. Atualizar projeto com título detectado
        if normalized_json.get("title"):
            await db.client.table("projects").update({
                "title": normalized_json["title"]
            }).eq("id", project_id).execute()
        
        # Status final: normalizado e pronto para template
        await db.update_project_status(project_id, ProjectStatus.NORMALIZED)
        
    except Exception as e:
        await db.update_project_status(
            project_id,
            ProjectStatus.ERROR,
            error_message=str(e)
        )
    finally:
        # Limpar arquivo temporário
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(
    project_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: UserInfo = Depends(get_current_user)
):
    """
    Upload de PDF para processamento
    
    O arquivo é salvo no storage e o processamento é iniciado em background.
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
    
    # Validar arquivo
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )
    
    # Ler arquivo
    file_data = await file.read()
    file_size = len(file_data)
    
    # Verificar tamanho
    settings = get_settings()
    max_size = settings.UPLOAD_MAX_SIZE_MB * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {settings.UPLOAD_MAX_SIZE_MB}MB"
        )
    
    # Salvar temporariamente para processamento
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        tmp.write(file_data)
        temp_path = tmp.name
    
    # Contar páginas rapidamente
    import fitz
    try:
        doc = fitz.open(temp_path)
        pages_count = len(doc)
        doc.close()
    except:
        pages_count = None
    
    # Upload para storage
    storage_path, error = await upload_original_pdf(
        file_data=file_data,
        user_id=user.id,
        project_id=project_id,
        filename=file.filename
    )
    
    if error:
        os.unlink(temp_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {error}"
        )
    
    # Registrar upload no banco
    upload_record = await db.create_upload(
        project_id=project_id,
        storage_path=storage_path,
        original_filename=file.filename,
        file_size_bytes=file_size,
        pages_count=pages_count
    )
    
    # Atualizar status do projeto
    await db.update_project_status(project_id, ProjectStatus.UPLOADED)
    
    # Atualizar nome do arquivo no projeto
    await db.client.table("projects").update({
        "original_filename": file.filename
    }).eq("id", project_id).execute()
    
    # Iniciar processamento em background
    background_tasks.add_task(
        process_pdf_pipeline,
        project_id=project_id,
        user_id=user.id,
        pdf_path=temp_path,
        original_filename=file.filename
    )
    
    return UploadResponse(
        success=True,
        message="Upload successful. Processing started.",
        upload_id=upload_record["id"] if upload_record else None,
        pages_count=pages_count,
        status=ProjectStatus.UPLOADED
    )


@router.get("/status", response_model=ProcessingStatusResponse)
async def get_processing_status(
    project_id: str,
    user: UserInfo = Depends(get_current_user)
):
    """
    Verifica o status de processamento do projeto
    """
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
    
    # Mapear status para mensagem amigável e progresso
    status_messages = {
        ProjectStatus.CREATED: ("Projeto criado", 0),
        ProjectStatus.UPLOADED: ("PDF enviado, aguardando processamento", 10),
        ProjectStatus.EXTRACTING: ("Extraindo conteúdo do PDF...", 30),
        ProjectStatus.PARSED: ("Conteúdo extraído, analisando estrutura", 50),
        ProjectStatus.NORMALIZING: ("IA normalizando estrutura do livro...", 70),
        ProjectStatus.NORMALIZED: ("Pronto para escolher template", 100),
        ProjectStatus.TEMPLATED: ("Template aplicado", 100),
        ProjectStatus.APPROVED: ("Diagramação aprovada", 100),
        ProjectStatus.EXPORTING: ("Gerando PDF final...", 90),
        ProjectStatus.EXPORTED: ("PDF exportado com sucesso", 100),
        ProjectStatus.ERROR: ("Erro no processamento", 0),
    }
    
    current_status = project["status"]
    message, progress = status_messages.get(current_status, ("Status desconhecido", 0))
    
    return ProcessingStatusResponse(
        project_id=project_id,
        status=current_status,
        message=message,
        progress=progress,
        error=project.get("error_message")
    )
