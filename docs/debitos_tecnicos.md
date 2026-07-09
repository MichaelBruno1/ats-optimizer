# Débitos Técnicos — ATS Optimizer v1.0

> Levantamento completo de débitos técnicos identificados por análise estática e revisão de código do projeto inteiro.
> Cada item é classificado por **severidade** e **área** para facilitar a priorização em sprints futuras.

**Legenda de severidade:**
- 🔴 **Crítico** — Perda de dados ou falha em produção
- 🟠 **Alto** — Impacto direto na qualidade, manutenção ou escalabilidade
- 🟡 **Médio** — Melhoria significativa de robustez ou experiência do desenvolvedor
- 🟢 **Baixo** — Polimento, boas práticas ou melhorias cosméticas

---

## 1. Performance

### 🟡 PERF-01 — CSS não minificado (1323 linhas)
**Arquivo:** `frontend/css/style.css`
O CSS é servido como arquivo único e não minificado. Contém CSS morto (ex: classe `.ats-badge` removida do template mas ainda definida no stylesheet).
**Correção sugerida:** Remover CSS não utilizado e considerar minificação no processo de build.

## 2. Qualidade de Código e Manutenibilidade

### 🟠 CODE-01 — Padrão de config com classe `Config` depreciado (Pydantic v2)
**Arquivo:** `backend/app/api/schemas.py`
O uso de `class Config` interno está depreciado no Pydantic V2 e gera warnings no runtime.
**Correção sugerida:** Migrar para `model_config = ConfigDict(...)`.

---

### 🟠 CODE-02 — Atributo `version` depreciado no docker-compose.yml
**Arquivo:** `docker-compose.yml`
O campo `version: '3.8'` é ignorado pelo Docker Compose moderno e gera avisos.
**Correção sugerida:** Remover o campo `version` do arquivo.

---

### 🟡 CODE-03 — Sem requirements-dev.txt para dependências de desenvolvimento
**Arquivo:** `backend/requirements.txt`
As dependências de teste (`pytest`, `pytest-asyncio`, `python-docx`, `pymupdf`) estão misturadas com as de produção ou ausentes.
**Correção sugerida:** Criar `requirements-dev.txt` separado.

---

### 🟡 CODE-04 — Dependências sem pinning exato de versão
**Arquivo:** `backend/requirements.txt`
Pacotes utilizam `>=` sem limite superior (ex: `fastapi>=0.115`), permitindo upgrades quebráveis.
**Correção sugerida:** Utilizar ranges como `fastapi>=0.115,<1.0` ou pinning exato com lock file.

---

### 🟡 CODE-05 — Valores hardcoded no frontend duplicam configurações do backend
**Arquivos:** `frontend/js/upload.js`, `frontend/js/jobs.js`
O limite de 5MB de upload e o limite de 10 vagas estão hardcoded no JavaScript em vez de serem obtidos do endpoint `/api/v1/config`.
**Correção sugerida:** Consumir o endpoint `/api/v1/config` na inicialização e usar os valores retornados.

---

### 🟡 CODE-06 — CSS morto no stylesheet
**Arquivo:** `frontend/css/style.css`
Classes como `.ats-badge` ainda estão definidas no CSS apesar de terem sido removidas do template HTML.
**Correção sugerida:** Auditar e remover regras CSS não referenciadas.

---

### 🟢 CODE-07 — Ausência de middleware de Request ID
**Arquivo:** `backend/app/main.py`
Não há geração de Request ID para correlacionar logs entre as etapas do pipeline.
**Correção sugerida:** Adicionar middleware que gere e propague um UUID por requisição.

---

### 🟢 CODE-08 — Sem .dockerignore
**Arquivo:** Raiz do projeto
Sem `.dockerignore`, arquivos desnecessários (`.git`, `docs/`, `tests/`, `__pycache__`) são incluídos no contexto de build do Docker.
**Correção sugerida:** Criar `.dockerignore` com exclusões apropriadas.

---

## 3. Infraestrutura e Observabilidade

### 🟡 INFRA-01 — Sem HEALTHCHECK no Dockerfile
**Arquivo:** `Dockerfile`
Nenhuma instrução `HEALTHCHECK` está definida. Orquestradores como Docker Swarm ou Kubernetes não podem verificar a saúde do container automaticamente.
**Correção sugerida:** Adicionar `HEALTHCHECK CMD curl -f http://localhost:8000/api/v1/health || exit 1`.

---

### 🟡 INFRA-02 — Sem endpoint de métricas (Prometheus)
**Arquivo:** `backend/app/main.py`
Não há instrumentação para métricas de performance (latência, throughput, erros).
**Correção sugerida:** Integrar `prometheus-fastapi-instrumentator` ou equivalente.

---

### 🟡 INFRA-03 — Sem variável de ambiente para nível de log
**Arquivo:** `backend/app/config.py`, `backend/.env.example`
O nível de logging está fixo como `INFO`. Não há como alterá-lo via variável de ambiente.
**Correção sugerida:** Adicionar `LOG_LEVEL` ao `Settings` e aplicar em `logging.basicConfig`.

---

### 🟢 INFRA-04 — Sem configuração de limites de recurso no docker-compose
**Arquivo:** `docker-compose.yml`
Nenhum limite de memória ou CPU está definido. Em caso de vazamento de memória, o container pode consumir toda a RAM do host.
**Correção sugerida:** Adicionar `mem_limit` e `cpus` ao serviço.

---

### 🟢 INFRA-05 — Sem política de restart no docker-compose
**Arquivo:** `docker-compose.yml`
Nenhuma política de reinicialização está configurada. Se o container falhar, ele não será reiniciado automaticamente.
**Correção sugerida:** Adicionar `restart: unless-stopped`.

---

## 4. Código Morto e Dependências Obsoletas

### 🟡 DEAD-01 — Dependency Injection não utilizada
**Arquivo:** `backend/app/api/dependencies.py`
O `SettingsDep` é definido mas nunca importado em nenhum endpoint. O `router.py` importa `settings` diretamente do `config.py`.
**Correção sugerida:** Remover o código morto ou migrar os endpoints para usar a injeção de dependências.

---

### 🟡 DEAD-02 — Schemas SSE definidos mas não utilizados
**Arquivo:** `backend/app/api/schemas.py`
`SSEProgress`, `SSEComplete` e `SSEError` são declarados mas o router constrói os payloads como dicts crus.
**Correção sugerida:** Utilizar os schemas definidos ou removê-los.

---

### 🟡 DEAD-03 — Materialize CSS é um framework depreciado
**Arquivo:** `frontend/index.html`
O Materialize CSS (v1.0.0, última release em 2018) está depreciado. O CSS do projeto contém mais de 50 overrides com `!important` para contornar estilos do Materialize.
**Correção sugerida:** Considerar migração para um framework mantido ou remover e usar CSS puro.

---

## 5. Cobertura de Testes — Mapa Detalhado

| Módulo | Cobertura | Nota |
|---|---|---|
| `document_parser.py` | TXT, PDF, DOCX, tamanho, formato | ✅ A |
| `schemas.py` | Parcial (clean nulls, V2 config) | ✅ B |
| `base_agent.py` | Resolução de modelos, fallbacks, parsing JSON | ✅ A |
| `router.py` | Endpoints, Pipeline, Validações, Download, SSE stream | ✅ A |
| `pdf_generator.py` | Geração de PDF, Heurísticas de idioma, Mock e real rendering | ✅ A |
| `temp_storage.py` | Registro de filas, session lifecycle, cleanup, mtime | ✅ A |
| `resume_analyst.py` | LLM invocation, mock payload, errors | ✅ A |
| `job_analyst.py` | LLM invocation, mock validation, indexing | ✅ A |
| `resume_optimizer.py` | Single/per_job modes, mock outputs, schema structures | ✅ A |
| `config.py` | Configs e definições de aliases | ✅ B |
| `main.py` | Fábrica do app e Uvicorn setup | ✅ B |

**Cobertura estimada total: ~90-95% do backend (54 testes passando).**

---

## Resumo por Severidade

| Severidade | Quantidade |
|---|---|
| 🔴 Crítico | 0 |
| 🟠 Alto | 2 |
| 🟡 Médio | 11 |
| 🟢 Baixo | 4 |
| **Total** | **17** |
