"""
BookFlow - Rotas de Projetos
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.services.db import db
from app.routes.auth import get_current_user, UserInfo

router = APIRouter(prefix="/projects", tags=["projects"])


# =============================================================================
# SCHEMAS
# =============================================================================

class ProjectCreate(BaseModel):
    title: str
    
class ProjectResponse(BaseModel):
    id: str
    title: str
    original_filename: Optional[str]
    status: str
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

class ProjectListResponse(BaseModel):
    projects: List[ProjectResponse]
    total: int

class ProjectDetailResponse(ProjectResponse):
    upload: Optional[dict] = None
    current_rendition: Optional[dict] = None
    structure_stats: Optional[dict] = None


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    user: UserInfo = Depends(get_current_user)
):
    """
    Cria um novo projeto de livro
    """
    project = await db.create_project(
        user_id=user.id,
        title=data.title
    )
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create project"
        )
    
    return ProjectResponse(**project)


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    user: UserInfo = Depends(get_current_user)
):
    """
    Lista todos os projetos do usuário
    """
    projects = await db.get_user_projects(user.id)
    
    return ProjectListResponse(
        projects=[ProjectResponse(**p) for p in projects],
        total=len(projects)
    )


@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(
    project_id: str,
    user: UserInfo = Depends(get_current_user)
):
    """
    Obtém detalhes de um projeto
    """
    project = await db.get_project(project_id)
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Verificar propriedade
    if project["user_id"] != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this project"
        )
    
    # Buscar dados relacionados
    upload = await db.get_project_upload(project_id)
    current_rendition = await db.get_current_rendition(project_id)
    structure = await db.get_book_structure(project_id)
    
    structure_stats = None
    if structure:
        structure_stats = {
            "word_count": structure.get("word_count"),
            "chapter_count": structure.get("chapter_count"),
            "image_count": structure.get("image_count")
        }
    
    return ProjectDetailResponse(
        **project,
        upload=upload,
        current_rendition=current_rendition,
        structure_stats=structure_stats
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    user: UserInfo = Depends(get_current_user)
):
    """
    Deleta um projeto e todos os arquivos associados
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
            detail="Not authorized to delete this project"
        )
    
    # Deletar arquivos do storage
    from app.services.storage_client import storage
    await storage.delete_project_files(user.id, project_id)
    
    # Deletar do banco (cascade deleta relacionados)
    success = await db.delete_project(project_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete project"
        )
    
    return None


@router.get("/{project_id}/renditions")
async def list_renditions(
    project_id: str,
    user: UserInfo = Depends(get_current_user)
):
    """
    Lista todas as versões renderizadas do projeto
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
    
    renditions = await db.get_project_renditions(project_id)
    
    return {"renditions": renditions}
