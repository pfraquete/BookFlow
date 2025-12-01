"""
BookFlow - Cliente de Storage (Supabase Storage)
Gerencia upload e download de arquivos no Supabase Storage
"""
import os
import uuid
from pathlib import Path
from typing import Optional, Tuple, BinaryIO
from datetime import datetime, timedelta
import logging

from supabase import create_client, Client

from app.config import get_settings

logger = logging.getLogger(__name__)


class StorageClient:
    """Cliente para Supabase Storage"""

    BUCKET_UPLOADS = "uploads"      # PDFs originais
    BUCKET_PREVIEWS = "previews"    # HTMLs de preview
    BUCKET_EXPORTS = "exports"      # PDFs finais

    def __init__(self):
        settings = get_settings()
        if settings.validate_supabase():
            self.client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_ROLE_KEY
            )
        else:
            self.client = None
            logger.warning("Supabase not configured. Storage operations will fail.")
    
    def _generate_path(self, user_id: str, project_id: str, filename: str, bucket: str) -> str:
        """Gera path único para arquivo"""
        # Formato: user_id/project_id/timestamp_filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = filename.replace(" ", "_")
        return f"{user_id}/{project_id}/{timestamp}_{safe_filename}"
    
    async def upload_pdf(
        self,
        file_data: bytes,
        user_id: str,
        project_id: str,
        original_filename: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Upload de PDF original
        
        Args:
            file_data: Bytes do arquivo
            user_id: ID do usuário
            project_id: ID do projeto
            original_filename: Nome original do arquivo
            
        Returns:
            Tuple[storage_path, error_message]
        """
        try:
            path = self._generate_path(user_id, project_id, original_filename, self.BUCKET_UPLOADS)
            
            result = self.client.storage.from_(self.BUCKET_UPLOADS).upload(
                path,
                file_data,
                {
                    "content-type": "application/pdf",
                    "x-upsert": "false"
                }
            )
            
            logger.info(f"PDF uploaded: {path}")
            return path, None
            
        except Exception as e:
            logger.error(f"PDF upload failed: {e}")
            return None, str(e)
    
    async def upload_preview_html(
        self,
        html_content: str,
        user_id: str,
        project_id: str,
        template_key: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Upload de HTML de preview
        
        Args:
            html_content: Conteúdo HTML
            user_id: ID do usuário
            project_id: ID do projeto
            template_key: Chave do template usado
            
        Returns:
            Tuple[storage_path, error_message]
        """
        try:
            filename = f"preview_{template_key}.html"
            path = self._generate_path(user_id, project_id, filename, self.BUCKET_PREVIEWS)
            
            result = self.client.storage.from_(self.BUCKET_PREVIEWS).upload(
                path,
                html_content.encode('utf-8'),
                {
                    "content-type": "text/html; charset=utf-8",
                    "x-upsert": "true"
                }
            )
            
            logger.info(f"Preview HTML uploaded: {path}")
            return path, None
            
        except Exception as e:
            logger.error(f"Preview HTML upload failed: {e}")
            return None, str(e)
    
    async def upload_final_pdf(
        self,
        pdf_path: str,
        user_id: str,
        project_id: str,
        book_title: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Upload de PDF final gerado
        
        Args:
            pdf_path: Caminho local do PDF
            user_id: ID do usuário
            project_id: ID do projeto
            book_title: Título do livro
            
        Returns:
            Tuple[storage_path, error_message]
        """
        try:
            # Sanitizar título para nome de arquivo
            safe_title = "".join(c for c in book_title if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_title = safe_title[:50] if safe_title else "book"
            filename = f"{safe_title}.pdf"
            
            path = self._generate_path(user_id, project_id, filename, self.BUCKET_EXPORTS)
            
            with open(pdf_path, 'rb') as f:
                pdf_data = f.read()
            
            result = self.client.storage.from_(self.BUCKET_EXPORTS).upload(
                path,
                pdf_data,
                {
                    "content-type": "application/pdf",
                    "x-upsert": "false"
                }
            )
            
            logger.info(f"Final PDF uploaded: {path}")
            return path, None
            
        except Exception as e:
            logger.error(f"Final PDF upload failed: {e}")
            return None, str(e)
    
    async def download_file(
        self,
        bucket: str,
        path: str
    ) -> Tuple[Optional[bytes], Optional[str]]:
        """
        Download de arquivo do storage
        
        Args:
            bucket: Nome do bucket
            path: Caminho do arquivo
            
        Returns:
            Tuple[file_data, error_message]
        """
        try:
            result = self.client.storage.from_(bucket).download(path)
            return result, None
            
        except Exception as e:
            logger.error(f"File download failed: {e}")
            return None, str(e)
    
    def get_public_url(self, bucket: str, path: str) -> str:
        """
        Obtém URL pública do arquivo
        
        Args:
            bucket: Nome do bucket
            path: Caminho do arquivo
            
        Returns:
            URL pública
        """
        return self.client.storage.from_(bucket).get_public_url(path)
    
    def get_signed_url(
        self,
        bucket: str,
        path: str,
        expires_in: int = 3600
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Obtém URL assinada temporária
        
        Args:
            bucket: Nome do bucket
            path: Caminho do arquivo
            expires_in: Tempo de expiração em segundos
            
        Returns:
            Tuple[signed_url, error_message]
        """
        try:
            result = self.client.storage.from_(bucket).create_signed_url(path, expires_in)
            return result.get('signedURL'), None
            
        except Exception as e:
            logger.error(f"Failed to create signed URL: {e}")
            return None, str(e)
    
    async def delete_file(self, bucket: str, path: str) -> bool:
        """
        Deleta arquivo do storage
        
        Args:
            bucket: Nome do bucket
            path: Caminho do arquivo
            
        Returns:
            True se deletado com sucesso
        """
        try:
            self.client.storage.from_(bucket).remove([path])
            return True
        except Exception as e:
            logger.error(f"Failed to delete file: {e}")
            return False
    
    async def delete_project_files(self, user_id: str, project_id: str) -> int:
        """
        Deleta todos os arquivos de um projeto
        
        Args:
            user_id: ID do usuário
            project_id: ID do projeto
            
        Returns:
            Número de arquivos deletados
        """
        deleted = 0
        prefix = f"{user_id}/{project_id}/"
        
        for bucket in [self.BUCKET_UPLOADS, self.BUCKET_PREVIEWS, self.BUCKET_EXPORTS]:
            try:
                # Listar arquivos no bucket
                files = self.client.storage.from_(bucket).list(prefix)
                
                if files:
                    paths = [f"{prefix}{f['name']}" for f in files]
                    self.client.storage.from_(bucket).remove(paths)
                    deleted += len(paths)
                    
            except Exception as e:
                logger.warning(f"Failed to delete files from {bucket}: {e}")
        
        return deleted


# Instância lazy
_storage_instance: Optional[StorageClient] = None

def get_storage() -> StorageClient:
    """Retorna instância singleton do StorageClient"""
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = StorageClient()
    return _storage_instance


class _LazyStorage:
    """Wrapper lazy para StorageClient"""
    def __getattr__(self, name):
        return getattr(get_storage(), name)

storage = _LazyStorage()


# Funções de conveniência
async def upload_original_pdf(file_data: bytes, user_id: str, project_id: str, filename: str) -> Tuple[Optional[str], Optional[str]]:
    """Upload de PDF original"""
    return await storage.upload_pdf(file_data, user_id, project_id, filename)


async def upload_preview(html: str, user_id: str, project_id: str, template_key: str) -> Tuple[Optional[str], Optional[str]]:
    """Upload de preview HTML"""
    return await storage.upload_preview_html(html, user_id, project_id, template_key)


async def upload_export(pdf_path: str, user_id: str, project_id: str, title: str) -> Tuple[Optional[str], Optional[str]]:
    """Upload de PDF exportado"""
    return await storage.upload_final_pdf(pdf_path, user_id, project_id, title)


def get_download_url(bucket: str, path: str, expires_in: int = 3600) -> Tuple[Optional[str], Optional[str]]:
    """Obtém URL de download"""
    return storage.get_signed_url(bucket, path, expires_in)
