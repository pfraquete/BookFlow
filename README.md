# BookFlow - Sistema de Diagramação de Livros com IA

Sistema completo para diagramação automática de livros usando inteligência artificial.

## Stack

- **Frontend**: Next.js 14 + TypeScript + Tailwind + shadcn/ui
- **Backend**: FastAPI (Python 3.11)
- **Banco/Auth/Storage**: Supabase
- **IA**: Claude API (Anthropic)
- **PDF Processing**: PyMuPDF + WeasyPrint

## Funcionalidades

1. Upload de PDF de livro
2. Extração automática de conteúdo e estrutura
3. Normalização semântica com IA (Claude)
4. 6 templates de diagramação profissionais
5. Preview em tempo real
6. Geração de PDF final pronto para impressão

---

## Setup Rápido

### 1. Configurar Supabase

1. Crie um projeto no [Supabase](https://supabase.com)
2. Execute o SQL em `sql/schema.sql` no SQL Editor
3. Crie os buckets no Storage:
   - `uploads` (privado)
   - `previews` (privado)
   - `exports` (privado)
4. Configure as policies de Storage (ver seção abaixo)
5. Copie as credenciais (URL, Anon Key, Service Role Key)

### 2. Configurar Backend

```bash
cd backend

# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp .env.example .env
# Edite .env com suas credenciais

# Rodar
uvicorn app.main:app --reload --port 8000
```

### 3. Configurar Frontend

```bash
cd frontend

# Instalar dependências
npm install

# Configurar variáveis de ambiente
cp .env.example .env.local
# Edite .env.local com suas credenciais

# Rodar
npm run dev
```

Acesse: http://localhost:3000

---

## Variáveis de Ambiente

### Backend (.env)

```env
DEBUG=true
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
ANTHROPIC_API_KEY=sk-ant-api03-...
```

### Frontend (.env.local)

```env
NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Deploy em Produção

### Backend (Railway/Render/Fly.io)

**Railway:**
```bash
# Instalar CLI
npm install -g @railway/cli

# Login e deploy
railway login
railway init
railway up
```

**Docker:**
```bash
cd backend
docker build -t bookflow-api .
docker run -p 8000:8000 --env-file .env bookflow-api
```

### Frontend (Vercel)

```bash
# Instalar Vercel CLI
npm i -g vercel

# Deploy
cd frontend
vercel
```

Configure as variáveis de ambiente no dashboard da Vercel.

---

## Policies de Storage (Supabase)

Execute no SQL Editor:

```sql
-- Bucket: uploads
CREATE POLICY "Users can upload to own folder"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
  bucket_id = 'uploads' AND
  (storage.foldername(name))[1] = auth.uid()::text
);

CREATE POLICY "Users can read own uploads"
ON storage.objects FOR SELECT
TO authenticated
USING (
  bucket_id = 'uploads' AND
  (storage.foldername(name))[1] = auth.uid()::text
);

-- Repetir para buckets 'previews' e 'exports'
```

---

## Estrutura do Projeto

```
bookflow/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Configurações
│   │   ├── routes/
│   │   │   ├── auth.py          # Autenticação JWT
│   │   │   ├── projects.py      # CRUD projetos
│   │   │   ├── upload.py        # Upload + processamento
│   │   │   ├── preview.py       # Templates + preview
│   │   │   └── export.py        # Geração PDF final
│   │   └── services/
│   │       ├── db.py            # Cliente Supabase
│   │       ├── pdf_extractor.py # Extração PyMuPDF
│   │       ├── structure_normalizer_ai.py  # Claude
│   │       ├── template_engine.py  # Jinja2 + CSS
│   │       ├── pdf_renderer.py  # WeasyPrint
│   │       └── storage_client.py # Supabase Storage
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── app/
│   │   ├── page.tsx             # Dashboard
│   │   ├── login/page.tsx       # Login
│   │   └── projects/[projectId]/
│   │       ├── upload/page.tsx  # Upload PDF
│   │       ├── templates/page.tsx # Seleção template
│   │       └── preview/page.tsx # Preview + export
│   ├── components/ui/           # shadcn components
│   ├── lib/
│   │   ├── api.ts               # Cliente API
│   │   ├── supabase.ts          # Cliente Supabase
│   │   └── utils.ts             # Utilitários
│   └── package.json
├── sql/
│   └── schema.sql               # Tabelas + RLS
└── docs/
    └── ARCHITECTURE.md          # Diagrama arquitetura
```

---

## API Endpoints

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | /api/v1/projects | Criar projeto |
| GET | /api/v1/projects | Listar projetos |
| GET | /api/v1/projects/:id | Detalhe projeto |
| DELETE | /api/v1/projects/:id | Deletar projeto |
| POST | /api/v1/projects/:id/upload | Upload PDF |
| GET | /api/v1/projects/:id/status | Status processamento |
| GET | /api/v1/projects/:id/preview-templates | Listar templates |
| POST | /api/v1/projects/:id/apply-template | Aplicar template |
| GET | /api/v1/projects/:id/preview | Obter preview |
| POST | /api/v1/projects/:id/approve | Aprovar + exportar |
| GET | /api/v1/projects/:id/export-status | Status exportação |
| GET | /api/v1/projects/:id/download | Link download |

---

## Templates Disponíveis

| Key | Nome | Descrição |
|-----|------|-----------|
| minimalist | Minimalista Moderno | Clean, sans-serif, espaçoso |
| classic | Clássico Literário | Serif, drop caps, tradicional |
| editorial | Editorial Clean | Revista moderna, títulos fortes |
| academic | Técnico/Acadêmico | Numeração, referências |
| fantasy | Fantasia/Romance | Decorativo, imersivo |
| business | Business | Corporativo, insights boxes |

---

## Troubleshooting

**Erro de CORS:**
- Verifique se CORS_ORIGINS no backend inclui a URL do frontend

**PDF não processa:**
- Verifique se o PDF tem texto selecionável (não é escaneado)
- Limite de 100MB

**Claude timeout:**
- Para livros grandes, aumente CLAUDE_TIMEOUT no .env

**WeasyPrint não funciona no Windows:**
- Use Docker ou WSL

---

## Licença

MIT
