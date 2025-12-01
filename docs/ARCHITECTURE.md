# BookFlow - Sistema de Diagramação de Livros

## Visão Geral da Arquitetura

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (Next.js 14)                         │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐  ┌────────────────┐  │
│  │  Login  │  │Dashboard │  │  Upload  │  │Templates│  │    Preview     │  │
│  └────┬────┘  └────┬─────┘  └────┬─────┘  └────┬────┘  └───────┬────────┘  │
└───────┼────────────┼─────────────┼─────────────┼───────────────┼───────────┘
        │            │             │             │               │
        ▼            ▼             ▼             ▼               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SUPABASE AUTH (JWT)                               │
└─────────────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          BACKEND (FastAPI - Python)                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                              ROUTES                                  │   │
│  │  /projects  /upload  /preview-templates  /apply-template  /approve  │   │
│  └───────┬───────────────────────────────────────────────────────┬─────┘   │
│          │                                                       │         │
│  ┌───────▼───────────────────────────────────────────────────────▼─────┐   │
│  │                            SERVICES                                  │   │
│  │  ┌────────────────┐  ┌─────────────────────┐  ┌──────────────────┐  │   │
│  │  │ PDF Extractor  │  │ AI Structure        │  │ Template Engine  │  │   │
│  │  │ (PyMuPDF)      │  │ Normalizer (Claude) │  │ (Jinja2+Tailwind)│  │   │
│  │  └────────────────┘  └─────────────────────┘  └──────────────────┘  │   │
│  │  ┌────────────────┐  ┌─────────────────────┐                        │   │
│  │  │ PDF Renderer   │  │ Storage Client      │                        │   │
│  │  │ (WeasyPrint)   │  │ (Supabase)          │                        │   │
│  │  └────────────────┘  └─────────────────────┘                        │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
        │                           │
        ▼                           ▼
┌────────────────────┐    ┌────────────────────────────────────────────────────┐
│   CLAUDE API       │    │                    SUPABASE                         │
│   (Anthropic)      │    │  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │
│                    │    │  │  Postgres   │  │   Storage   │  │    Auth    │  │
│  - Normalização    │    │  │  (Tabelas)  │  │   (PDFs)    │  │   (JWT)    │  │
│  - Estruturação    │    │  └─────────────┘  └─────────────┘  └────────────┘  │
└────────────────────┘    └────────────────────────────────────────────────────┘
```

## Pipeline de Processamento

```
PDF Original
     │
     ▼
┌────────────────────┐
│  1. UPLOAD         │  Salva PDF no Storage
│     (Storage)      │  Cria registro no DB
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│  2. EXTRAÇÃO       │  PyMuPDF extrai texto
│     (PDF→HTML)     │  Identifica estrutura básica
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│  3. NORMALIZAÇÃO   │  Claude analisa estrutura
│     (IA)           │  Gera HTML semântico limpo
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│  4. TEMPLATE       │  Usuário escolhe template
│     (Escolha)      │  Sistema aplica estilos
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│  5. PREVIEW        │  Visualização paginada
│     (HTML)         │  Ajustes se necessário
└─────────┬──────────┘
          │
          ▼
┌────────────────────┐
│  6. APROVAÇÃO      │  WeasyPrint gera PDF
│     (PDF Final)    │  Salva no Storage
└────────────────────┘
```

## Stack Tecnológica

| Componente | Tecnologia | Justificativa |
|------------|------------|---------------|
| Frontend | Next.js 14 + TypeScript | App Router, SSR, performance |
| UI | Tailwind + shadcn/ui | Componentes prontos, customizável |
| Backend | FastAPI (Python 3.11) | Async, tipagem, OpenAPI automático |
| PDF Parse | PyMuPDF (fitz) | Rápido, suporta imagens, robusto |
| PDF Render | WeasyPrint | CSS paging, qualidade profissional |
| IA | Claude API (Anthropic) | Melhor para estruturação semântica |
| DB | Supabase (Postgres) | Auth integrado, Storage, realtime |
| Storage | Supabase Storage | Integrado, CDN, signed URLs |

## Decisões de Produto

1. **Limite de PDF**: 100MB máximo (cobre 99% dos livros)
2. **Formatos suportados**: PDF apenas (pode expandir depois)
3. **Idiomas**: PT-BR foco principal, mas funciona com qualquer idioma
4. **Templates**: 6 templates iniciais, expansível
5. **Versionamento**: Mantém histórico de todas as renditions
6. **Timeout IA**: 120 segundos (livros grandes)
