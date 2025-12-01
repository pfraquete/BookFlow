"""
BookFlow - Serviço de Extração de PDF
Converte PDF em HTML estruturado básico usando PyMuPDF
"""
import fitz  # PyMuPDF
import re
import html
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class TextBlock:
    """Representa um bloco de texto extraído"""
    text: str
    font_name: str = ""
    font_size: float = 0.0
    is_bold: bool = False
    is_italic: bool = False
    bbox: Tuple[float, float, float, float] = (0, 0, 0, 0)
    page_num: int = 0
    block_type: str = "paragraph"  # paragraph, heading, quote, list_item, footer


@dataclass
class Chapter:
    """Representa um capítulo do livro"""
    title: str
    level: int = 1  # 1 = h1, 2 = h2, etc
    blocks: List[TextBlock] = field(default_factory=list)
    page_start: int = 0


@dataclass
class BookContent:
    """Estrutura completa do livro extraído"""
    title: str = ""
    author: str = ""
    chapters: List[Chapter] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    total_pages: int = 0
    word_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "author": self.author,
            "chapters": [
                {
                    "title": ch.title,
                    "level": ch.level,
                    "page_start": ch.page_start,
                    "blocks": [asdict(b) for b in ch.blocks]
                }
                for ch in self.chapters
            ],
            "metadata": self.metadata,
            "total_pages": self.total_pages,
            "word_count": self.word_count
        }


class PDFExtractor:
    """Extrai conteúdo estruturado de PDFs"""
    
    # Thresholds para detecção de headings
    HEADING_SIZE_MULTIPLIER = 1.2  # 20% maior que body
    MIN_HEADING_SIZE = 14.0
    
    # Padrões de capítulo
    CHAPTER_PATTERNS = [
        r'^(?:CAPÍTULO|CHAPTER|CAP\.?)\s*[IVXLCDM\d]+[:\.\s]',
        r'^(?:PARTE|PART)\s*[IVXLCDM\d]+[:\.\s]',
        r'^\d+\.\s+[A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇ]',
        r'^[IVXLCDM]+\.\s+[A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇ]',
    ]
    
    def __init__(self):
        self.base_font_size: float = 12.0
        self.page_margins = {"top": 72, "bottom": 72, "left": 72, "right": 72}  # 1 inch
    
    def extract(self, pdf_path: str) -> Tuple[BookContent, str]:
        """
        Extrai conteúdo do PDF
        
        Args:
            pdf_path: Caminho para o arquivo PDF
            
        Returns:
            Tuple[BookContent, str]: Estrutura do livro e HTML básico
        """
        doc = fitz.open(pdf_path)
        
        try:
            content = BookContent(
                total_pages=len(doc),
                metadata=self._extract_metadata(doc)
            )
            
            all_blocks: List[TextBlock] = []
            font_sizes: List[float] = []
            
            # Primeira passada: extrair todos os blocos e calcular font size base
            for page_num in range(len(doc)):
                page = doc[page_num]
                blocks = self._extract_page_blocks(page, page_num)
                all_blocks.extend(blocks)
                
                for block in blocks:
                    if block.font_size > 0:
                        font_sizes.append(block.font_size)
            
            # Calcular font size base (mais comum)
            if font_sizes:
                self.base_font_size = max(set(font_sizes), key=font_sizes.count)
            
            # Segunda passada: classificar blocos
            for block in all_blocks:
                block.block_type = self._classify_block(block)
            
            # Organizar em capítulos
            content.chapters = self._organize_chapters(all_blocks)
            
            # Extrair título do livro (primeiro heading grande ou metadata)
            content.title = self._detect_book_title(content, doc)
            content.author = content.metadata.get("author", "")
            
            # Contar palavras
            content.word_count = sum(
                len(block.text.split())
                for ch in content.chapters
                for block in ch.blocks
            )
            
            # Gerar HTML básico
            raw_html = self._generate_html(content)
            
            return content, raw_html
            
        finally:
            doc.close()
    
    def _extract_metadata(self, doc: fitz.Document) -> Dict[str, Any]:
        """Extrai metadados do PDF"""
        meta = doc.metadata
        return {
            "title": meta.get("title", ""),
            "author": meta.get("author", ""),
            "subject": meta.get("subject", ""),
            "creator": meta.get("creator", ""),
            "producer": meta.get("producer", ""),
            "creation_date": meta.get("creationDate", ""),
            "mod_date": meta.get("modDate", ""),
        }
    
    def _extract_page_blocks(self, page: fitz.Page, page_num: int) -> List[TextBlock]:
        """Extrai blocos de texto de uma página"""
        blocks: List[TextBlock] = []
        page_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
        
        for block in page_dict.get("blocks", []):
            if block.get("type") != 0:  # Não é texto
                continue
            
            for line in block.get("lines", []):
                line_text = ""
                line_fonts = []
                line_sizes = []
                line_flags = []
                
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if text:
                        line_text += text + " "
                        line_fonts.append(span.get("font", ""))
                        line_sizes.append(span.get("size", 0))
                        line_flags.append(span.get("flags", 0))
                
                line_text = line_text.strip()
                if not line_text:
                    continue
                
                # Determinar propriedades predominantes
                font_name = max(set(line_fonts), key=line_fonts.count) if line_fonts else ""
                font_size = max(set(line_sizes), key=line_sizes.count) if line_sizes else 0
                
                # Flags: 1=superscript, 2=italic, 4=serif, 8=monospace, 16=bold
                avg_flags = sum(line_flags) / len(line_flags) if line_flags else 0
                is_bold = avg_flags >= 16 or "bold" in font_name.lower()
                is_italic = (int(avg_flags) & 2) > 0 or "italic" in font_name.lower()
                
                text_block = TextBlock(
                    text=line_text,
                    font_name=font_name,
                    font_size=font_size,
                    is_bold=is_bold,
                    is_italic=is_italic,
                    bbox=tuple(block.get("bbox", [0, 0, 0, 0])),
                    page_num=page_num
                )
                blocks.append(text_block)
        
        return blocks
    
    def _classify_block(self, block: TextBlock) -> str:
        """Classifica o tipo de bloco baseado em características"""
        text = block.text.strip()
        
        # Verificar se é número de página / footer
        if self._is_page_number(text, block):
            return "footer"
        
        # Verificar se é heading
        if self._is_heading(block):
            return "heading"
        
        # Verificar se é citação
        if self._is_quote(text):
            return "quote"
        
        # Verificar se é item de lista
        if self._is_list_item(text):
            return "list_item"
        
        return "paragraph"
    
    def _is_heading(self, block: TextBlock) -> bool:
        """Determina se o bloco é um heading"""
        # Muito pequeno para ser heading
        if len(block.text) < 2 or len(block.text) > 200:
            return False
        
        # Font size significativamente maior
        if block.font_size >= self.base_font_size * self.HEADING_SIZE_MULTIPLIER:
            return True
        
        # Bold e tamanho >= base
        if block.is_bold and block.font_size >= self.base_font_size:
            return True
        
        # Padrão de capítulo
        for pattern in self.CHAPTER_PATTERNS:
            if re.match(pattern, block.text, re.IGNORECASE):
                return True
        
        return False
    
    def _is_page_number(self, text: str, block: TextBlock) -> bool:
        """Verifica se é número de página"""
        # Apenas números
        if re.match(r'^\d{1,4}$', text):
            return True
        # Padrões comuns de paginação
        if re.match(r'^(página|page|pág\.?)\s*\d+', text, re.IGNORECASE):
            return True
        if re.match(r'^\d+\s*(de|of|/)\s*\d+$', text, re.IGNORECASE):
            return True
        return False
    
    def _is_quote(self, text: str) -> bool:
        """Verifica se é citação"""
        # Começa com aspas
        if text.startswith('"') or text.startswith('"') or text.startswith('«'):
            return True
        # Padrão de citação com travessão
        if text.startswith('—') or text.startswith('–'):
            return True
        return False
    
    def _is_list_item(self, text: str) -> bool:
        """Verifica se é item de lista"""
        patterns = [
            r'^\s*[\•\-\*\◦\▪]\s+',  # Bullets
            r'^\s*\d+[\.\)]\s+',  # Numerado
            r'^\s*[a-zA-Z][\.\)]\s+',  # Letras
            r'^\s*[ivxIVX]+[\.\)]\s+',  # Romano
        ]
        for pattern in patterns:
            if re.match(pattern, text):
                return True
        return False
    
    def _organize_chapters(self, blocks: List[TextBlock]) -> List[Chapter]:
        """Organiza blocos em capítulos"""
        chapters: List[Chapter] = []
        current_chapter = Chapter(title="Início", level=1, page_start=0)
        
        for block in blocks:
            if block.block_type == "footer":
                continue
            
            if block.block_type == "heading":
                # Determinar nível do heading
                level = self._get_heading_level(block)
                
                # Se é um novo capítulo principal (h1)
                if level == 1 and current_chapter.blocks:
                    chapters.append(current_chapter)
                    current_chapter = Chapter(
                        title=block.text,
                        level=level,
                        page_start=block.page_num
                    )
                else:
                    # Sub-heading, adicionar como bloco
                    current_chapter.blocks.append(block)
            else:
                current_chapter.blocks.append(block)
        
        # Adicionar último capítulo
        if current_chapter.blocks:
            chapters.append(current_chapter)
        
        return chapters
    
    def _get_heading_level(self, block: TextBlock) -> int:
        """Determina o nível do heading (1-6)"""
        size_ratio = block.font_size / self.base_font_size
        
        if size_ratio >= 2.0:
            return 1
        elif size_ratio >= 1.5:
            return 2
        elif size_ratio >= 1.3:
            return 3
        elif size_ratio >= 1.2 or block.is_bold:
            return 4
        else:
            return 5
    
    def _detect_book_title(self, content: BookContent, doc: fitz.Document) -> str:
        """Detecta o título do livro"""
        # Primeiro tentar metadata
        if content.metadata.get("title"):
            return content.metadata["title"]
        
        # Procurar no primeiro capítulo por heading grande
        if content.chapters:
            first_chapter = content.chapters[0]
            if first_chapter.title and first_chapter.title != "Início":
                return first_chapter.title
            
            for block in first_chapter.blocks[:5]:
                if block.block_type == "heading" and block.font_size >= self.base_font_size * 1.5:
                    return block.text
        
        return "Livro sem título"
    
    def _generate_html(self, content: BookContent) -> str:
        """Gera HTML básico estruturado"""
        html_parts = [
            '<!DOCTYPE html>',
            '<html lang="pt-BR">',
            '<head>',
            '<meta charset="UTF-8">',
            f'<title>{html.escape(content.title)}</title>',
            '</head>',
            '<body>',
            f'<h1 class="book-title">{html.escape(content.title)}</h1>',
        ]
        
        if content.author:
            html_parts.append(f'<p class="book-author">{html.escape(content.author)}</p>')
        
        for chapter in content.chapters:
            html_parts.append(f'<section class="chapter" data-page="{chapter.page_start}">')
            
            if chapter.title and chapter.title != "Início":
                html_parts.append(f'<h{chapter.level} class="chapter-title">{html.escape(chapter.title)}</h{chapter.level}>')
            
            current_list = None
            
            for block in chapter.blocks:
                text = html.escape(block.text)
                
                if block.is_bold and not block.is_italic:
                    text = f'<strong>{text}</strong>'
                elif block.is_italic and not block.is_bold:
                    text = f'<em>{text}</em>'
                elif block.is_bold and block.is_italic:
                    text = f'<strong><em>{text}</em></strong>'
                
                if block.block_type == "heading":
                    level = self._get_heading_level(block)
                    if current_list:
                        html_parts.append(f'</{current_list}>')
                        current_list = None
                    html_parts.append(f'<h{level}>{text}</h{level}>')
                    
                elif block.block_type == "quote":
                    if current_list:
                        html_parts.append(f'</{current_list}>')
                        current_list = None
                    html_parts.append(f'<blockquote>{text}</blockquote>')
                    
                elif block.block_type == "list_item":
                    if current_list != "ul":
                        if current_list:
                            html_parts.append(f'</{current_list}>')
                        html_parts.append('<ul>')
                        current_list = "ul"
                    # Remover bullet do texto
                    clean_text = re.sub(r'^\s*[\•\-\*\◦\▪\d]+[\.\)]*\s*', '', text)
                    html_parts.append(f'<li>{clean_text}</li>')
                    
                else:  # paragraph
                    if current_list:
                        html_parts.append(f'</{current_list}>')
                        current_list = None
                    html_parts.append(f'<p>{text}</p>')
            
            if current_list:
                html_parts.append(f'</{current_list}>')
            
            html_parts.append('</section>')
        
        html_parts.extend(['</body>', '</html>'])
        
        return '\n'.join(html_parts)


# Função de conveniência
def extract_pdf(pdf_path: str) -> Tuple[Dict[str, Any], str]:
    """
    Extrai conteúdo de um PDF
    
    Args:
        pdf_path: Caminho para o arquivo PDF
        
    Returns:
        Tuple[dict, str]: Estrutura JSON e HTML básico
    """
    extractor = PDFExtractor()
    content, raw_html = extractor.extract(pdf_path)
    return content.to_dict(), raw_html
