# Débitos Técnicos — ATS Optimizer v1.0

> Levantamento completo de débitos técnicos identificados por análise estática e revisão de código do projeto inteiro.
> Cada item é classificado por **severidade** e **área** para facilitar a priorização em sprints futuras.

**Legenda de severidade:**
- 🔴 **Crítico** — Risco de segurança, perda de dados ou falha em produção
- 🟠 **Alto** — Impacto direto na qualidade, manutenção ou escalabilidade
- 🟡 **Médio** — Melhoria significativa de robustez ou experiência do desenvolvedor
- 🟢 **Baixo** — Polimento, boas práticas ou melhorias cosméticas

---

## 1. Segurança

### 🔴 SEC-01 — XSS via innerHTML no frontend
**Arquivos:** `frontend/js/jobs.js`, `frontend/js/results.js`
A função `renderJobCard()` em `jobs.js` injeta os valores digitados pelo usuário (`job.title`, `job.company`, `job.description`) diretamente no DOM via template literals e `innerHTML`, sem sanitização. O mesmo padrão ocorre em `results.js` ao exibir `strengths`, `weaknesses` e `improvement_suggestions` retornados pela LLM. Se a LLM devolver conteúdo com tags HTML ou se o usuário colar código malicioso no campo de descrição de vaga, o conteúdo será executado no navegador.
**Correção sugerida:** Utilizar `textContent` para textos simples ou uma função de escape HTML antes de qualquer inserção via `innerHTML`.

---

### 🔴 SEC-02 — Chave de API armazenada como texto plano
**Arquivo:** `backend/app/config.py`
A variável `llm_api_key` é tipada como `str` simples. Pydantic recomenda o uso de `SecretStr` para evitar que o valor apareça em logs, serialização JSON ou tracebacks de erro.
**Correção sugerida:** Alterar o tipo para `SecretStr` e acessar via `.get_secret_value()`.

---

### 🔴 SEC-03 — Container Docker executa como root
**Arquivo:** `Dockerfile`
O Dockerfile não cria nem troca para um usuário não-root. Se o container for comprometido, o atacante terá permissões de root dentro do container.
**Correção sugerida:** Adicionar `RUN adduser --disabled-password appuser` e `USER appuser` antes do `CMD`.

---

### 🟠 SEC-04 — Override de segurança do Gemini excessivamente permissivo
**Arquivo:** `backend/app/agents/base_agent.py`
As configurações de segurança do Gemini são definidas como `BLOCK_NONE` para **todas** as categorias de conteúdo. Apenas as categorias relacionadas a PII (informações pessoais do candidato) deveriam ser relaxadas.
**Correção sugerida:** Manter `BLOCK_NONE` apenas para `HARM_CATEGORY_DANGEROUS_CONTENT` e categorias de PII, mantendo os filtros padrão para as demais.

---

### 🟠 SEC-05 — Ausência de SRI (Subresource Integrity) nos CDNs externos
**Arquivo:** `frontend/index.html`
Os links do Materialize CSS e Google Fonts são carregados de CDNs sem o atributo `integrity`. Se o CDN for comprometido, scripts maliciosos podem ser injetados.
**Correção sugerida:** Adicionar atributos `integrity` e `crossorigin` em todas as tags `<link>` e `<script>` externas.

---

### 🟡 SEC-06 — Ausência de validação de magic bytes nos uploads
**Arquivo:** `backend/app/services/document_parser.py`
A validação do arquivo se baseia apenas na extensão. Um arquivo `.pdf` renomeado de um executável passaria pela validação. O frontend também não verifica o MIME type (`file.type`).
**Correção sugerida:** Verificar os magic bytes do arquivo (ex: `%PDF` para PDFs, `PK` para DOCX).

---

### 🟡 SEC-07 — Sem limite de sessões concorrentes
**Arquivo:** `backend/app/api/router.py`
Os dicionários `_sessions` e `_progress_queues` crescem indefinidamente. Um ataque de negação de serviço poderia criar milhares de sessões esgotando memória e disco.
**Correção sugerida:** Implementar um limite máximo de sessões ativas e retornar `429 Too Many Requests` quando excedido.

---

## 2. Robustez e Tratamento de Erros

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

## 3. Performance

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

---

## 4. Acessibilidade (A11y)

### 🟠 A11Y-01 — Barra de progresso sem atributos ARIA
**Arquivo:** `frontend/js/progress.js`
A barra de progresso não possui `role="progressbar"`, `aria-valuenow`, `aria-valuemin` ou `aria-valuemax`. Leitores de tela não conseguem interpretar o progresso.
**Correção sugerida:** Adicionar os atributos ARIA adequados e atualizá-los dinamicamente.

---

### 🟠 A11Y-02 — Tabs de navegação sem papéis ARIA
**Arquivo:** `frontend/index.html`
A navegação por etapas (`.step-tabs`) não possui `role="tablist"`, `role="tab"` e `role="tabpanel"`.
**Correção sugerida:** Adicionar os roles ARIA apropriados e gerenciar `aria-selected`.

---

### 🟠 A11Y-03 — Ausência de estados de foco (:focus-visible)
**Arquivo:** `frontend/css/style.css`
Nenhum estilo de foco é definido para elementos interativos. Usuários de teclado não têm indicação visual de qual elemento está selecionado.
**Correção sugerida:** Adicionar estilos `:focus-visible` para botões, inputs e links.

---

### 🟡 A11Y-04 — Zona de drag-and-drop inacessível via teclado
**Arquivo:** `frontend/js/upload.js`
A área de upload por arrastar não pode ser ativada via teclado. Não há foco programático no input file oculto.
**Correção sugerida:** Tornar a área focável (`tabindex="0"`) e ativar o seletor de arquivos via `Enter`/`Space`.

---

### 🟡 A11Y-05 — Dial SVG de score sem texto alternativo
**Arquivo:** `frontend/js/results.js`
O gráfico circular SVG do score ATS não possui `aria-label` ou equivalente textual para leitores de tela.
**Correção sugerida:** Adicionar `aria-label="Pontuação ATS: XX de 100"` ao container SVG.

---

### 🟡 A11Y-06 — Contraste de cores insuficiente
**Arquivo:** `frontend/css/style.css`
A cor `--pastel-text-light: #8A8A8A` sobre fundo branco (`#FFFFFF`) provavelmente não atende o critério de contraste WCAG AA (mínimo 4.5:1).
**Correção sugerida:** Verificar com ferramenta de contraste e ajustar para pelo menos `#767676`.

---

### 🟡 A11Y-07 — Atributo `lang` ausente no HTML
**Arquivos:** `frontend/index.html`, `backend/app/templates/resume_template.html`
Nenhum dos documentos HTML possui o atributo `lang="pt-BR"`, prejudicando leitores de tela e motores de busca.
**Correção sugerida:** Adicionar `<html lang="pt-BR">`.

---

## 5. Cobertura de Testes

### 🔴 TEST-01 — Geração de PDF sem cobertura de testes
**Arquivo:** `backend/app/services/pdf_generator.py`
Nenhuma função deste módulo é testada: nem `_detect_language()`, nem `generate_pdf()`. Bugs de regressão no template ou na detecção de idioma passarão despercebidos.
**Correção sugerida:** Criar testes unitários que gerem PDFs a partir de `OptimizedResume` mockados e verifiquem a existência e integridade do arquivo.

---

### 🔴 TEST-02 — Agentes LLM sem testes com mock
**Arquivos:** `backend/app/agents/resume_analyst.py`, `job_analyst.py`, `resume_optimizer.py`
Nenhum dos três agentes possui testes unitários com mock de `litellm.acompletion`. A lógica de construção de mensagens, parsing de resposta e tratamento de erro é inteiramente não testada.
**Correção sugerida:** Criar testes com `unittest.mock.patch` sobre `litellm.acompletion` para simular respostas válidas, truncadas e malformadas.

---

### 🟠 TEST-03 — Pipeline completo sem teste de integração
**Arquivo:** `backend/app/api/router.py`
Não existe nenhum teste end-to-end que envie um currículo real, aguarde o SSE `complete` e valide o payload retornado e o PDF gerado.
**Correção sugerida:** Criar teste de integração com LLM mockada que percorra todas as etapas do pipeline.

---

### 🟠 TEST-04 — Streaming SSE sem cobertura
**Arquivo:** `backend/app/api/router.py`
O endpoint `/progress/{session_id}` não é testado. O formato dos eventos SSE, a sequência de progresso e o comportamento em caso de sessão inexistente não são verificados.
**Correção sugerida:** Implementar testes do endpoint SSE usando `httpx.AsyncClient` com stream.

---

### 🟠 TEST-05 — Limpeza de sessões temporárias sem cobertura
**Arquivo:** `backend/app/services/temp_storage.py`
A coroutine `cleanup_old_sessions()` não é testada. Não há validação de que sessões expiradas são limpas e que sessões ativas são preservadas.
**Correção sugerida:** Criar testes com diretórios mockados e timestamps manipulados.

---

### 🟡 TEST-06 — Ausência de conftest.py com fixtures reutilizáveis
**Diretório:** `backend/tests/`
Não existe `conftest.py`. Fixtures comuns como `sample_resume_text`, `sample_optimized_resume`, `mock_llm_response` e `clean_sessions` (reset de estado global) estão ausentes.
**Correção sugerida:** Criar `conftest.py` com fixtures parametrizadas.

---

### 🟡 TEST-07 — Isolamento de testes comprometido por estado global
**Arquivo:** `backend/app/api/router.py`
Os dicionários `_sessions` e `_progress_queues` são globais no módulo. Testes que criam sessões via API poluem o estado para testes subsequentes.
**Correção sugerida:** Criar fixture que resete esses dicionários entre os testes.

---

## 6. Qualidade de Código e Manutenibilidade

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

## 7. Infraestrutura e Observabilidade

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

## 8. Internacionalização (i18n)

### 🟡 I18N-01 — Strings da interface hardcoded em português
**Arquivo:** `frontend/index.html`, `frontend/js/app.js`
Todos os textos da interface estão embutidos diretamente no HTML e JS. Não há sistema de i18n para suportar outros idiomas no futuro.
**Correção sugerida:** Extrair strings para um arquivo de localização (ex: `locales/pt-BR.json`) e consumir via helper JS.

---

### 🟡 I18N-02 — Detecção de idioma do PDF baseada em heurísticas limitadas
**Arquivo:** `backend/app/services/pdf_generator.py`
A função `_detect_language()` utiliza apenas ~12 palavras por idioma para detectar português/espanhol/inglês. Currículos curtos, bilíngues ou em idiomas não suportados podem ser classificados incorretamente.
**Correção sugerida:** Utilizar uma biblioteca de detecção de idioma (ex: `langdetect`, `lingua`) ou propagar o idioma detectado pela LLM durante a análise do currículo.

---

### 🟡 I18N-03 — Meta description do HTML em inglês
**Arquivo:** `frontend/index.html`
A meta tag de descrição está em inglês ("AI-powered resume optimizer...") enquanto o público-alvo é falante de português.
**Correção sugerida:** Traduzir para português.

---

## 9. Segurança Adicional

### 🔴 SEC-08 — Path Traversal via session_id
**Arquivos:** `backend/app/services/temp_storage.py`, `backend/app/api/router.py`
O `session_id` recebido nos endpoints `/progress/{session_id}` e `/download/{session_id}/{job_index}` é concatenado diretamente ao caminho do diretório temporário via `Path(temp_dir) / session_id` sem nenhuma validação. Um `session_id` malicioso como `../../etc/passwd` poderia acessar arquivos fora do diretório temporário.
**Correção sugerida:** Validar que o `session_id` corresponde ao padrão UUID hex (`^[a-f0-9]{32}$`) antes de qualquer operação de I/O.

---

### 🟠 SEC-09 — Ausência de autenticação em todos os endpoints
**Arquivo:** `backend/app/api/router.py`
Nenhum endpoint possui autenticação (API key, JWT, OAuth). Qualquer pessoa pode submeter currículos, consumir tokens da LLM e fazer download de PDFs gerados.
**Correção sugerida:** Implementar ao menos rate limiting por IP e, idealmente, autenticação por API key para o endpoint `/analyze`.

---

### 🟠 SEC-10 — CORS excessivamente permissivo
**Arquivo:** `backend/app/main.py`
`allow_methods=["*"]` e `allow_headers=["*"]` liberam todos os métodos e cabeçalhos HTTP. Apenas `GET` e `POST` são necessários.
**Correção sugerida:** Restringir a `allow_methods=["GET", "POST"]` e `allow_headers=["Content-Type"]`.

---

### 🟡 SEC-11 — Exposição de detalhes de exceção no SSE
**Arquivo:** `backend/app/api/router.py`
O `str(exc)` da exceção capturada no pipeline é enviado diretamente ao cliente no evento SSE `error`. Isso pode expor caminhos internos, nomes de módulos e detalhes de configuração.
**Correção sugerida:** Retornar uma mensagem genérica ao cliente e logar o traceback completo internamente.

---

## 10. Performance Adicional

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

## 11. Código Morto e Dependências Obsoletas

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

## 12. Acessibilidade Adicional

### 🟡 A11Y-08 — Sem suporte a `prefers-reduced-motion`
**Arquivo:** `frontend/css/style.css`
Animações infinitas (`logoFloat`, `pulse`, `ripple`) rodam sem respeitar a preferência do sistema operacional por movimento reduzido, o que pode causar desconforto em usuários com distúrbios vestibulares.
**Correção sugerida:** Adicionar `@media (prefers-reduced-motion: reduce) { * { animation: none !important; } }`.

---

### 🟡 A11Y-09 — Ausência de `<noscript>` fallback
**Arquivo:** `frontend/index.html`
Se o JavaScript estiver desabilitado, o usuário verá uma página em branco sem nenhuma mensagem explicativa.
**Correção sugerida:** Adicionar `<noscript>` com orientação ao usuário.

---

### 🟡 A11Y-10 — Função `escapeHtml` não compartilhada entre módulos
**Arquivo:** `frontend/js/results.js`
A função `escapeHtml()` existe apenas em `results.js` e não é exportada. Outros módulos que usam `innerHTML` (`app.js`, `jobs.js`, `upload.js`) não têm acesso a ela.
**Correção sugerida:** Extrair para um módulo utilitário compartilhado (`utils.js`).

---

## 13. Cobertura de Testes — Mapa Detalhado

| Módulo | Cobertura | Nota |
|---|---|---|
| `document_parser.py` | TXT, PDF, DOCX, tamanho, formato | ✅ B+ |
| `schemas.py` | Parcial (apenas defaults de null) | ⚠️ C |
| `base_agent.py` | Mínima (model string, API key fallback) | ⚠️ D+ |
| `router.py` | Apenas validação (sem happy path, sem SSE) | ⚠️ D |
| `pdf_generator.py` | Nenhuma | ❌ F |
| `temp_storage.py` | Nenhuma | ❌ F |
| `resume_analyst.py` | Nenhuma | ❌ F |
| `job_analyst.py` | Nenhuma | ❌ F |
| `resume_optimizer.py` | Nenhuma | ❌ F |
| `config.py` | Nenhuma | ❌ F |
| `main.py` | Nenhuma | ❌ F |

**Cobertura estimada total: ~20-25% do backend.**

---

## Resumo por Severidade

| Severidade | Quantidade |
|---|---|
| 🔴 Crítico | 6 |
| 🟠 Alto | 16 |
| 🟡 Médio | 26 |
| 🟢 Baixo | 4 |
| **Total** | **52** |
