# System Architecture

The **ATS Optimizer** application is designed around a clean decoupling of the client interface (Vanilla ES6+ SPA) and backend services (FastAPI), running inside a unified Docker container environment.

## 1. Architectural Overview

```mermaid
graph TD
    subgraph Frontend [Browser - Step 1-5 Wizard]
        UI[HTML5 / CSS3 / JS] -->|1. Upload File & Jobs| API_Client[api.js]
        API_Client -->|2. POST /analyze| Backend_Router
        UI -->|3. SSE /progress| SSE_Client[progress.js]
    end

    subgraph Backend [FastAPI Application]
        Backend_Router[api/router.py] -->|4. Launch Task| Pipeline_Task[_run_pipeline]
        Backend_Router -->|5. Stream Events| SSE_Client
        
        Pipeline_Task -->|6. Parse Bytes| Doc_Parser[document_parser.py]
        Pipeline_Task -->|7. Invoke| Resume_Analyst[ResumeAnalystAgent]
        Pipeline_Task -->|8. Invoke| Job_Analyst[JobAnalystAgent]
        Pipeline_Task -->|9. Invoke| Resume_Optimizer[ResumeOptimizerAgent]
        Pipeline_Task -->|10. Render PDF| PDF_Gen[pdf_generator.py]
        
        PDF_Gen -->|11. Write HTML/CSS| WeasyPrint[WeasyPrint engine]
        WeasyPrint -->|12. Write PDF| Temp_Store[temp_storage.py]
    end

    subgraph LLM Gateway [LiteLLM Provider Manager]
        Resume_Analyst & Job_Analyst & Resume_Optimizer -->|REST API| LiteLLM[LiteLLM wrapper]
        LiteLLM -->|openai/gemini/ollama| External_API[LLM Gateway / Ollama Host]
    end

    Temp_Store -->|13. Read FileResponse| Backend_Router
```

## 2. Key Architecture Points
* **Asynchronous Execution Pattern**: The API router receives requests, immediately spins off a background task to process the pipeline, and returns a session token. The client then monitors the task state in real-time via Server-Sent Events (SSE).
* **Temporary State Storage**: Optimizations are session-scoped and stored inside `/tmp/{session_id}`. No database is required, and data is kept ephemeral.
* **LLM Abstraction Layer**: By using LiteLLM, the backend remains agnostic to the upstream provider, allowing developers to switch between OpenAI, Vertex AI, Gemini, or local gateways by simply altering environment variables.
