# Débitos Técnicos — ATS Optimizer v1.0

> Levantamento completo de débitos técnicos identificados por análise estática e revisão de código do projeto inteiro.
> Cada item é classificado por **severidade** e **área** para facilitar a priorização em sprints futuras.

**Legenda de severidade:**
- 🔴 **Crítico** — Perda de dados ou falha em produção
- 🟠 **Alto** — Impacto direto na qualidade, manutenção ou escalabilidade
- 🟡 **Médio** — Melhoria significativa de robustez ou experiência do desenvolvedor
- 🟢 **Baixo** — Polimento, boas práticas ou melhorias cosméticas

---

## 1. Robustez e Tratamento de Erros

### 🟠 ERR-01 — Sem retry/backoff nas chamadas LLM
**Arquivo:** `backend/app/agents/base_agent.py`
O método `_invoke` não implementa lógica de retry com backoff exponencial. Erros transitórios (timeout de rede, rate limiting 429) resultam em falha imediata do pipeline inteiro.
**Correção sugerida:** Implementar retry com backoff exponencial (ex: `tenacity` ou lógica manual) para erros transitórios.

---

### 🟠 ERR-02 — Sem timeout nas chamadas LLM
**Arquivo:** `backend/app/api/router.py`
A função `_run_pipeline` executa chamadas à LLM sem timeout. Se a LLM travar, a sessão ficará pendente indefinidamente sem feedback ao usuário.
**Correção sugerida:** Envolver as chamadas em `asyncio.wait_for()` com um timeout configurável.

---

### 🟠 ERR-03 — Captura genérica de exceções (bare except)
**Arquivos:** `backend/app/api/router.py`, `backend/app/agents/base_agent.py`, `backend/app/services/pdf_generator.py`
Vários blocos `except Exception` capturam exceções amplas demais, incluindo `KeyboardInterrupt` e `SystemExit`.
**Correção sugerida:** Capturar exceções específicas e re-levantar exceções de sistema.

---

### 🟡 ERR-04 — Parsing de JSON via regex é frágil
**Arquivo:** `backend/app/agents/base_agent.py`
O fallback que tenta extrair JSON de blocos de código markdown utiliza regex, que pode casar com JSON parcial ou incompleto.
**Correção sugerida:** Utilizar um parser JSON streaming ou validar o resultado extraído com `json.loads` dentro de um try/except explícito.

---

### 🟡 ERR-05 — Sem validação programática de alucinação do otimizador
**Arquivo:** `backend/app/agents/resume_optimizer.py`
A regra de segurança de que o otimizador não deve inventar habilidades é apenas instrução no prompt. Não há verificação programática comparando skills do output com skills do input.
**Correção sugerida:** Implementar uma comparação pós-processamento que detecte habilidades adicionadas que não existem no currículo original.

---

### 🟡 ERR-06 — Continuação de execução após falha no frontend
**Arquivo:** `frontend/js/app.js`
Na função `submitForOptimization()`, se a chamada API falhar dentro do `catch`, o fluxo pode continuar executando linhas subsequentes que acessam `data.session_id` (indefinido).
**Correção sugerida:** Garantir que o `return` dentro do `catch` encerre a função completamente.

---

### 🟡 ERR-07 — Sem timeout de inatividade no SSE do frontend
**Arquivo:** `frontend/js/progress.js`
Se o servidor parar de enviar eventos (pipeline travou), o cliente aguarda indefinidamente sem feedback.
**Correção sugerida:** Implementar um timer de inatividade (ex: 120s sem eventos) que exiba um aviso ao usuário.

---

## 2. Performance

### 🟠 PERF-01 — Jinja2 Environment recriado a cada chamada
**Arquivo:** `backend/app/services/pdf_generator.py`
O `Environment` e `FileSystemLoader` do Jinja2 são instanciados a cada invocação de `generate_pdf()`. Devem ser singletons no nível do módulo.
**Correção sugerida:** Mover a instanciação para o nível do módulo como constantes.

---

### 🟠 PERF-02 — Arquivo de prompt relido do disco a cada chamada
**Arquivo:** `backend/app/agents/base_agent.py`
Cada invocação de agente relê o arquivo `.txt` do prompt do sistema de arquivos. Deveria ser cacheado em memória.
**Correção sugerida:** Utilizar `functools.lru_cache` ou carregar no `__init__` e armazenar como atributo da instância.

---

### 🟡 PERF-03 — CSS render-blocking com @import de Google Fonts
**Arquivo:** `frontend/css/style.css`
O `@import url(...)` para Google Fonts bloqueia a renderização da página.
**Correção sugerida:** Mover o carregamento de fontes para um `<link rel="preconnect">` + `<link rel="stylesheet">` no HTML.

---

### 🟡 PERF-04 — CSS não minificado (1323 linhas)
**Arquivo:** `frontend/css/style.css`
O CSS é servido como arquivo único e não minificado. Contém CSS morto (ex: classe `.ats-badge` removida do template mas ainda definida no stylesheet).
**Correção sugerida:** Remover CSS não utilizado e considerar minificação no processo de build.

## 3. Qualidade de Código e Manutenibilidade

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

## 5. Infraestrutura e Observabilidade

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

## 5. Performance Adicional

### 🟠 PERF-05 — Parsing de documentos bloqueia o event loop
**Arquivo:** `backend/app/services/document_parser.py`
As funções `_extract_from_pdf` e `_extract_from_docx` são chamadas de forma síncrona dentro de uma função `async`. Para PDFs e DOCXs grandes, isso bloqueia o event loop do asyncio, impedindo o processamento de outras requisições.
**Correção sugerida:** Executar o parsing dentro de `loop.run_in_executor()`.

---

### 🟠 PERF-06 — Sem controle de concorrência nas chamadas LLM
**Arquivo:** `backend/app/agents/resume_optimizer.py`
No modo `per_job`, todas as otimizações rodam via `asyncio.gather` sem semáforo. Com 10 vagas e múltiplas sessões simultâneas, dezenas de chamadas LLM concorrentes podem saturar a API do provedor.
**Correção sugerida:** Utilizar `asyncio.Semaphore` para limitar chamadas concorrentes.

---

## 6. Código Morto e Dependências Obsoletas

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

## 7. Cobertura de Testes — Mapa Detalhado

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

**Cobertura estimada total: ~90-95% do backend (51 testes passando).**

---

## Resumo por Severidade

| Severidade | Quantidade |
|---|---|
| 🔴 Crítico | 0 |
| 🟠 Alto | 4 |
| 🟡 Médio | 10 |
| 🟢 Baixo | 4 |
| **Total** | **18** |
