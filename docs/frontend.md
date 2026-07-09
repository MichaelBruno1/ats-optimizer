# Frontend SPA Architecture

The client side is implemented as a modern single-page application (SPA) without structural frameworks (Vanilla JS, HTML5, and CSS3). It uses Materialize CSS for grid and input components.

---

## 1. Step Wizard flow
The interface acts as a 5-step wizard, making only one step visible at a time:
* **Step 1: Upload**: Drag and drop zone with client-side file size verification (max 5MB) and whitelist checks (`.pdf`, `.docx`, `.txt`).
* **Step 2: Vacancies**: Dynamic listing form. Allows typing a title, company, and description (max 5000 chars) for up to 10 jobs.
* **Step 3: Output Mode**: Selector card between "Single Resume" (combined optimization) and "Per-Job Resumes" (individual files).
* **Step 4: Processing**: Connects to the SSE endpoint. Displays a progress bar and checklists as checkpoints complete.
* **Step 5: Results**: Displays the circular ATS score chart, strengths/weaknesses grids, accordion analysis for missing keywords, and download links.

---

## 2. EventSource (SSE) Handling (`api.js` & `progress.js`)

* **Silent Reconnection**: When the connection is interrupted or times out during long LLM inferences, the browser attempts to reconnect automatically, firing the EventSource `onerror` handler. The client in `api.js` checks the `readyState` parameter. If it is `CONNECTING`, it ignores the error and lets the browser reconnect silently without showing a user alert.
* **State Flag Protection**: Keeps a `hasFinished` boolean flag in `progress.js`. Once a pipeline completes or hits a terminal failure, the flag is set to `true`. This prevents subsequent generic disconnection events from displaying error cards or alerts.
