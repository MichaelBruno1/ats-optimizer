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
        Backend_Router[api/router.py] -->|4. Launch Task| Graph_Pipeline[graph/pipeline.py]
        Backend_Router -->|5. Stream Events| SSE_Client
        
        Graph_Pipeline -->|6. Execute Graph| Graph_Nodes[graph/nodes.py]
        Graph_Nodes -->|7. Parse Bytes| Doc_Parser[document_parser.py]
        Graph_Nodes -->|8. Invoke| Resume_Analyst[ResumeAnalystAgent]
        Graph_Nodes -->|9. Invoke| Job_Analyst[JobAnalystAgent]
        Graph_Nodes -->|10. Invoke| Resume_Optimizer[ResumeOptimizerAgent]
        Graph_Nodes -->|11. Render PDF| PDF_Gen[pdf_generator.py]
        
        PDF_Gen -->|12. Write HTML/CSS| WeasyPrint[WeasyPrint engine]
        WeasyPrint -->|13. Write PDF| Temp_Store[temp_storage.py]
    end

    subgraph LLM Gateway [LiteLLM Provider Manager]
        Resume_Analyst & Job_Analyst & Resume_Optimizer -->|REST API| LiteLLM[LiteLLM wrapper]
        LiteLLM -->|openai/gemini/ollama| External_API[LLM Gateway / Ollama Host]
    end

    Temp_Store -->|14. Read FileResponse| Backend_Router
```

## 2. Key Architecture Points
* **LangGraph Multi-Agent Orchestration**: The pipeline execution is orchestrated using a state graph (`app/graph`), enabling parallel agent execution (fan-out), explicit error routing via conditional edges, and reusable subgraphs.
* **Asynchronous Execution Pattern**: The API router receives requests, immediately spins off a background task running `run_graph_pipeline`, and returns a session token. The client monitors state in real-time via Server-Sent Events (SSE).
* **Temporary State Storage**: Optimizations are session-scoped and stored inside `/tmp/{session_id}`. No database is required, and data is kept ephemeral.
* **LLM Abstraction Layer**: By using LiteLLM, the backend remains agnostic to the upstream provider, allowing developers to switch between OpenAI, Vertex AI, Gemini, or local gateways by simply altering environment variables.
