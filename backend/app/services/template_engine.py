"""
BookFlow - Template Engine
Aplica templates de diagramação ao conteúdo normalizado
"""
import json
from typing import Dict, Any, Optional, List
from jinja2 import Environment, BaseLoader
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# ESTILOS CSS PARA CADA TEMPLATE
# =============================================================================

TEMPLATE_STYLES = {
    "minimalist": """
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        :root {
            --color-text: #1a1a1a;
            --color-heading: #000000;
            --color-accent: #666666;
            --color-bg: #ffffff;
            --font-heading: 'Inter', sans-serif;
            --font-body: 'Inter', sans-serif;
        }
        
        @page {
            size: A5;
            margin: 3cm 2.5cm 3cm 2.5cm;
            @bottom-center {
                content: counter(page);
                font-family: var(--font-body);
                font-size: 10pt;
                color: var(--color-accent);
            }
        }
        
        @page :first {
            @bottom-center { content: none; }
        }
        
        body {
            font-family: var(--font-body);
            font-size: 11pt;
            line-height: 1.8;
            color: var(--color-text);
            background: var(--color-bg);
        }
        
        .book-title {
            font-family: var(--font-heading);
            font-size: 32pt;
            font-weight: 300;
            text-align: center;
            margin-bottom: 0.5em;
            letter-spacing: -0.02em;
        }
        
        .book-author {
            font-size: 14pt;
            text-align: center;
            color: var(--color-accent);
            margin-bottom: 3em;
        }
        
        .chapter {
            page-break-before: always;
        }
        
        .chapter:first-of-type {
            page-break-before: avoid;
        }
        
        .chapter-title {
            font-family: var(--font-heading);
            font-size: 24pt;
            font-weight: 400;
            margin-bottom: 2em;
            padding-top: 3em;
            letter-spacing: -0.01em;
        }
        
        h2 { font-size: 18pt; font-weight: 500; margin-top: 2em; }
        h3 { font-size: 14pt; font-weight: 500; margin-top: 1.5em; }
        
        p {
            margin-bottom: 1.5em;
            text-align: justify;
            text-indent: 0;
        }
        
        blockquote {
            margin: 2em 0;
            padding-left: 1.5em;
            border-left: 2px solid var(--color-accent);
            font-style: italic;
            color: var(--color-accent);
        }
        
        ul, ol {
            margin: 1.5em 0;
            padding-left: 1.5em;
        }
        
        li {
            margin-bottom: 0.5em;
        }
    """,
    
    "classic": """
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;500;600;700&family=Crimson+Pro:ital,wght@0,400;0,500;1,400&display=swap');
        
        :root {
            --color-text: #2d2d2d;
            --color-heading: #1a1a1a;
            --color-accent: #8b4513;
            --color-bg: #fefefe;
            --font-heading: 'Playfair Display', serif;
            --font-body: 'Crimson Pro', serif;
        }
        
        @page {
            size: A5;
            margin: 2.5cm 2cm 3cm 2cm;
            @top-center {
                content: string(chapter-title);
                font-family: var(--font-body);
                font-size: 9pt;
                font-style: italic;
                color: var(--color-accent);
            }
            @bottom-center {
                content: counter(page);
                font-family: var(--font-body);
                font-size: 10pt;
            }
        }
        
        @page :first {
            @top-center { content: none; }
            @bottom-center { content: none; }
        }
        
        body {
            font-family: var(--font-body);
            font-size: 11pt;
            line-height: 1.7;
            color: var(--color-text);
            background: var(--color-bg);
        }
        
        .book-title {
            font-family: var(--font-heading);
            font-size: 36pt;
            text-align: center;
            margin-bottom: 0.3em;
        }
        
        .book-author {
            font-size: 14pt;
            text-align: center;
            font-style: italic;
            margin-bottom: 4em;
        }
        
        .chapter {
            page-break-before: always;
        }
        
        .chapter-title {
            string-set: chapter-title content();
            font-family: var(--font-heading);
            font-size: 22pt;
            text-align: center;
            margin-bottom: 2em;
            padding-top: 4em;
        }
        
        /* Drop cap para primeiro parágrafo */
        .chapter > p:first-of-type::first-letter {
            font-family: var(--font-heading);
            font-size: 4em;
            float: left;
            line-height: 0.8;
            padding-right: 0.1em;
            color: var(--color-accent);
        }
        
        h2 { 
            font-family: var(--font-heading);
            font-size: 16pt;
            margin-top: 2em;
            text-align: center;
        }
        
        p {
            text-align: justify;
            text-indent: 1.5em;
            margin-bottom: 0;
        }
        
        p + p {
            text-indent: 1.5em;
        }
        
        blockquote {
            margin: 1.5em 2em;
            font-style: italic;
            text-align: center;
        }
        
        .ornament {
            text-align: center;
            font-size: 18pt;
            color: var(--color-accent);
            margin: 2em 0;
        }
    """,
    
    "editorial": """
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Source+Serif+Pro:ital,wght@0,400;0,600;1,400&display=swap');
        
        :root {
            --color-text: #333333;
            --color-heading: #111111;
            --color-accent: #0066cc;
            --color-bg: #ffffff;
            --font-heading: 'DM Sans', sans-serif;
            --font-body: 'Source Serif Pro', serif;
        }
        
        @page {
            size: A5;
            margin: 2.5cm 2cm;
            @bottom-right {
                content: counter(page);
                font-family: var(--font-heading);
                font-size: 9pt;
            }
        }
        
        body {
            font-family: var(--font-body);
            font-size: 10.5pt;
            line-height: 1.65;
            color: var(--color-text);
        }
        
        .book-title {
            font-family: var(--font-heading);
            font-size: 42pt;
            font-weight: 700;
            text-align: left;
            margin-bottom: 0.2em;
            letter-spacing: -0.03em;
            line-height: 1.1;
        }
        
        .book-author {
            font-family: var(--font-heading);
            font-size: 16pt;
            font-weight: 400;
            margin-bottom: 3em;
        }
        
        .chapter {
            page-break-before: always;
        }
        
        .chapter-title {
            font-family: var(--font-heading);
            font-size: 28pt;
            font-weight: 700;
            margin-bottom: 1em;
            padding-top: 2em;
            border-bottom: 4px solid var(--color-heading);
            padding-bottom: 0.5em;
        }
        
        h2 {
            font-family: var(--font-heading);
            font-size: 18pt;
            font-weight: 600;
            margin-top: 2em;
            color: var(--color-heading);
        }
        
        h3 {
            font-family: var(--font-heading);
            font-size: 13pt;
            font-weight: 500;
            margin-top: 1.5em;
            color: var(--color-accent);
        }
        
        p {
            margin-bottom: 1em;
            text-align: justify;
        }
        
        blockquote {
            margin: 2em 0;
            padding: 1.5em;
            background: #f5f5f5;
            border-left: 4px solid var(--color-accent);
            font-size: 12pt;
            font-style: italic;
        }
        
        .pull-quote {
            font-family: var(--font-heading);
            font-size: 18pt;
            font-weight: 500;
            color: var(--color-accent);
            text-align: center;
            margin: 2em 0;
            padding: 1em;
        }
    """,
    
    "academic": """
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Serif:ital,wght@0,400;0,500;1,400&family=IBM+Plex+Mono&display=swap');
        
        :root {
            --color-text: #1f1f1f;
            --color-heading: #000000;
            --color-accent: #0055a5;
            --color-bg: #ffffff;
            --font-heading: 'IBM Plex Sans', sans-serif;
            --font-body: 'IBM Plex Serif', serif;
            --font-mono: 'IBM Plex Mono', monospace;
        }
        
        @page {
            size: A4;
            margin: 2.5cm 2cm 2.5cm 3cm;
            @top-left {
                content: string(chapter-title);
                font-family: var(--font-heading);
                font-size: 9pt;
            }
            @bottom-center {
                content: counter(page);
                font-family: var(--font-heading);
                font-size: 10pt;
            }
        }
        
        body {
            font-family: var(--font-body);
            font-size: 11pt;
            line-height: 1.6;
            color: var(--color-text);
        }
        
        .book-title {
            font-family: var(--font-heading);
            font-size: 28pt;
            font-weight: 600;
            text-align: center;
            margin-bottom: 0.5em;
        }
        
        .book-author {
            font-family: var(--font-heading);
            font-size: 14pt;
            text-align: center;
            margin-bottom: 3em;
        }
        
        .chapter {
            page-break-before: always;
            counter-reset: section;
        }
        
        .chapter-title {
            string-set: chapter-title content();
            font-family: var(--font-heading);
            font-size: 20pt;
            font-weight: 600;
            margin-bottom: 1.5em;
            padding-top: 2em;
        }
        
        h2 {
            font-family: var(--font-heading);
            font-size: 14pt;
            font-weight: 500;
            margin-top: 1.5em;
            counter-increment: section;
        }
        
        h2::before {
            content: counter(chapter) "." counter(section) " ";
        }
        
        h3 {
            font-family: var(--font-heading);
            font-size: 12pt;
            font-weight: 500;
            margin-top: 1em;
        }
        
        p {
            margin-bottom: 0.75em;
            text-align: justify;
        }
        
        blockquote {
            margin: 1em 2em;
            padding-left: 1em;
            border-left: 3px solid var(--color-accent);
            font-style: italic;
        }
        
        code {
            font-family: var(--font-mono);
            font-size: 10pt;
            background: #f5f5f5;
            padding: 0.2em 0.4em;
        }
        
        .footnote {
            font-size: 9pt;
            color: #666;
        }
        
        .footnote-ref {
            font-size: 8pt;
            vertical-align: super;
            color: var(--color-accent);
        }
    """,
    
    "fantasy": """
        @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400&family=EB+Garamond:ital,wght@0,400;0,500;1,400&display=swap');
        
        :root {
            --color-text: #3d3d3d;
            --color-heading: #2c1810;
            --color-accent: #7b4a2d;
            --color-bg: #faf8f5;
            --font-heading: 'Cormorant Garamond', serif;
            --font-body: 'EB Garamond', serif;
        }
        
        @page {
            size: A5;
            margin: 2.5cm 2cm 3cm 2cm;
            background: var(--color-bg);
            @bottom-center {
                content: "✦ " counter(page) " ✦";
                font-family: var(--font-body);
                font-size: 10pt;
                color: var(--color-accent);
            }
        }
        
        body {
            font-family: var(--font-body);
            font-size: 11pt;
            line-height: 1.75;
            color: var(--color-text);
            background: var(--color-bg);
        }
        
        .book-title {
            font-family: var(--font-heading);
            font-size: 38pt;
            font-weight: 400;
            text-align: center;
            margin-bottom: 0.3em;
            letter-spacing: 0.05em;
        }
        
        .book-author {
            font-family: var(--font-heading);
            font-size: 16pt;
            font-style: italic;
            text-align: center;
            margin-bottom: 3em;
        }
        
        .chapter {
            page-break-before: always;
        }
        
        .chapter-title {
            font-family: var(--font-heading);
            font-size: 26pt;
            text-align: center;
            margin-bottom: 0.5em;
            padding-top: 3em;
        }
        
        .chapter-ornament {
            text-align: center;
            font-size: 24pt;
            color: var(--color-accent);
            margin-bottom: 2em;
        }
        
        .chapter-ornament::before {
            content: "❧";
        }
        
        /* Drop cap */
        .chapter > p:first-of-type::first-letter {
            font-family: var(--font-heading);
            font-size: 4.5em;
            float: left;
            line-height: 0.75;
            padding-right: 0.1em;
            color: var(--color-accent);
        }
        
        h2 {
            font-family: var(--font-heading);
            font-size: 18pt;
            text-align: center;
            margin-top: 2em;
            font-style: italic;
        }
        
        p {
            text-align: justify;
            text-indent: 1.5em;
            margin-bottom: 0;
        }
        
        blockquote {
            margin: 2em 1.5em;
            text-align: center;
            font-style: italic;
            color: var(--color-accent);
        }
        
        blockquote::before {
            content: "« ";
        }
        
        blockquote::after {
            content: " »";
        }
        
        .scene-break {
            text-align: center;
            margin: 2em 0;
            color: var(--color-accent);
        }
        
        .scene-break::before {
            content: "⁂";
            font-size: 18pt;
        }
    """,
    
    "business": """
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&family=Open+Sans:ital,wght@0,400;0,600;1,400&display=swap');
        
        :root {
            --color-text: #2d3748;
            --color-heading: #1a202c;
            --color-accent: #2563eb;
            --color-bg: #ffffff;
            --color-highlight: #f0f9ff;
            --font-heading: 'Montserrat', sans-serif;
            --font-body: 'Open Sans', sans-serif;
        }
        
        @page {
            size: A5;
            margin: 2cm 2cm 2.5cm 2cm;
            @bottom-right {
                content: counter(page);
                font-family: var(--font-heading);
                font-size: 9pt;
                font-weight: 500;
            }
        }
        
        body {
            font-family: var(--font-body);
            font-size: 10pt;
            line-height: 1.65;
            color: var(--color-text);
        }
        
        .book-title {
            font-family: var(--font-heading);
            font-size: 32pt;
            font-weight: 700;
            text-align: left;
            margin-bottom: 0.3em;
            color: var(--color-heading);
        }
        
        .book-author {
            font-family: var(--font-heading);
            font-size: 14pt;
            font-weight: 500;
            color: var(--color-accent);
            margin-bottom: 3em;
        }
        
        .chapter {
            page-break-before: always;
        }
        
        .chapter-title {
            font-family: var(--font-heading);
            font-size: 22pt;
            font-weight: 700;
            margin-bottom: 1.5em;
            padding-top: 2em;
            color: var(--color-heading);
        }
        
        h2 {
            font-family: var(--font-heading);
            font-size: 16pt;
            font-weight: 600;
            margin-top: 2em;
            color: var(--color-heading);
        }
        
        h3 {
            font-family: var(--font-heading);
            font-size: 13pt;
            font-weight: 600;
            margin-top: 1.5em;
            color: var(--color-accent);
        }
        
        p {
            margin-bottom: 1em;
        }
        
        blockquote {
            margin: 1.5em 0;
            padding: 1.5em;
            background: var(--color-highlight);
            border-left: 4px solid var(--color-accent);
            font-style: italic;
        }
        
        .insight-box {
            margin: 2em 0;
            padding: 1.5em;
            background: var(--color-highlight);
            border: 1px solid var(--color-accent);
            border-radius: 4px;
        }
        
        .insight-box-title {
            font-family: var(--font-heading);
            font-size: 12pt;
            font-weight: 600;
            color: var(--color-accent);
            margin-bottom: 0.5em;
        }
        
        .key-point {
            font-family: var(--font-heading);
            font-weight: 600;
            color: var(--color-accent);
        }
        
        .pull-quote {
            font-family: var(--font-heading);
            font-size: 16pt;
            font-weight: 600;
            color: var(--color-accent);
            text-align: center;
            margin: 2em 1em;
            padding: 1em;
            border-top: 2px solid var(--color-accent);
            border-bottom: 2px solid var(--color-accent);
        }
        
        ul, ol {
            margin: 1em 0;
            padding-left: 1.5em;
        }
        
        li {
            margin-bottom: 0.5em;
        }
    """
}


# =============================================================================
# TEMPLATE HTML BASE
# =============================================================================

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="{{ language }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        /* Reset básico */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        /* Estilos do template */
        {{ template_css }}
    </style>
</head>
<body>
    <header class="book-header">
        <h1 class="book-title">{{ title }}</h1>
        {% if author %}
        <p class="book-author">{{ author }}</p>
        {% endif %}
    </header>
    
    <main class="book-content">
        {% for chapter in chapters %}
        <section class="chapter" id="chapter-{{ loop.index }}">
            {% if chapter.title %}
            <h1 class="chapter-title">{{ chapter.title }}</h1>
            {% endif %}
            
            {% if template_key == 'fantasy' or template_key == 'classic' %}
            <div class="chapter-ornament"></div>
            {% endif %}
            
            {% for block in chapter.content %}
                {% if block.type == 'paragraph' %}
                <p class="paragraph">{{ block.text }}</p>
                
                {% elif block.type == 'heading' %}
                <h{{ block.level }} class="section-title">{{ block.text }}</h{{ block.level }}>
                
                {% elif block.type == 'quote' %}
                <blockquote class="quote">
                    {{ block.text }}
                    {% if block.attribution %}
                    <footer class="quote-attribution">— {{ block.attribution }}</footer>
                    {% endif %}
                </blockquote>
                
                {% elif block.type == 'list' %}
                {% if block.get('ordered', false) %}
                <ol class="list-ordered">
                {% else %}
                <ul class="list-unordered">
                {% endif %}
                    {% for item in block.get('items', []) %}
                    <li>{{ item }}</li>
                    {% endfor %}
                {% if block.get('ordered', false) %}
                </ol>
                {% else %}
                </ul>
                {% endif %}
                
                {% elif block.type == 'footnote' %}
                <aside class="footnote" id="fn-{{ block.id }}">
                    <span class="footnote-ref">{{ block.id }}</span>
                    {{ block.text }}
                </aside>
                
                {% elif block.type == 'scene_break' %}
                <div class="scene-break"></div>
                
                {% elif block.type == 'insight_box' and template_key == 'business' %}
                <div class="insight-box">
                    {% if block.title %}
                    <div class="insight-box-title">{{ block.title }}</div>
                    {% endif %}
                    <p>{{ block.text }}</p>
                </div>
                
                {% elif block.type == 'pull_quote' %}
                <div class="pull-quote">{{ block.text }}</div>
                
                {% endif %}
            {% endfor %}
        </section>
        {% endfor %}
    </main>
    
    <footer class="book-footer">
        <p class="generated-date">Gerado em {{ generation_date }}</p>
    </footer>
</body>
</html>"""


# =============================================================================
# TEMPLATE ENGINE
# =============================================================================

class TemplateEngine:
    """Engine para aplicar templates de diagramação"""
    
    def __init__(self):
        self.env = Environment(loader=BaseLoader())
        self.template = self.env.from_string(HTML_TEMPLATE)
    
    def apply_template(
        self,
        content_json: Dict[str, Any],
        template_key: str,
        template_config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Aplica um template ao conteúdo do livro
        
        Args:
            content_json: Estrutura JSON do livro
            template_key: Chave do template (minimalist, classic, etc)
            template_config: Configurações adicionais do template
            
        Returns:
            HTML completo com estilos aplicados
        """
        # Obter CSS do template
        template_css = TEMPLATE_STYLES.get(template_key, TEMPLATE_STYLES["minimalist"])
        
        # Mesclar configurações customizadas se houver
        if template_config:
            template_css = self._apply_custom_config(template_css, template_config)
        
        # Preparar dados para o template
        context = {
            "title": content_json.get("title", "Livro"),
            "author": content_json.get("author", ""),
            "chapters": content_json.get("chapters", []),
            "language": content_json.get("metadata", {}).get("detected_language", "pt-BR"),
            "template_key": template_key,
            "template_css": template_css,
            "generation_date": datetime.now().strftime("%d/%m/%Y"),
        }
        
        # Renderizar template
        html = self.template.render(**context)
        
        return html
    
    def _apply_custom_config(self, css: str, config: Dict[str, Any]) -> str:
        """Aplica configurações customizadas ao CSS"""
        # Substituir fontes se especificado
        if "fonts" in config:
            fonts = config["fonts"]
            if "heading" in fonts:
                css = css.replace("var(--font-heading)", f"'{fonts['heading']}', sans-serif")
            if "body" in fonts:
                css = css.replace("var(--font-body)", f"'{fonts['body']}', serif")
        
        # Substituir cores se especificado
        if "colors" in config:
            colors = config["colors"]
            for key, value in colors.items():
                css = css.replace(f"var(--color-{key})", value)
        
        return css
    
    def get_available_templates(self) -> List[Dict[str, Any]]:
        """Lista templates disponíveis com metadados"""
        return [
            {
                "key": "minimalist",
                "name": "Minimalista Moderno",
                "description": "Design limpo com muito espaço em branco, tipografia sans-serif elegante.",
                "category": "modern",
            },
            {
                "key": "classic",
                "name": "Clássico Literário",
                "description": "Estilo tradicional de livro físico com tipografia serif elegante e capitulares.",
                "category": "traditional",
            },
            {
                "key": "editorial",
                "name": "Editorial Clean",
                "description": "Layout moderno de revista/editora com títulos fortes e hierarquia visual clara.",
                "category": "modern",
            },
            {
                "key": "academic",
                "name": "Técnico / Acadêmico",
                "description": "Formato acadêmico com numeração de seções e suporte a referências.",
                "category": "technical",
            },
            {
                "key": "fantasy",
                "name": "Fantasia / Romance",
                "description": "Design imersivo com elementos decorativos sutis e atmosfera envolvente.",
                "category": "creative",
            },
            {
                "key": "business",
                "name": "Business / Empreendedorismo",
                "description": "Layout corporativo com boxes de insights e citações destacadas.",
                "category": "business",
            },
        ]


# Instância global
template_engine = TemplateEngine()


def apply_book_template(
    content_json: Dict[str, Any],
    template_key: str,
    template_config: Optional[Dict[str, Any]] = None
) -> str:
    """
    Função de conveniência para aplicar template
    
    Returns:
        HTML completo com estilos
    """
    return template_engine.apply_template(content_json, template_key, template_config)
