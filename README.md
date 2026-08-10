# ATS Optimizer — Arquitetura Multiagente com LangGraph

> Mecanismo avançado de otimização de currículos baseado em IA com arquitetura **Multiagente baseada em LangGraph**, ontologia de habilidades, matching determinístico, avaliação de elegibilidade, cálculo de score por código e loop controlado de validação ATS anti-alucinação.

---

## Funcionalidades

- 📄 **Leitura de Currículos** — Suporta formatos PDF, DOCX e TXT com detecção de OCR e metadados.
- 🔍 **Estruturação Semântica** — Converte currículos e vagas em modelos de domínio fortemente tipados (`StructuredResume` e `StructuredJob`).
- 🏷️ **Ontologia e Normalização de Skills** — Normalização determinística baseada em regras, aliases (AWS, Postgres, K8s, etc.), taxonomia e similaridade.
- 🎯 **Matching Engine com Evidências** — Estados explícitos (`MATCH`, `PARTIAL`, `NOT_FOUND`, `CONFLICT`, `UNKNOWN`) com citação da origem da evidência.
- 🧮 **Scoring ATS Determinístico** — Pontuação calculada 100% por código (Fórmula: Keywords 25%, Skills 25%, Experiência 20%, Responsabilidades 15%, Senioridade 10%, Educação 5%).
- ⚖️ **Elegibilidade vs Ranking** — Avaliação de critérios eliminatórios (`PASS`/`FAIL`) isolada da pontuação numérica (0-100).
- 📋 **Optimization Planner** — Plano estratégico de ação por seção antes de alterar o currículo.
- ✨ **Otimização sem Alucinações** — Agente especialista aplicando a fórmula XYZ com filtro programático estrito anti-alucinação.
- 🛡️ **ATS & Anti-Hallucination Validator** — Validação híbrida (programática e semântica) com loop de otimização condicional (máximo de 3 iterações).
- 📥 **Exportação para PDF** — PDF profissional A4 gerado via WeasyPrint + Jinja2 com suporte a multi-idioma (pt, es, en).
- 📡 **Progresso em Tempo Real** — Server-Sent Events (SSE) informando cada etapa do LangGraph ao vivo.

---

## Arquitetura LangGraph

```text
                INPUT (CV + Vagas)
                        │
          ┌─────────────┴─────────────┐
          ▼                           ▼
    CV Structurer                Job Analyzer
          │                           │
          └─────────────┬─────────────┘
                        ▼
                 Skill Ontology
                        │
                        ▼
                 Matching Engine
            (Score & Eligibility Code)
                        │
             ┌──────────┴──────────┐
             ▼                     ▼
         Strengths               Gaps
             │                     │
             └──────────┬──────────┘
                        ▼
              Optimization Planner
                        │
                        ▼
               Resume Optimizer
                        │
                        ▼
                 ATS Validator
                        │
             ┌──────────┴──────────┐
             │                     │
            FAIL                  PASS
     (iter < 3)                    │
             │                     ▼
             └──► Loop Optimizer OUTPUT (PDFs)
```

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
        ├── main.py              # Aplicação FastAPI e rotinas de lifespan
        ├── config.py            # Configurações via BaseSettings
        ├── domain/              # Modelos de domínio (Resume, Job, Matching, Scoring, Eligibility, Optimization, Validation)
        ├── llm/                 # Provedor de LLM abstrato (LiteLLM, Structured Output, Prompts)
        ├── services/            # Serviços de negócio (DocumentParser, SkillNormalization, MatchingEngine, Scoring, Eligibility, ATSValidator)
        ├── agents/              # Agentes especialistas (CVStructurer, JobAnalyst, StrengthGap, Planner, Optimizer, Validator)
        ├── graph/               # Grafo LangGraph (ResumeState, Routing, Nodes, Pipeline)
        ├── api/                 # Endpoints REST e schemas da API pública
        └── templates/           # Template HTML Jinja2 para WeasyPrint
```

---

## Executando os Testes

Para rodar a suíte completa de testes unitários e de integração:

```bash
cd backend
.venv\Scripts\pytest -v
```

---

## Licença e Uso

Desenvolvido para otimização profissional de currículos e aderência técnica aos sistemas ATS.
