"""
BookFlow - Serviço de Renderização de PDF
Usa WeasyPrint para gerar PDF final a partir do HTML diagramado
"""
import os
import time
import tempfile
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

try:
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration
    WEASYPRINT_AVAILABLE = True
except OSError:
    WEASYPRINT_AVAILABLE = False
    HTML = None
    CSS = None
    FontConfiguration = None
    logger.warning("WeasyPrint system dependencies not found. PDF rendering will be disabled.")

from app.config import get_settings



@dataclass
class RenderResult:
    """Resultado da renderização"""
    success: bool
    pdf_path: Optional[str] = None
    page_count: Optional[int] = None
    file_size_bytes: Optional[int] = None
    duration_ms: int = 0
    error_message: Optional[str] = None


class PDFRenderer:
    """Renderiza HTML em PDF usando WeasyPrint"""
    
    def __init__(self):
        settings = get_settings()
        if WEASYPRINT_AVAILABLE:
            self.font_config = FontConfiguration()
        else:
            self.font_config = None
        self.temp_dir = Path(settings.TEMP_DIR)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def render(
        self,
        html_content: str,
        output_filename: Optional[str] = None,
        base_url: Optional[str] = None
    ) -> RenderResult:
        """
        Renderiza HTML em PDF
        
        Args:
            html_content: Conteúdo HTML completo
            output_filename: Nome do arquivo de saída (opcional)
            base_url: URL base para resolver recursos relativos
            
        Returns:
            RenderResult com informações do PDF gerado
        """
        start_time = time.time()
        
        try:
            # Gerar nome de arquivo se não fornecido
            if not output_filename:
                output_filename = f"book_{int(time.time())}.pdf"
            
            output_path = self.temp_dir / output_filename
            
            # Criar documento HTML
            html_doc = HTML(
                string=html_content,
                base_url=base_url or str(self.temp_dir),
            )
            
            # Renderizar PDF
            pdf_doc = html_doc.render(font_config=self.font_config)
            
            # Obter número de páginas
            page_count = len(pdf_doc.pages)
            
            # Escrever PDF
            pdf_doc.write_pdf(str(output_path))
            
            # Obter tamanho do arquivo
            file_size = output_path.stat().st_size
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            logger.info(f"PDF rendered: {output_path}, {page_count} pages, {file_size} bytes, {duration_ms}ms")
            
            return RenderResult(
                success=True,
                pdf_path=str(output_path),
                page_count=page_count,
                file_size_bytes=file_size,
                duration_ms=duration_ms
            )
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"PDF render failed: {e}")
            
            return RenderResult(
                success=False,
                error_message=str(e),
                duration_ms=duration_ms
            )
    
    def render_from_file(
        self,
        html_path: str,
        output_filename: Optional[str] = None
    ) -> RenderResult:
        """
        Renderiza PDF a partir de arquivo HTML
        
        Args:
            html_path: Caminho para o arquivo HTML
            output_filename: Nome do arquivo de saída
            
        Returns:
            RenderResult com informações do PDF gerado
        """
        start_time = time.time()
        
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            base_url = str(Path(html_path).parent)
            
            return self.render(html_content, output_filename, base_url)
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Failed to read HTML file: {e}")
            
            return RenderResult(
                success=False,
                error_message=str(e),
                duration_ms=duration_ms
            )
    
    def render_preview_pages(
        self,
        html_content: str,
        start_page: int = 1,
        num_pages: int = 5
    ) -> Tuple[Optional[bytes], Optional[int], Optional[str]]:
        """
        Renderiza apenas algumas páginas para preview
        
        Args:
            html_content: Conteúdo HTML
            start_page: Página inicial (1-indexed)
            num_pages: Número de páginas a renderizar
            
        Returns:
            Tuple[pdf_bytes, total_pages, error_message]
        """
        try:
            if not WEASYPRINT_AVAILABLE:
                return None, None, "WeasyPrint dependencies not installed"
            html_doc = HTML(string=html_content)
            pdf_doc = html_doc.render(font_config=self.font_config)
            
            total_pages = len(pdf_doc.pages)
            
            # Limitar páginas ao range válido
            start_idx = max(0, start_page - 1)
            end_idx = min(total_pages, start_idx + num_pages)
            
            # WeasyPrint não suporta renderização parcial diretamente
            # Renderizamos tudo e retornamos info de páginas
            pdf_bytes = pdf_doc.write_pdf()
            
            return pdf_bytes, total_pages, None
            
        except Exception as e:
            logger.error(f"Preview render failed: {e}")
            return None, None, str(e)
    
    def cleanup_temp_files(self, max_age_hours: int = 24) -> int:
        """
        Limpa arquivos temporários antigos
        
        Args:
            max_age_hours: Idade máxima em horas
            
        Returns:
            Número de arquivos removidos
        """
        import time
        
        removed = 0
        max_age_seconds = max_age_hours * 3600
        current_time = time.time()
        
        for file_path in self.temp_dir.glob("*.pdf"):
            try:
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age_seconds:
                    file_path.unlink()
                    removed += 1
            except Exception as e:
                logger.warning(f"Failed to remove temp file {file_path}: {e}")
        
        return removed


# CSS adicional para impressão
PRINT_CSS = """
@media print {
    body {
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }
    
    .chapter {
        page-break-before: always;
    }
    
    .chapter:first-of-type {
        page-break-before: avoid;
    }
    
    h1, h2, h3, h4, h5, h6 {
        page-break-after: avoid;
    }
    
    p, blockquote, ul, ol {
        orphans: 3;
        widows: 3;
    }
    
    img {
        page-break-inside: avoid;
    }
}
"""


# Instância lazy
_pdf_renderer_instance: Optional[PDFRenderer] = None

def get_pdf_renderer() -> PDFRenderer:
    global _pdf_renderer_instance
    if _pdf_renderer_instance is None:
        _pdf_renderer_instance = PDFRenderer()
    return _pdf_renderer_instance


def render_book_pdf(
    html_content: str,
    output_filename: Optional[str] = None
) -> Tuple[Optional[str], Optional[int], Optional[int], Optional[str]]:
    """
    Função de conveniência para renderizar PDF
    
    Returns:
        Tuple[pdf_path, page_count, file_size, error_message]
    """
    result = get_pdf_renderer().render(html_content, output_filename)
    
    if result.success:
        return result.pdf_path, result.page_count, result.file_size_bytes, None
    else:
        return None, None, None, result.error_message
