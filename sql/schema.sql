-- ============================================================================
-- BookFlow - Schema SQL para Supabase
-- ============================================================================

-- Habilitar extensões necessárias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- TABELA: projects
-- Representa um projeto de livro do usuário
-- ============================================================================
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    original_filename VARCHAR(500),
    status VARCHAR(50) NOT NULL DEFAULT 'created' 
        CHECK (status IN ('created', 'uploaded', 'extracting', 'parsed', 'normalizing', 'normalized', 'templated', 'approved', 'exporting', 'exported', 'error')),
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índices para projects
CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_created_at ON projects(created_at DESC);

-- ============================================================================
-- TABELA: uploads
-- Armazena informações do PDF original
-- ============================================================================
CREATE TABLE uploads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    storage_path VARCHAR(1000) NOT NULL,
    original_filename VARCHAR(500) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    mime_type VARCHAR(100) NOT NULL DEFAULT 'application/pdf',
    pages_count INTEGER,
    checksum_sha256 VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índice para uploads
CREATE INDEX idx_uploads_project_id ON uploads(project_id);

-- ============================================================================
-- TABELA: book_structures
-- Estrutura semântica extraída e normalizada do livro
-- ============================================================================
CREATE TABLE book_structures (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    
    -- Estrutura bruta extraída do PDF
    raw_text TEXT,
    raw_html TEXT,
    
    -- Estrutura semântica em JSON (capítulos, seções, etc)
    content_json JSONB,
    
    -- HTML normalizado pela IA
    normalized_html TEXT,
    
    -- Metadados da extração
    extraction_metadata JSONB DEFAULT '{}',
    
    -- Estatísticas
    word_count INTEGER,
    chapter_count INTEGER,
    image_count INTEGER,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índice para book_structures
CREATE INDEX idx_book_structures_project_id ON book_structures(project_id);

-- ============================================================================
-- TABELA: templates
-- Templates de diagramação disponíveis
-- ============================================================================
CREATE TABLE templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(50) DEFAULT 'general',
    
    -- Configurações do template
    config JSONB NOT NULL DEFAULT '{}',
    
    -- CSS/Tailwind classes
    css_content TEXT,
    
    -- URL do thumbnail de preview
    preview_thumbnail_url VARCHAR(1000),
    
    -- Ordenação para exibição
    sort_order INTEGER DEFAULT 0,
    
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índice para templates
CREATE INDEX idx_templates_key ON templates(key);
CREATE INDEX idx_templates_active ON templates(is_active);

-- ============================================================================
-- TABELA: renditions
-- Versões renderizadas do livro (preview + final)
-- ============================================================================
CREATE TABLE renditions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    template_id UUID NOT NULL REFERENCES templates(id),
    
    status VARCHAR(50) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'preview_generating', 'preview_generated', 'approved', 'pdf_generating', 'pdf_generated', 'error')),
    
    -- Caminhos no Storage
    preview_html_path VARCHAR(1000),
    final_pdf_path VARCHAR(1000),
    
    -- Metadados da renderização
    page_count INTEGER,
    file_size_bytes BIGINT,
    render_duration_ms INTEGER,
    
    error_message TEXT,
    
    is_current BOOLEAN DEFAULT FALSE,
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índices para renditions
CREATE INDEX idx_renditions_project_id ON renditions(project_id);
CREATE INDEX idx_renditions_template_id ON renditions(template_id);
CREATE INDEX idx_renditions_status ON renditions(status);

-- ============================================================================
-- TABELA: logs_ai
-- Logs de interações com a IA
-- ============================================================================
CREATE TABLE logs_ai (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    
    step VARCHAR(50) NOT NULL
        CHECK (step IN ('extract', 'normalize', 'template_apply', 'export', 'other')),
    
    -- Resumo da requisição (não guardar payload completo por privacidade)
    request_summary TEXT,
    
    -- Tokens usados
    input_tokens INTEGER,
    output_tokens INTEGER,
    
    -- Resultado
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT,
    duration_ms INTEGER,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índice para logs_ai
CREATE INDEX idx_logs_ai_project_id ON logs_ai(project_id);
CREATE INDEX idx_logs_ai_step ON logs_ai(step);
CREATE INDEX idx_logs_ai_created_at ON logs_ai(created_at DESC);

-- ============================================================================
-- FUNCTIONS E TRIGGERS
-- ============================================================================

-- Função para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers para updated_at
CREATE TRIGGER update_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_book_structures_updated_at
    BEFORE UPDATE ON book_structures
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_templates_updated_at
    BEFORE UPDATE ON templates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_renditions_updated_at
    BEFORE UPDATE ON renditions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================================

-- Habilitar RLS em todas as tabelas
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE uploads ENABLE ROW LEVEL SECURITY;
ALTER TABLE book_structures ENABLE ROW LEVEL SECURITY;
ALTER TABLE renditions ENABLE ROW LEVEL SECURITY;
ALTER TABLE logs_ai ENABLE ROW LEVEL SECURITY;

-- Políticas para projects
CREATE POLICY "Users can view own projects" ON projects
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can create own projects" ON projects
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own projects" ON projects
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own projects" ON projects
    FOR DELETE USING (auth.uid() = user_id);

-- Políticas para uploads (via project ownership)
CREATE POLICY "Users can view uploads of own projects" ON uploads
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM projects WHERE projects.id = uploads.project_id AND projects.user_id = auth.uid())
    );

CREATE POLICY "Users can create uploads for own projects" ON uploads
    FOR INSERT WITH CHECK (
        EXISTS (SELECT 1 FROM projects WHERE projects.id = uploads.project_id AND projects.user_id = auth.uid())
    );

-- Políticas para book_structures
CREATE POLICY "Users can view structures of own projects" ON book_structures
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM projects WHERE projects.id = book_structures.project_id AND projects.user_id = auth.uid())
    );

CREATE POLICY "Users can manage structures of own projects" ON book_structures
    FOR ALL USING (
        EXISTS (SELECT 1 FROM projects WHERE projects.id = book_structures.project_id AND projects.user_id = auth.uid())
    );

-- Políticas para renditions
CREATE POLICY "Users can view renditions of own projects" ON renditions
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM projects WHERE projects.id = renditions.project_id AND projects.user_id = auth.uid())
    );

CREATE POLICY "Users can manage renditions of own projects" ON renditions
    FOR ALL USING (
        EXISTS (SELECT 1 FROM projects WHERE projects.id = renditions.project_id AND projects.user_id = auth.uid())
    );

-- Templates são públicos para leitura
ALTER TABLE templates ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Anyone can view active templates" ON templates
    FOR SELECT USING (is_active = TRUE);

-- Logs são visíveis apenas para o dono do projeto
CREATE POLICY "Users can view logs of own projects" ON logs_ai
    FOR SELECT USING (
        project_id IS NULL OR
        EXISTS (SELECT 1 FROM projects WHERE projects.id = logs_ai.project_id AND projects.user_id = auth.uid())
    );

-- ============================================================================
-- DADOS INICIAIS: Templates
-- ============================================================================

INSERT INTO templates (key, name, description, category, sort_order, config) VALUES

('minimalist', 'Minimalista Moderno', 
'Design limpo com muito espaço em branco, tipografia sans-serif elegante e espaçamento generoso. Ideal para livros de não-ficção, ensaios e obras contemporâneas.',
'modern', 1,
'{
    "fonts": {
        "heading": "Inter",
        "body": "Inter",
        "sizes": {"h1": "2.5rem", "h2": "2rem", "h3": "1.5rem", "body": "1.125rem"}
    },
    "colors": {
        "text": "#1a1a1a",
        "heading": "#000000",
        "accent": "#666666",
        "background": "#ffffff"
    },
    "spacing": {
        "margins": {"top": "3cm", "bottom": "3cm", "left": "2.5cm", "right": "2.5cm"},
        "lineHeight": "1.8",
        "paragraphSpacing": "1.5rem"
    },
    "features": {
        "dropCaps": false,
        "chapterBreak": "page",
        "headerFooter": "minimal"
    }
}'::jsonb),

('classic', 'Clássico Literário',
'Estilo tradicional de livro físico com tipografia serif elegante, capitulares decorativas e layout atemporal. Perfeito para ficção literária, poesia e clássicos.',
'traditional', 2,
'{
    "fonts": {
        "heading": "Playfair Display",
        "body": "Crimson Pro",
        "sizes": {"h1": "2.25rem", "h2": "1.75rem", "h3": "1.375rem", "body": "1.0625rem"}
    },
    "colors": {
        "text": "#2d2d2d",
        "heading": "#1a1a1a",
        "accent": "#8b4513",
        "background": "#fefefe"
    },
    "spacing": {
        "margins": {"top": "2.5cm", "bottom": "3cm", "left": "2cm", "right": "2cm"},
        "lineHeight": "1.7",
        "paragraphSpacing": "0"
    },
    "features": {
        "dropCaps": true,
        "chapterBreak": "page",
        "headerFooter": "classic",
        "ornaments": true
    }
}'::jsonb),

('editorial', 'Editorial Clean',
'Layout moderno de revista/editora com títulos fortes, hierarquia visual clara e design sofisticado. Ideal para livros de negócios, biografias e não-ficção premium.',
'modern', 3,
'{
    "fonts": {
        "heading": "DM Sans",
        "body": "Source Serif Pro",
        "sizes": {"h1": "3rem", "h2": "2rem", "h3": "1.5rem", "body": "1.0625rem"}
    },
    "colors": {
        "text": "#333333",
        "heading": "#111111",
        "accent": "#0066cc",
        "background": "#ffffff"
    },
    "spacing": {
        "margins": {"top": "2.5cm", "bottom": "2.5cm", "left": "2cm", "right": "2cm"},
        "lineHeight": "1.65",
        "paragraphSpacing": "1rem"
    },
    "features": {
        "dropCaps": false,
        "chapterBreak": "page",
        "headerFooter": "editorial",
        "pullQuotes": true
    }
}'::jsonb),

('academic', 'Técnico / Acadêmico',
'Formato acadêmico com numeração de seções, suporte a equações, tabelas e referências. Ideal para teses, artigos, manuais técnicos e livros didáticos.',
'technical', 4,
'{
    "fonts": {
        "heading": "IBM Plex Sans",
        "body": "IBM Plex Serif",
        "code": "IBM Plex Mono",
        "sizes": {"h1": "2rem", "h2": "1.5rem", "h3": "1.25rem", "body": "1rem"}
    },
    "colors": {
        "text": "#1f1f1f",
        "heading": "#000000",
        "accent": "#0055a5",
        "background": "#ffffff"
    },
    "spacing": {
        "margins": {"top": "2.5cm", "bottom": "2.5cm", "left": "3cm", "right": "2cm"},
        "lineHeight": "1.6",
        "paragraphSpacing": "0.75rem"
    },
    "features": {
        "dropCaps": false,
        "chapterBreak": "page",
        "headerFooter": "academic",
        "sectionNumbering": true,
        "footnotes": true
    }
}'::jsonb),

('fantasy', 'Fantasia / Romance',
'Design imersivo com elementos decorativos sutis, tipografia que evoca atmosfera e layouts que transportam o leitor. Perfeito para ficção, romance e fantasia.',
'creative', 5,
'{
    "fonts": {
        "heading": "Cormorant Garamond",
        "body": "EB Garamond",
        "sizes": {"h1": "2.5rem", "h2": "1.875rem", "h3": "1.375rem", "body": "1.0625rem"}
    },
    "colors": {
        "text": "#3d3d3d",
        "heading": "#2c1810",
        "accent": "#7b4a2d",
        "background": "#faf8f5"
    },
    "spacing": {
        "margins": {"top": "2.5cm", "bottom": "3cm", "left": "2cm", "right": "2cm"},
        "lineHeight": "1.75",
        "paragraphSpacing": "0"
    },
    "features": {
        "dropCaps": true,
        "chapterBreak": "page",
        "headerFooter": "decorative",
        "ornaments": true,
        "chapterOrnaments": true
    }
}'::jsonb),

('business', 'Business / Empreendedorismo',
'Layout corporativo focado em clareza e impacto. Boxes de insights, citações destacadas e design que facilita a leitura rápida. Ideal para livros de negócios e autoajuda.',
'business', 6,
'{
    "fonts": {
        "heading": "Montserrat",
        "body": "Open Sans",
        "sizes": {"h1": "2.25rem", "h2": "1.75rem", "h3": "1.375rem", "body": "1rem"}
    },
    "colors": {
        "text": "#2d3748",
        "heading": "#1a202c",
        "accent": "#2563eb",
        "background": "#ffffff",
        "highlight": "#f0f9ff"
    },
    "spacing": {
        "margins": {"top": "2cm", "bottom": "2.5cm", "left": "2cm", "right": "2cm"},
        "lineHeight": "1.65",
        "paragraphSpacing": "1rem"
    },
    "features": {
        "dropCaps": false,
        "chapterBreak": "page",
        "headerFooter": "business",
        "insightBoxes": true,
        "pullQuotes": true,
        "keyPoints": true
    }
}'::jsonb);

-- ============================================================================
-- STORAGE BUCKETS (executar no Supabase Dashboard)
-- ============================================================================
-- Nota: Criar estes buckets via Dashboard do Supabase:
-- 1. "uploads" - PDFs originais
-- 2. "previews" - HTMLs de preview
-- 3. "exports" - PDFs finais gerados

-- Políticas de storage serão configuradas no Dashboard
