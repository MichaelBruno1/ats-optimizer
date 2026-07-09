# API Contracts

All backend endpoints are hosted under the `/api/v1` namespace.

---

## 1. Endpoints

### 1.1 `POST /api/v1/analyze`
Submits the candidate's resume and a set of target job descriptions for optimization. Launches the background pipeline asynchronously.

* **Request Content-Type**: `multipart/form-data`
* **Form Arguments**:
  * `resume`: File binary (`.pdf`, `.docx`, `.txt`) — Max size limit: `5MB`.
  * `jobs`: JSON-serialized array of target job metadata. Max: 10 items.
    ```json
    [
      {
        "title": "Senior Backend Developer",
        "company": "Enterprise Tech",
        "description": "Requires strong expertise in Python, FastAPI, and dockerizing..."
      }
    ]
    ```
  * `output_mode`: Enforced enum: `single` | `per_job`.
* **Success Response (200 OK)**:
  ```json
  {
    "session_id": "8a3cf12d1b824a739ef0e3c15...",
    "message": "Processing started. Connect to the SSE endpoint for progress."
  }
  ```
* **Error Validation (422 Unprocessable Entity)**:
  Returned for file size limit exceeded, unwhitelisted document formats, or missing required fields.

---

### 1.2 `GET /api/v1/progress/{session_id}`
Initiates a long-running Server-Sent Events (SSE) HTTP stream. The client receives progress notifications as the pipeline executes in the background.

* **Response Headers**:
  * `Content-Type: text/event-stream`
  * `Cache-Control: no-cache`
* **Available Event Names**:
  * **`progress`**: Emitted when pipeline checkpoints are completed.
    ```json
    {
      "step": "analyzing_resume",
      "progress": 30,
      "message": "Analisando perfil do currículo..."
    }
    ```
  * **`complete`**: Emitted when all files are processed and PDFs are generated. Returns the full JSON results payload.
    ```json
    {
      "progress": 100,
      "message": "Otimização concluída!",
      "session_id": "8a3cf12...",
      "result": {
        "session_id": "8a3cf12...",
        "resume_analysis": { ... },
        "job_analyses": [ ... ],
        "optimizations": [ ... ]
      }
    }
    ```
  * **`error`**: Emitted if any critical exception occurs inside the pipeline thread. Closes the stream.
    ```json
    {
      "message": "Pipeline failed: Conexão com o LLM recusada."
    }
    ```

---

### 1.3 `GET /api/v1/download/{session_id}/{job_index}`
Downloads the generated optimized PDF resume.

* **Response Content-Type**: `FileResponse` (`application/pdf`)
* **Errors**:
  * `404 Not Found`: Session ID does not exist, or index is outside bounds.

---

### 1.4 `GET /api/v1/health`
Displays service state.
```json
{
  "status": "healthy",
  "llm_provider": "openai",
  "model": "google/gemma-4-e4b"
}
```

---

### 1.5 `GET /api/v1/config`
Exposes active limits and permitted parameters.
```json
{
  "provider": "openai",
  "model": "google/gemma-4-e4b",
  "max_jobs": 10,
  "accepted_formats": [".pdf", ".docx", ".txt"]
}
```
