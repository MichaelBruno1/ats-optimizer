/**
 * progress.js — SSE-driven progress updates for Step 4
 *
 * Connects to the backend EventSource, drives the progress bar,
 * status message, and step checklist.
 */

import api from './api.js';

/* ------------------------------------------------------------------ */
/*  Step mapping                                                        */
/* Ordered list used to mark checklist items as done                    */
/* ------------------------------------------------------------------ */
const STEP_ORDER = [
  'extract',
  'resume_analysis',
  'job_analysis',
  'optimization',
  'pdf_generation',
];

/** Map backend step identifiers to checklist element IDs */
const STEP_ID_MAP = {
  extract:         'check-extract',
  resume_analysis: 'check-analyze-resume',
  job_analysis:    'check-analyze-jobs',
  optimization:    'check-optimize',
  pdf_generation:  'check-generate-pdf',
};

/* ------------------------------------------------------------------ */
/*  Private state                                                       */
/* ------------------------------------------------------------------ */
let activeEventSource = null;
let completedSteps    = new Set();

/* ------------------------------------------------------------------ */
/*  DOM helpers                                                         */
/* ------------------------------------------------------------------ */

function getProgressBar()  { return document.getElementById('progress-bar'); }
function getPctLabel()     { return document.getElementById('progress-pct'); }
function getStatusMsg()    { return document.getElementById('progress-status-msg'); }
function getProgressEl()   { return document.querySelector('.progress'); }

/* ------------------------------------------------------------------ */
/*  Public: UI updaters                                                 */
/* ------------------------------------------------------------------ */

/**
 * Update the progress bar to a given percentage (0–100).
 * @param {number} pct
 */
export function updateProgressBar(pct) {
  const clamped = Math.max(0, Math.min(100, Math.round(pct)));
  const bar     = getProgressBar();
  const pctEl   = getPctLabel();
  const progEl  = getProgressEl();

  if (bar)   bar.style.width = `${clamped}%`;
  if (pctEl) pctEl.textContent = `${clamped}%`;
  if (progEl) progEl.setAttribute('aria-valuenow', clamped);
}

/**
 * Update the status text below the progress bar.
 * @param {string} msg
 */
export function updateStatusMessage(msg) {
  const el = getStatusMsg();
  if (el && msg) el.textContent = msg;
}

/**
 * Mark a checklist step as done, and advance the active indicator.
 * @param {string} step - one of STEP_ORDER values
 */
export function updateStepChecklist(step) {
  if (!STEP_ID_MAP[step]) return;
  if (completedSteps.has(step)) return;

  completedSteps.add(step);

  // Remove active-step from all
  STEP_ORDER.forEach((s) => {
    const el = document.getElementById(STEP_ID_MAP[s]);
    if (!el) return;
    el.classList.remove('active-step');
  });

  // Mark completed steps
  completedSteps.forEach((s) => {
    const el = document.getElementById(STEP_ID_MAP[s]);
    if (!el) return;
    el.classList.add('done');
    el.classList.remove('active-step');
    const icon = el.querySelector('.check-icon');
    if (icon) icon.textContent = 'check_circle';
  });

  // Activate next step
  const nextIdx = STEP_ORDER.indexOf(step) + 1;
  if (nextIdx < STEP_ORDER.length) {
    const nextStep = STEP_ORDER[nextIdx];
    if (!completedSteps.has(nextStep)) {
      const el = document.getElementById(STEP_ID_MAP[nextStep]);
      if (el) el.classList.add('active-step');
    }
  }
}

/* ------------------------------------------------------------------ */
/*  Private: reset UI to initial state                                  */
/* ------------------------------------------------------------------ */
function resetProgressUI() {
  completedSteps.clear();

  updateProgressBar(0);
  updateStatusMessage('Iniciando processamento...');

  // Reset checklist
  STEP_ORDER.forEach((step) => {
    const el = document.getElementById(STEP_ID_MAP[step]);
    if (!el) return;
    el.classList.remove('done', 'active-step');
    const icon = el.querySelector('.check-icon');
    if (icon) icon.textContent = 'radio_button_unchecked';
  });

  // Mark extract as completed immediately since it was done in POST /analyze
  completedSteps.add('extract');
  const extractEl = document.getElementById(STEP_ID_MAP['extract']);
  if (extractEl) {
    extractEl.classList.add('done');
    const icon = extractEl.querySelector('.check-icon');
    if (icon) icon.textContent = 'check_circle';
  }

  // Activate the next step (resume_analysis)
  const nextEl = document.getElementById(STEP_ID_MAP['resume_analysis']);
  if (nextEl) nextEl.classList.add('active-step');

  // Hide error card
  const errCard = document.getElementById('processing-error');
  if (errCard) errCard.hidden = true;
}

/* ------------------------------------------------------------------ */
/*  Public: show error inside step 4                                    */
/* ------------------------------------------------------------------ */
export function showProcessingError(msg) {
  const errCard = document.getElementById('processing-error');
  const errMsg  = document.getElementById('processing-error-msg');
  if (errCard) errCard.hidden = false;
  if (errMsg && msg) errMsg.textContent = msg;
}

/* ------------------------------------------------------------------ */
/*  Public: start SSE connection                                        */
/* ------------------------------------------------------------------ */

/**
 * Connect to SSE for sessionId and drive the progress UI.
 *
 * @param {string}   sessionId
 * @param {Function} onComplete - called with final result data
 * @param {Function} onError    - called with error message string
 * @returns {void}
 */
export function startProgress(sessionId, onComplete, onError) {
  // Close any previous connection
  stopProgress();
  resetProgressUI();

  let hasFinished = false;

  activeEventSource = api.connectProgress(
    sessionId,

    // onProgress
    ({ step, progress, message }) => {
      if (hasFinished) return;
      if (typeof progress === 'number') updateProgressBar(progress);
      if (message) updateStatusMessage(message);
      if (step)    updateStepChecklist(step);
    },

    // onComplete
    (data) => {
      if (hasFinished) return;
      hasFinished = true;
      // Mark all steps done and fill bar
      STEP_ORDER.forEach(updateStepChecklist);
      updateProgressBar(100);
      updateStatusMessage('Otimização concluída!');
      activeEventSource = null;

      // Small delay for visual feedback
      setTimeout(() => onComplete(data), 600);
    },

    // onError
    (errMsg) => {
      if (hasFinished) return;
      hasFinished = true;
      activeEventSource = null;
      showProcessingError(errMsg);
      onError(errMsg);
    },
  );
}

/**
 * Disconnect the EventSource (if active).
 */
export function stopProgress() {
  if (activeEventSource) {
    activeEventSource.close();
    activeEventSource = null;
  }
}
