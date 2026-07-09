/**
 * api.js — ATS Optimizer API client
 * Wraps all backend endpoints with typed helpers.
 */

const BASE = '/api/v1';

const api = {

  /**
   * POST /api/v1/analyze
   * @param {File}   resumeFile  - The resume file object
   * @param {Array}  jobs        - [{title, company?, description}]
   * @param {string} outputMode  - 'single' | 'per_job'
   * @returns {Promise<{session_id, resume_analysis, job_analyses, optimizations}>}
   */
  async analyze(resumeFile, jobs, outputMode = 'single') {
    const formData = new FormData();
    formData.append('resume', resumeFile);
    formData.append('jobs', JSON.stringify(jobs));
    formData.append('output_mode', outputMode);

    const response = await fetch(`${BASE}/analyze`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      let errMsg = `Erro ${response.status}`;
      try {
        const errData = await response.json();
        errMsg = errData.detail || errData.message || errMsg;
      } catch (_) { /* ignore parse error */ }
      throw new Error(errMsg);
    }

    return response.json();
  },

  /**
   * GET /api/v1/config
   * @returns {Promise<{provider, model, max_jobs, accepted_formats}>}
   */
  async getConfig() {
    const response = await fetch(`${BASE}/config`);
    if (!response.ok) throw new Error(`Config unavailable (${response.status})`);
    return response.json();
  },

  /**
   * GET /api/v1/health
   * @returns {Promise<{status, version}>}
   */
  async checkHealth() {
    const response = await fetch(`${BASE}/health`);
    if (!response.ok) throw new Error('Backend offline');
    return response.json();
  },

  /**
   * Returns the download URL for a given session/job combo.
   * @param {string} sessionId
   * @param {number} jobIndex
   * @returns {string}
   */
  getDownloadUrl(sessionId, jobIndex) {
    return `${BASE}/download/${sessionId}/${jobIndex}`;
  },

  /**
   * Connects to the SSE progress stream for a session.
   * GET /api/v1/progress/{session_id}
   *
   * @param {string}   sessionId
   * @param {Function} onProgress  - ({step, progress, message}) => void
   * @param {Function} onComplete  - (data) => void
   * @param {Function} onError     - (errorMsg) => void
   * @returns {EventSource}        - Call .close() to disconnect
   */
  connectProgress(sessionId, onProgress, onComplete, onError) {
    const es = new EventSource(`${BASE}/progress/${sessionId}`);

    es.addEventListener('progress', (event) => {
      try {
        const data = JSON.parse(event.data);
        onProgress(data);
      } catch (err) {
        console.warn('[api] Failed to parse progress event:', err);
      }
    });

    es.addEventListener('complete', (event) => {
      es.close();
      let data = null;
      try { data = JSON.parse(event.data); } catch (_) { /* no body */ }
      onComplete(data);
    });

    es.addEventListener('error', (event) => {
      es.close();
      let msg = 'Erro durante o processamento.';
      if (event.data) {
        try {
          const parsed = JSON.parse(event.data);
          msg = parsed.message || parsed.detail || msg;
        } catch (_) {
          msg = event.data;
        }
      }
      onError(msg);
    });

    // Generic onerror (connection lost / network)
    es.onerror = () => {
      // If the browser is attempting to reconnect, let it do so without throwing a fatal error.
      if (es.readyState === EventSource.CONNECTING) {
        console.log('[api] SSE connection lost. Attempting to reconnect...');
        return;
      }
      es.close();
      onError('Conexão com o servidor perdida. Tente novamente.');
    };

    return es;
  },
};

export default api;
