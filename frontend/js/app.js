/**
 * app.js — ATS Optimizer main orchestrator
 *
 * Manages global state, wizard step transitions, and wires
 * all modules together.
 */

import api                    from './api.js';
import { initUpload, getFile, clearFile } from './upload.js';
import { initJobs, addJob, getJobs, validateJobs, hasValidJob, onJobsChange } from './jobs.js';
import { startProgress, stopProgress }    from './progress.js';
import { renderResults }                  from './results.js';

/* ================================================================== */
/*  Global application state                                           */
/* ================================================================== */
const state = {
  currentStep:    1,
  resumeFile:     null,
  jobs:           [],
  outputMode:     'single',
  sessionId:      null,
  analysisResults: null,
  config:          null,
};

/* ================================================================== */
/*  Step Navigation                                                    */
/* ================================================================== */

/**
 * Transition the wizard to step `n`.
 * Applies CSS animation classes and updates the stepper nav.
 * @param {number} n - target step (1–5)
 */
function goToStep(n) {
  if (n === state.currentStep) return;

  const currentEl = document.getElementById(`step-${state.currentStep}`);
  const targetEl  = document.getElementById(`step-${n}`);

  if (currentEl) {
    currentEl.classList.remove('active');
    currentEl.style.display = 'none';
  }

  if (targetEl) {
    targetEl.style.display = 'block';
    // Allow display:block to take effect before adding animation class
    requestAnimationFrame(() => {
      targetEl.classList.add('active');
    });
  }

  state.currentStep = n;
  updateStepper(n);
  scrollToTop();
}

function scrollToTop() {
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

/* ================================================================== */
/*  Stepper UI                                                         */
/* ================================================================== */

function updateStepper(currentStep) {
  const stepper = document.getElementById('stepper');
  if (!stepper) return;

  // Show/hide stepper on step 5
  stepper.style.display = currentStep === 5 ? 'none' : 'flex';

  const indicators  = stepper.querySelectorAll('.step-indicator');
  const connectors  = stepper.querySelectorAll('.step-connector');

  indicators.forEach((ind, idx) => {
    const stepNum = idx + 1;
    ind.classList.remove('active', 'completed');

    if (stepNum < currentStep) {
      ind.classList.add('completed');
      ind.innerHTML = '<span class="material-icons" style="font-size:16px">check</span>';
    } else if (stepNum === currentStep) {
      ind.classList.add('active');
      ind.textContent = stepNum;
    } else {
      ind.textContent = stepNum;
    }
  });

  connectors.forEach((con, idx) => {
    // Connector after indicator (idx+1) is "completed" if step (idx+1) is done
    con.classList.toggle('completed', idx + 1 < currentStep);
  });
}

/* ================================================================== */
/*  Step 1 — Upload                                                    */
/* ================================================================== */

function setupStep1() {
  const btnNext = document.getElementById('btn-step1-next');

  // Listen for file events from upload.js
  document.addEventListener('resumeSelected', (e) => {
    state.resumeFile = e.detail.file;
    btnNext.disabled = false;
    btnNext.setAttribute('aria-disabled', 'false');
  });

  document.addEventListener('resumeCleared', () => {
    state.resumeFile = null;
    btnNext.disabled = true;
    btnNext.setAttribute('aria-disabled', 'true');
  });

  btnNext.addEventListener('click', () => {
    if (!state.resumeFile) return;
    goToStep(2);
  });
}

/* ================================================================== */
/*  Step 2 — Jobs                                                      */
/* ================================================================== */

function setupStep2() {
  const btnBack = document.getElementById('btn-step2-back');
  const btnNext = document.getElementById('btn-step2-next');

  btnBack.addEventListener('click', () => goToStep(1));

  // Enable/disable Next based on job validity
  onJobsChange(() => {
    const valid = hasValidJob();
    btnNext.disabled = !valid;
    btnNext.setAttribute('aria-disabled', !valid);
  });

  btnNext.addEventListener('click', () => {
    if (!validateJobs()) return;
    state.jobs = getJobs();
    goToStep(3);
  });
}

/* ================================================================== */
/*  Step 3 — Output Mode                                              */
/* ================================================================== */

function setupStep3() {
  const btnBack     = document.getElementById('btn-step3-back');
  const btnOptimize = document.getElementById('btn-optimize');
  const cardSingle  = document.getElementById('mode-card-single');
  const cardPerJob  = document.getElementById('mode-card-per-job');

  btnBack.addEventListener('click', () => goToStep(2));

  function selectMode(mode) {
    state.outputMode = mode;

    if (mode === 'single') {
      cardSingle.classList.add('selected');
      cardSingle.setAttribute('aria-checked', 'true');
      cardPerJob.classList.remove('selected');
      cardPerJob.setAttribute('aria-checked', 'false');
    } else {
      cardPerJob.classList.add('selected');
      cardPerJob.setAttribute('aria-checked', 'true');
      cardSingle.classList.remove('selected');
      cardSingle.setAttribute('aria-checked', 'false');
    }
  }

  cardSingle.addEventListener('click',   () => selectMode('single'));
  cardPerJob.addEventListener('click',   () => selectMode('per_job'));

  cardSingle.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); selectMode('single'); }
  });
  cardPerJob.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); selectMode('per_job'); }
  });

  btnOptimize.addEventListener('click', () => handleAnalyze());
}

/* ================================================================== */
/*  Step 4 — Processing                                               */
/* ================================================================== */

function setupStep4() {
  const btnRetry = document.getElementById('btn-retry');
  btnRetry?.addEventListener('click', () => {
    goToStep(3);
  });
}

/* ================================================================== */
/*  Step 5 — Results                                                   */
/* ================================================================== */

function setupStep5() {
  const btnNewAnalysis = document.getElementById('btn-new-analysis');
  btnNewAnalysis?.addEventListener('click', () => resetApp());
}

/* ================================================================== */
/*  Main analyze flow                                                   */
/* ================================================================== */

async function handleAnalyze() {
  // Ensure jobs are up-to-date
  state.jobs = getJobs();

  if (!state.resumeFile) {
    showToast('Por favor, selecione um currículo primeiro.', 'error');
    goToStep(1);
    return;
  }

  if (state.jobs.length === 0) {
    showToast('Adicione pelo menos uma vaga.', 'error');
    goToStep(2);
    return;
  }

  // Move to processing step
  goToStep(4);

  try {
    // Submit the analysis request
    const response = await api.analyze(state.resumeFile, state.jobs, state.outputMode);
    state.sessionId      = response.session_id;
    state.analysisResults = response;

    if (state.sessionId) {
      // Connect SSE progress stream with dynamic timeout
      const timeoutLimit = (state.config && typeof state.config.llm_timeout === 'number')
        ? state.config.llm_timeout
        : 120;

      startProgress(
        state.sessionId,
        handleComplete,   // onComplete
        handleError,      // onError
        timeoutLimit,     // Dynamic timeout in seconds
      );
    } else {
      // Backend returned result synchronously (no SSE session)
      handleComplete(response);
    }
  } catch (err) {
    handleError(err.message || 'Erro ao iniciar a análise.');
    return;
  }
}

function handleComplete(resultData) {
  // Extract nested result object from complete event payload, if present
  let data = null;
  if (resultData && resultData.result) {
    data = resultData.result;
  } else {
    data = resultData || state.analysisResults;
  }

  if (!data || !data.resume_analysis) {
    handleError('Nenhum resultado de análise válido recebido do servidor.');
    return;
  }

  state.analysisResults = data;

  // Render results then navigate
  renderResults(data, state.outputMode, state.jobs);
  goToStep(5);
}

function handleError(msg) {
  console.error('[ATS Optimizer] Error:', msg);
  showToast(msg, 'error');
  // Error card is shown inside step 4 by progress.js
}

/* ================================================================== */
/*  Reset                                                              */
/* ================================================================== */

function resetApp() {
  stopProgress();

  // Reset state
  state.currentStep    = 1;
  state.resumeFile     = null;
  state.jobs           = [];
  state.outputMode     = 'single';
  state.sessionId      = null;
  state.analysisResults = null;

  // Reset upload
  clearFile();

  // Reset jobs — remove all cards and reinit
  const jobsList = document.getElementById('jobs-list');
  if (jobsList) jobsList.innerHTML = '';
  addJob(); // seed first card

  // Reset mode card selection
  const cardSingle = document.getElementById('mode-card-single');
  const cardPerJob = document.getElementById('mode-card-per-job');
  cardSingle?.classList.add('selected');
  cardSingle?.setAttribute('aria-checked', 'true');
  cardPerJob?.classList.remove('selected');
  cardPerJob?.setAttribute('aria-checked', 'false');

  // Clear results section HTML
  const analysisColumns  = document.getElementById('analysis-columns');
  const jobsAccordion    = document.getElementById('jobs-accordion');
  const downloadsContainer = document.getElementById('downloads-container');
  if (analysisColumns)    analysisColumns.innerHTML   = '';
  if (jobsAccordion)      jobsAccordion.innerHTML     = '';
  if (downloadsContainer) downloadsContainer.innerHTML = '';

  // Reset score circle
  const fgCircle = document.getElementById('score-fg-circle');
  if (fgCircle) fgCircle.style.strokeDashoffset = '364.42';
  const scoreNum = document.getElementById('ats-score-number');
  if (scoreNum) scoreNum.textContent = '0';

  // Navigate to step 1
  // Manually set all steps hidden first
  [1, 2, 3, 4, 5].forEach(n => {
    const el = document.getElementById(`step-${n}`);
    if (el) { el.classList.remove('active'); el.style.display = 'none'; }
  });
  state.currentStep = 0; // force goToStep to transition
  goToStep(1);

  // Re-enable Next button on step 1 (will be disabled after file cleared)
  const btnNext1 = document.getElementById('btn-step1-next');
  if (btnNext1) { btnNext1.disabled = true; btnNext1.setAttribute('aria-disabled', 'true'); }
}

/* ================================================================== */
/*  Toast helper (Materialize)                                         */
/* ================================================================== */
function showToast(msg, type = 'info') {
  const colorMap = {
    error:   'background-color:var(--pastel-error);color:#5a2020',
    success: 'background-color:var(--pastel-success);color:#1a4a17',
    warning: 'background-color:var(--pastel-warning);color:#5a3d00',
    info:    'background-color:var(--pastel-primary);color:#fff',
  };
  const style = colorMap[type] || colorMap.info;
  M.toast({
    html: `<span style="font-family:Inter,sans-serif;font-size:0.88rem;font-weight:500">${msg}</span>`,
    displayLength: 4000,
    classes: '',
    completeCallback: null,
  });
  // Apply custom style to the last toast
  setTimeout(() => {
    const toasts = document.querySelectorAll('.toast');
    const last = toasts[toasts.length - 1];
    if (last) last.setAttribute('style', `${style};border-radius:12px;box-shadow:0 4px 16px rgba(0,0,0,0.12)`);
  }, 10);
}

/* ================================================================== */
/*  Config loading                                                      */
/* ================================================================== */
async function loadConfig() {
  try {
    state.config = await api.getConfig();

    const infoEl   = document.getElementById('config-info');
    const textEl   = document.getElementById('config-info-text');

    if (infoEl && textEl && state.config) {
      const { provider, model, max_jobs, accepted_formats } = state.config;
      const parts = [];
      if (provider && model) parts.push(`${provider} / ${model}`);
      if (max_jobs)          parts.push(`Máx. ${max_jobs} vagas`);
      if (accepted_formats)  parts.push(`Formatos: ${accepted_formats.join(', ')}`);
      if (parts.length) {
        textEl.textContent = parts.join(' · ');
        infoEl.hidden = false;
      }
    }
  } catch (_) {
    // Config is optional — fail silently
  }
}

/* ================================================================== */
/*  Initialisation                                                      */
/* ================================================================== */

async function init() {
  // Init sub-modules
  initUpload();
  initJobs();

  // Setup step handlers
  setupStep1();
  setupStep2();
  setupStep3();
  setupStep4();
  setupStep5();

  // Load config from backend (optional)
  loadConfig();

  // Show step 1
  goToStep(1);
}

// Bootstrap when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
