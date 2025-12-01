"""
BookFlow - Serviço de Normalização de Estrutura com IA (Claude)
Usa Claude para limpar e estruturar semanticamente o conteúdo extraído do PDF
"""
import anthropic
import json
import time
import re
import logging
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

from app.config import get_settings
from app.services.db import db

logger = logging.getLogger(__name__)


# =============================================================================
# PROMPTS PARA CLAUDE
# =============================================================================

SYSTEM_PROMPT_NORMALIZE = """Você é um especialista em estruturação semântica de livros. Sua tarefa é receber conteúdo extraído de um PDF de livro e produzir uma versão limpa, bem estruturada e semanticamente correta.

## REGRAS FUNDAMENTAIS:
1. NUNCA invente, adicione ou modifique o conteúdo textual
2. Apenas reorganize, corrija erros de extração e aplique estrutura semântica
3. Mantenha 100% da fidelidade ao texto original
4. Corrija apenas problemas claros de extração (palavras cortadas, parágrafos quebrados)

## PROBLEMAS COMUNS A CORRIGIR:
- Palavras cortadas no meio (ex: "estu-" "dantes" → "estudantes")
- Parágrafos quebrados incorretamente
- Números de página misturados no texto
- Headers/footers repetidos misturados no conteúdo
- Espaçamentos inconsistentes
- Caracteres especiais corrompidos

## ESTRUTURA SEMÂNTICA ESPERADA:
- Identificar e marcar capítulos (h1)
- Identificar e marcar seções/subseções (h2, h3)
- Identificar citações (blockquote)
- Identificar listas (ul/ol)
- Identificar notas de rodapé
- Manter parágrafos bem definidos

## FORMATO DE SAÍDA:
Você DEVE retornar um JSON válido com esta estrutura exata:
{
    "title": "Título do Livro",
    "author": "Autor (se detectado)",
    "chapters": [
        {
            "title": "Título do Capítulo",
            "level": 1,
            "content": [
                {"type": "paragraph", "text": "Texto do parágrafo..."},
                {"type": "heading", "level": 2, "text": "Subtítulo"},
                {"type": "quote", "text": "Citação...", "attribution": "Autor da citação (opcional)"},
                {"type": "list", "ordered": false, "items": ["Item 1", "Item 2"]},
                {"type": "footnote", "id": "1", "text": "Texto da nota de rodapé"}
            ]
        }
    ],
    "metadata": {
        "word_count": 12345,
        "chapter_count": 10,
        "has_footnotes": true,
        "detected_language": "pt-BR"
    }
}

## IMPORTANTE:
- Responda APENAS com o JSON, sem texto adicional
- O JSON deve ser válido e parseável
- Mantenha a ordem original do conteúdo"""


SYSTEM_PROMPT_HTML_GENERATE = """Você é um especialista em HTML semântico para livros. Sua tarefa é converter uma estrutura JSON de livro em HTML semântico limpo e bem formatado.

## REGRAS:
1. Use tags HTML5 semânticas apropriadas
2. Adicione classes CSS semânticas para facilitar estilização
3. Preserve a hierarquia do documento
4. Mantenha acessibilidade (ARIA quando necessário)

## CLASSES CSS A USAR:
- .book-title: título principal do livro
- .book-author: autor do livro
- .chapter: container de capítulo
- .chapter-title: título do capítulo
- .section-title: títulos de seção (h2, h3)
- .paragraph: parágrafos normais
- .quote: citações (blockquote)
- .quote-attribution: atribuição de citação
- .footnote: notas de rodapé
- .footnote-ref: referência à nota no texto
- .list-ordered / .list-unordered: listas

## FORMATO DE SAÍDA:
Retorne APENAS o HTML, começando com <!DOCTYPE html> e terminando com </html>.
Não inclua explicações ou texto adicional."""


# =============================================================================
# SERVIÇO DE NORMALIZAÇÃO
# =============================================================================

@dataclass
class NormalizationResult:
    """Resultado da normalização"""
    success: bool
    content_json: Optional[Dict[str, Any]] = None
    normalized_html: Optional[str] = None
    error_message: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    duration_ms: int = 0


class StructureNormalizerAI:
    """Serviço de normalização de estrutura usando Claude"""
    
    def __init__(self):
        settings = get_settings()
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.CLAUDE_MODEL
        self.max_tokens = settings.CLAUDE_MAX_TOKENS
        self.timeout = settings.CLAUDE_TIMEOUT
    
    async def normalize(
        self,
        raw_html: str,
        content_json: Optional[Dict[str, Any]] = None,
        project_id: Optional[str] = None
    ) -> NormalizationResult:
        """
        Normaliza o conteúdo extraído do PDF
        
        Args:
            raw_html: HTML bruto extraído do PDF
            content_json: Estrutura JSON opcional já extraída
            project_id: ID do projeto para logging
            
        Returns:
            NormalizationResult com estrutura normalizada
        """
        start_time = time.time()
        
        try:
            # Preparar input para Claude
            input_content = self._prepare_input(raw_html, content_json)
            
            # Primeira chamada: normalizar estrutura para JSON
            json_result = await self._call_claude_normalize(input_content)
            
            if not json_result.success:
                return json_result
            
            # Segunda chamada: gerar HTML semântico
            html_result = await self._call_claude_html(json_result.content_json)
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Logging
            if project_id:
                await db.log_ai_interaction(
                    project_id=project_id,
                    step="normalize",
                    request_summary=f"Normalized book with {json_result.content_json.get('metadata', {}).get('word_count', 0)} words",
                    input_tokens=json_result.input_tokens + html_result.input_tokens,
                    output_tokens=json_result.output_tokens + html_result.output_tokens,
                    success=True,
                    duration_ms=duration_ms
                )
            
            return NormalizationResult(
                success=True,
                content_json=json_result.content_json,
                normalized_html=html_result.normalized_html,
                input_tokens=json_result.input_tokens + html_result.input_tokens,
                output_tokens=json_result.output_tokens + html_result.output_tokens,
                duration_ms=duration_ms
            )
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Normalization failed: {e}")
            
            if project_id:
                await db.log_ai_interaction(
                    project_id=project_id,
                    step="normalize",
                    request_summary="Normalization failed",
                    success=False,
                    error_message=str(e),
                    duration_ms=duration_ms
                )
            
            return NormalizationResult(
                success=False,
                error_message=str(e),
                duration_ms=duration_ms
            )
    
    def _prepare_input(self, raw_html: str, content_json: Optional[Dict[str, Any]]) -> str:
        """Prepara o input para Claude"""
        parts = []
        
        if content_json:
            parts.append("## ESTRUTURA JSON EXTRAÍDA:")
            parts.append("```json")
            parts.append(json.dumps(content_json, ensure_ascii=False, indent=2)[:50000])
            parts.append("```")
        
        parts.append("\n## HTML BRUTO EXTRAÍDO:")
        parts.append("```html")
        # Limitar tamanho do HTML para não estourar contexto
        parts.append(raw_html[:100000])
        parts.append("```")
        
        return "\n".join(parts)
    
    async def _call_claude_normalize(self, input_content: str) -> NormalizationResult:
        """Chama Claude para normalizar estrutura"""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=SYSTEM_PROMPT_NORMALIZE,
                messages=[
                    {
                        "role": "user",
                        "content": f"Normalize o seguinte conteúdo de livro extraído de PDF:\n\n{input_content}"
                    }
                ]
            )
            
            # Extrair JSON da resposta
            response_text = response.content[0].text.strip()
            
            # Tentar limpar a resposta se vier com markdown
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            content_json = json.loads(response_text)
            
            return NormalizationResult(
                success=True,
                content_json=content_json,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude JSON response: {e}")
            return NormalizationResult(
                success=False,
                error_message=f"Invalid JSON from AI: {e}"
            )
        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            return NormalizationResult(
                success=False,
                error_message=f"AI API error: {e}"
            )
    
    async def _call_claude_html(self, content_json: Dict[str, Any]) -> NormalizationResult:
        """Chama Claude para gerar HTML semântico"""
        try:
            json_str = json.dumps(content_json, ensure_ascii=False, indent=2)
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=SYSTEM_PROMPT_HTML_GENERATE,
                messages=[
                    {
                        "role": "user",
                        "content": f"Converta esta estrutura JSON de livro em HTML semântico:\n\n```json\n{json_str}\n```"
                    }
                ]
            )
            
            html_content = response.content[0].text.strip()
            
            # Limpar se veio com markdown
            if html_content.startswith("```html"):
                html_content = html_content[7:]
            if html_content.startswith("```"):
                html_content = html_content[3:]
            if html_content.endswith("```"):
                html_content = html_content[:-3]
            
            return NormalizationResult(
                success=True,
                normalized_html=html_content,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens
            )
            
        except anthropic.APIError as e:
            logger.error(f"Claude API error generating HTML: {e}")
            return NormalizationResult(
                success=False,
                error_message=f"AI API error: {e}"
            )


# Instância global
# Instância lazy
_normalizer_instance: Optional[StructureNormalizerAI] = None

def get_normalizer() -> StructureNormalizerAI:
    global _normalizer_instance
    if _normalizer_instance is None:
        _normalizer_instance = StructureNormalizerAI()
    return _normalizer_instance


async def normalize_book_structure(
    raw_html: str,
    content_json: Optional[Dict[str, Any]] = None,
    project_id: Optional[str] = None
) -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[str]]:
    """
    Função de conveniência para normalizar estrutura do livro
    
    Returns:
        Tuple[content_json, normalized_html, error_message]
    """
    result = await get_normalizer().normalize(raw_html, content_json, project_id)
    
    if result.success:
        return result.content_json, result.normalized_html, None
    else:
        return None, None, result.error_message
