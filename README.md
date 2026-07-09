# ATS Optimizer

> Mecanismo de otimização de currículos baseado em IA que analisa descrições de vagas e personaliza currículos para máxima compatibilidade com sistemas ATS (Applicant Tracking System).

---

## Funcionalidades

- 📄 **Leitura de Currículos** — Suporta formatos PDF, DOCX e TXT (até 5 MB)
- 🔍 **Análise Inteligente de Vagas** — Extrai palavras-chave ATS, habilidades exigidas, nível de senioridade e análise de lacunas (gap analysis)
- ✨ **Otimização de Currículos** — Dois modos de operação:
  - `single` — Um único currículo balanceado e otimizado para todas as vagas enviadas
  - `per_job` — Um currículo altamente focado e personalizado para cada vaga individualmente
- 📊 **Pontuação ATS** — Estimativa de pontuação de legibilidade e compatibilidade com o sistema ATS
- 📥 **Exportação para PDF** — PDF profissional de coluna única gerado dinamicamente com WeasyPrint
- 📡 **Progresso em Tempo Real** — Server-Sent Events (SSE) para acompanhamento ao vivo do pipeline de processamento
- 🤖 **Integração de LLM Multi-provedor** — OpenAI, Ollama, Gemini, Azure e Anthropic via LiteLLM

---

## Arquitetura

```
POST /api/v1/analyze
│
├── Document Parser     → Extrai texto de PDF/DOCX/TXT
├── Resume Analyst      → Agente LLM: extração estruturada do currículo
├── Job Analyst (async) → Agente LLM: análise paralela de descrições de vagas
├── Resume Optimizer    → Agente LLM: geração de currículo otimizado para ATS
└── PDF Generator       → WeasyPrint + Jinja2 → Arquivo PDF final
    
GET /api/v1/progress/{session_id}  → Stream de progresso SSE em tempo real
GET /api/v1/download/{session_id}/{job_index} → Download do PDF gerado
```

---

## Início Rápido

### Pré-requisitos

- Python 3.12+
- Uma chave de API de LLM (OpenAI, Gemini, Anthropic) **ou** uma instância local do Ollama ativa

### Desenvolvimento Local

```bash
# 1. Entre no diretório do backend
cd backend

# 2. Crie e ative um ambiente virtual
python -m venv .venv
# No Windows:
.venv\Scripts\activate
# No Linux/macOS:
source .venv/bin/activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Configure as variáveis de ambiente
cp .env.example .env
# Edite o arquivo .env com sua chave de API e configurações de LLM

# 5. Inicie o servidor da API
uvicorn app.main:app --reload --port 8000
```

A API estará disponível em `http://localhost:8000`.
Documentação interativa do Swagger: `http://localhost:8000/api/docs`

### Docker Compose

```bash
# 1. Configure as variáveis de ambiente
cp backend/.env.example backend/.env
# Edite backend/.env com as configurações da sua LLM

# 2. Compile e inicie o container
docker-compose up --build

# Para parar a execução
docker-compose down
```

---

## Configurações

Todas as configurações são carregadas de variáveis de ambiente ou do arquivo `backend/.env`:

| Variável | Padrão | Descrição |
|---|---|---|
| `LLM_PROVIDER` | `openai` | Nome do provedor (openai, ollama, gemini, azure, anthropic) |
| `LLM_MODEL` | `gpt-4o-mini` | Nome do modelo |
| `LLM_API_KEY` | _(vazio)_ | Chave de API do provedor configurado |
| `LLM_API_BASE` | _(vazio)_ | URL base personalizada (para Ollama ou gateways compatíveis com OpenAI) |
| `LLM_TEMPERATURE` | `0.3` | Temperatura de amostragem (0.0 a 1.0) |
| `LLM_MAX_TOKENS` | `4096` | Limite de tokens de saída por chamada do LLM |
| `MAX_FILE_SIZE_MB` | `5` | Tamanho máximo permitido para o upload de currículos |
| `MAX_JOBS` | `10` | Quantidade máxima de vagas processadas por requisição |
| `TEMP_DIR` | `/tmp/ats_optimizer` | Diretório de armazenamento temporário de sessões |
| `TEMP_CLEANUP_MINUTES` | `30` | Tempo de vida dos arquivos temporários antes da limpeza automática |
| `CORS_ORIGINS` | `http://localhost:8000` | Origens permitidas para requisições CORS separadas por vírgula |

### Exemplo usando Ollama (local)

```env
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2
LLM_API_BASE=http://localhost:11434
LLM_API_KEY=ollama
```

### Exemplo usando Google Gemini

```env
LLM_PROVIDER=gemini
LLM_MODEL=gemini-1.5-flash
LLM_API_KEY=sua-chave-api-gemini
```

---

## Referência da API

### `POST /api/v1/analyze`

Inicia o fluxo de otimização de currículo em segundo plano.

**Requisição** — `multipart/form-data`:
| Campo | Tipo | Descrição |
|---|---|---|
| `resume` | Arquivo | Currículo (.pdf, .docx, .txt — máx 5 MB) |
| `jobs` | string (JSON) | Array contendo objetos `{title, company?, description}` |
| `output_mode` | string | `"single"` ou `"per_job"` |

**Resposta** — `200 OK`:
```json
{
  "session_id": "abc123...",
  "message": "Processing started. Connect to the SSE endpoint for progress."
}
```

---

### `GET /api/v1/progress/{session_id}`

Fluxo de Server-Sent Events (SSE) para atualização do progresso de execução.

**Eventos**:
```
event: progress
data: {"step": "resume_analysis", "progress": 20, "message": "Análise do currículo concluída."}

event: complete
data: {"progress": 100, "message": "...", "session_id": "...", "result": {...}}

event: error
data: {"message": "Falha no processamento: ..."}
```

---

### `GET /api/v1/download/{session_id}/{job_index}`

Faz o download do currículo PDF otimizado.

- Retorna `application/pdf` com `Content-Disposition: attachment`
- `job_index`: `0` no modo single, ou o índice numérico da vaga no modo per_job
- Retorna `404` se a sessão ou o arquivo PDF correspondente não for localizado

---

### `GET /api/v1/health`

```json
{"status": "healthy", "llm_provider": "openai", "model": "gpt-4o-mini"}
```

---

### `GET /api/v1/config`

```json
{
  "provider": "openai",
  "model": "gpt-4o-mini",
  "max_jobs": 10,
  "accepted_formats": [".pdf", ".docx", ".txt"],
  "max_file_size_mb": 5,
  "output_modes": ["single", "per_job"]
}
```

---

## Executando os Testes

```bash
cd backend
pytest tests/ -v
```

> **Nota**: Testes de integração que exigem chamadas de LLMs reais são ignorados por padrão. Defina as credenciais adequadas na variável de ambiente local para executá-los.

---

## Estrutura do Projeto

```
ats_optimizer/
├── Dockerfile
├── docker-compose.yml
├── README.md
└── backend/
    ├── requirements.txt
    ├── .env.example
    └── app/
        ├── main.py              # Aplicação FastAPI + rotinas de lifespan
        ├── config.py            # Definição do Pydantic BaseSettings
        ├── api/
        │   ├── router.py        # Endpoints expostos e pipeline assíncrono
        │   ├── schemas.py       # Modelos Pydantic v2 do contrato da API
        │   └── dependencies.py  # Gerenciamento de dependências do FastAPI
        ├── agents/
        │   ├── base_agent.py        # Classe base do LiteLLM
        │   ├── job_analyst.py       # Agente analista de descrição de vagas
        │   ├── resume_analyst.py    # Agente de extração estruturada do currículo
        │   ├── resume_optimizer.py  # Agente otimizador para ATS
        │   └── prompts/
        │       ├── job_analysis.txt
        │       ├── resume_analysis.txt
        │       └── resume_optimization.txt
        ├── services/
        │   ├── document_parser.py   # Extrator de texto de PDF/DOCX/TXT
        │   ├── pdf_generator.py     # Renderizador de PDF via WeasyPrint
        │   └── temp_storage.py      # Gestão de sessões e filas SSE
        └── templates/
            └── resume_template.html # Template Jinja2 amigável para ATS
```

---

## Princípios de Design dos Agentes

1. **Sem alucinação** — O otimizador se limita a reorganizar e reformular informações reais presentes no currículo original
2. **Respeito ao idioma** — Toda a saída estruturada gerada pelos agentes é gerada no mesmo idioma detectado no currículo original
3. **Correspondência exata de termos** — As palavras-chave ATS identificadas são inseridas de forma literal a partir do anúncio da vaga
4. **Assincronismo** — As análises de vagas rodam de forma concorrente em paralelo; WeasyPrint executa em thread pool isolado
5. **Armazenamento efêmero** — Todos os arquivos criados nas sessões são destruídos automaticamente após decorridos `TEMP_CLEANUP_MINUTES`
