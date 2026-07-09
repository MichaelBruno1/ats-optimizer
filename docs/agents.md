# Multi-Agent Workflows

The system splits optimization reasoning across three decoupled agent modules inheriting from `BaseAgent`.

```
BaseAgent
 ├── ResumeAnalystAgent
 ├── JobAnalystAgent
 └── ResumeOptimizerAgent
```

---

## 1. BaseAgent Mechanics

The `BaseAgent` handles all external calls to the LLM via LiteLLM and abstracts the following operations:
* **Docker Network Bridging**: If the container detects that it is running inside a Docker network (`/.dockerenv` exists or `RUNNING_IN_DOCKER=true`), it rewrites localhost-bound URLs in `LLM_API_BASE` (like `localhost:11434` for Ollama) to `host.docker.internal` automatically.
* **API Key Fallback**: If no key is set in the environment but an OpenAI-compatible provider (Ollama, LM Studio) is chosen, the agent injects `"local"` as a dummy key to prevent LiteLLM errors.
* **Safety Filter Bypass**: Automatically injects safety category overrides set to `BLOCK_NONE` when invoking Gemini models. This ensures phone numbers, locations, and personal emails from candidates' profiles are processed without getting blocked by PII safety filters.

---

## 2. Agent Definitions

### 2.1 ResumeAnalystAgent
* **Scope**: Evaluates the raw resume text, compiles lists of strengths/weaknesses, and formats the structured JSON schema.
* **Linguistic Rule**: Detects the original language of the resume. ALL text values in its JSON output (such as summary, strengths, weaknesses, and recommendations) MUST be generated in that detected language.
* **Prompts Source**: [resume_analysis.txt](file:///c:/projetos/ats_optimizer/backend/app/agents/prompts/resume_analysis.txt)

### 2.2 JobAnalystAgent
* **Scope**: Parses the target job description to extract responsibilities, seniority level, and requirements.
* **Keywords Rule**: Must extract keywords exactly as they are spelt in the text (case-sensitive literal matching) since ATS parsers look for exact term occurrences.
* **Prompts Source**: [job_analysis.txt](file:///c:/projetos/ats_optimizer/backend/app/agents/prompts/job_analysis.txt)

### 2.3 ResumeOptimizerAgent
* **Scope**: Rewrites the resume bullet points to weave in the extracted job keywords.
* **Safety Guardrail**: Forbidden from inventing or generating qualifications, roles, achievements, or certifications the candidate does not have. It organizes and formats information *only*.
* **Prompts Source**: [resume_optimization.txt](file:///c:/projetos/ats_optimizer/backend/app/agents/prompts/resume_optimization.txt)
