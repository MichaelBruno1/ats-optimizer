# ATS Optimizer

> AI-powered resume optimization engine that analyzes job descriptions and tailors resumes for maximum ATS (Applicant Tracking System) compatibility.

---

## Features

- 📄 **Resume Parsing** — Supports PDF, DOCX, and TXT formats (up to 5 MB)
- 🔍 **Intelligent Job Analysis** — Extracts ATS keywords, required skills, seniority, and gap analysis
- ✨ **Resume Optimization** — Two modes:
  - `single` — One balanced resume optimized for all submitted jobs
  - `per_job` — A highly focused resume tailored to each vacancy
- 📊 **ATS Scoring** — Estimated ATS readability and compatibility scores
- 📥 **PDF Export** — Professional single-column PDF generated with WeasyPrint
- 📡 **Real-time Progress** — Server-Sent Events (SSE) for live pipeline updates
- 🤖 **Multi-provider LLM** — OpenAI, Ollama, Gemini, Azure, Anthropic via LiteLLM

---

## Architecture

```
POST /api/v1/analyze
│
├── Document Parser     → Extracts text from PDF/DOCX/TXT
├── Resume Analyst      → LLM agent: structured resume extraction
├── Job Analyst (async) → LLM agent: parallel job description analysis
├── Resume Optimizer    → LLM agent: ATS-optimized resume content
└── PDF Generator       → WeasyPrint + Jinja2 → PDF file

GET /api/v1/progress/{session_id}  → SSE real-time progress stream
GET /api/v1/download/{session_id}/{job_index} → PDF download
```

---

## Quick Start

### Prerequisites

- Python 3.12+
- An LLM API key (OpenAI, Gemini, Anthropic) **or** a local Ollama instance

### Local Development

```bash
# 1. Clone and enter the backend
cd backend

# 2. Create and activate a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your LLM API key and settings

# 5. Start the API server
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.
Interactive docs: `http://localhost:8000/api/docs`

### Docker Compose

```bash
# 1. Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env with your settings

# 2. Build and start
docker-compose up --build

# Stop
docker-compose down
```

---

## Configuration

All settings are loaded from environment variables or `backend/.env`:

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `openai` | Provider name (openai, ollama, gemini, azure, anthropic) |
| `LLM_MODEL` | `gpt-4o-mini` | Model name |
| `LLM_API_KEY` | _(empty)_ | API key for the chosen provider |
| `LLM_API_BASE` | _(empty)_ | Custom API base URL (for Ollama or compatible APIs) |
| `LLM_TEMPERATURE` | `0.3` | Sampling temperature (0.0–1.0) |
| `LLM_MAX_TOKENS` | `4096` | Maximum output tokens per LLM call |
| `MAX_FILE_SIZE_MB` | `5` | Maximum uploaded resume size |
| `MAX_JOBS` | `10` | Maximum job descriptions per request |
| `TEMP_DIR` | `/tmp/ats_optimizer` | Base directory for temporary session files |
| `TEMP_CLEANUP_MINUTES` | `30` | Lifetime of session files before cleanup |
| `CORS_ORIGINS` | `http://localhost:8000` | Comma-separated allowed CORS origins |

### Using Ollama (local)

```env
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2
LLM_API_BASE=http://localhost:11434
LLM_API_KEY=ollama
```

### Using Google Gemini

```env
LLM_PROVIDER=gemini
LLM_MODEL=gemini-1.5-flash
LLM_API_KEY=your-gemini-api-key
```

---

## API Reference

### `POST /api/v1/analyze`

Starts the resume optimization pipeline.

**Request** — `multipart/form-data`:
| Field | Type | Description |
|---|---|---|
| `resume` | File | Resume file (.pdf, .docx, .txt — max 5 MB) |
| `jobs` | string (JSON) | Array of `{title, company?, description}` objects |
| `output_mode` | string | `"single"` or `"per_job"` |

**Response** — `200 OK`:
```json
{
  "session_id": "abc123...",
  "message": "Processing started. Connect to the SSE endpoint for progress."
}
```

---

### `GET /api/v1/progress/{session_id}`

Server-Sent Events stream for real-time progress.

**Events**:
```
event: progress
data: {"step": "resume_analysis", "progress": 20, "message": "Resume analysis complete."}

event: complete
data: {"progress": 100, "message": "...", "session_id": "...", "result": {...}}

event: error
data: {"message": "Processing failed: ..."}
```

---

### `GET /api/v1/download/{session_id}/{job_index}`

Downloads the optimized PDF resume.

- Returns `application/pdf` with `Content-Disposition: attachment`
- `job_index`: `0` for single mode, or the job's index for per_job mode
- Returns `404` if the session or PDF doesn't exist

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

## Running Tests

```bash
cd backend
pytest tests/ -v
```

> **Note**: Integration tests that require LLM calls are skipped by default. Set `LLM_API_KEY` in your environment to run them.

---

## Project Structure

```
ats_optimizer/
├── Dockerfile
├── docker-compose.yml
├── README.md
└── backend/
    ├── requirements.txt
    ├── .env.example
    └── app/
        ├── main.py              # FastAPI app + lifespan
        ├── config.py            # Pydantic BaseSettings
        ├── api/
        │   ├── router.py        # All endpoints + SSE pipeline
        │   ├── schemas.py       # Pydantic v2 models
        │   └── dependencies.py  # FastAPI dependency injection
        ├── agents/
        │   ├── base_agent.py        # LiteLLM base class
        │   ├── job_analyst.py       # Job description analyzer
        │   ├── resume_analyst.py    # Resume structure extractor
        │   ├── resume_optimizer.py  # ATS resume optimizer
        │   └── prompts/
        │       ├── job_analysis.txt
        │       ├── resume_analysis.txt
        │       └── resume_optimization.txt
        ├── services/
        │   ├── document_parser.py   # PDF/DOCX/TXT text extraction
        │   ├── pdf_generator.py     # WeasyPrint PDF renderer
        │   └── temp_storage.py      # Session management + SSE queues
        └── templates/
            └── resume_template.html # Jinja2 ATS-friendly template
```

---

## Agent Design Principles

1. **No hallucination** — The optimizer only reorganizes and rephrases existing content
2. **Language detection** — All output is in the same language as the input resume
3. **Exact keyword matching** — ATS keywords are incorporated verbatim from job descriptions
4. **Async-first** — Job analyses run concurrently; WeasyPrint runs in a thread pool
5. **Ephemeral storage** — All session files are deleted after `TEMP_CLEANUP_MINUTES`

---

## License

MIT
