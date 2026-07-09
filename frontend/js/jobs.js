/**
 * jobs.js — Job card management for Step 2
 *
 * Manages dynamic job cards with real-time validation,
 * char counters, and a public API consumed by app.js.
 */

const MAX_JOBS = 3;
const MAX_CHARS = 4000;

/* ------------------------------------------------------------------ */
/*  Private state                                                       */
/* ------------------------------------------------------------------ */
let jobsListEl;
let jobsCountEl;
let btnAddJobEl;
let validationMsgEl;
let onChangeCallback = null; // called whenever job list changes

let jobIdCounter = 0; // incremental ID for each card

/* ------------------------------------------------------------------ */
/*  Internal helpers                                                    */
/* ------------------------------------------------------------------ */

function getJobCards() {
  return Array.from(jobsListEl.querySelectorAll('.job-card'));
}

function getJobCount() {
  return getJobCards().length;
}

function updateCountLabel() {
  const count = getJobCount();
  if (jobsCountEl) jobsCountEl.textContent = count;

  if (btnAddJobEl) {
    const disabled = count >= MAX_JOBS;
    btnAddJobEl.disabled = disabled;
    btnAddJobEl.setAttribute('aria-disabled', disabled);
  }
}

function updateEmptyHint() {
  let hint = jobsListEl.querySelector('.empty-jobs-hint');
  if (getJobCount() === 0) {
    if (!hint) {
      hint = document.createElement('div');
      hint.className = 'empty-jobs-hint';
      hint.innerHTML = `
        <span class="material-icons">work_outline</span>
        Adicione pelo menos uma vaga para continuar
      `;
      jobsListEl.appendChild(hint);
    }
  } else {
    hint?.remove();
  }
}

function notifyChange() {
  updateCountLabel();
  updateEmptyHint();
  if (typeof onChangeCallback === 'function') onChangeCallback();
}

/** Show validation message below the list */
function setValidationMsg(msg) {
  if (validationMsgEl) {
    validationMsgEl.innerHTML = msg
      ? `<span class="material-icons" style="font-size:14px">error_outline</span> ${msg}`
      : '';
  }
}

/* ------------------------------------------------------------------ */
/*  Card building                                                       */
/* ------------------------------------------------------------------ */

function buildJobCard(index, cardId) {
  const card = document.createElement('div');
  card.className = 'job-card';
  card.dataset.cardId = cardId;
  card.setAttribute('role', 'listitem');
  card.setAttribute('aria-label', `Vaga ${index}`);

  card.innerHTML = `
    <div class="job-card-header">
      <span class="job-card-title">
        <span class="material-icons">work_outline</span>
        Vaga ${index}
      </span>
      <button class="btn-icon btn-remove-job waves-effect" type="button"
              aria-label="Remover vaga ${index}" data-card-id="${cardId}"
              ${index === 1 ? 'style="visibility:hidden"' : ''}>
        <span class="material-icons">delete_outline</span>
      </button>
    </div>

    <div class="field-group">
      <label class="field-label" for="job-title-${cardId}">
        Título da Vaga <span style="color:var(--pastel-error)">*</span>
      </label>
      <input
        type="text"
        id="job-title-${cardId}"
        class="job-input job-title-input"
        placeholder="Ex: Desenvolvedor Frontend Senior"
        maxlength="200"
        aria-required="true"
        autocomplete="off"
      />
    </div>

    <div class="field-group">
      <label class="field-label" for="job-company-${cardId}">
        Empresa <span class="field-optional">(opcional)</span>
      </label>
      <input
        type="text"
        id="job-company-${cardId}"
        class="job-input job-company-input"
        placeholder="Ex: Google, Nubank, Startup XYZ"
        maxlength="100"
        autocomplete="organization"
      />
    </div>

    <div class="field-group">
      <label class="field-label" for="job-desc-${cardId}">
        Descrição da Vaga <span style="color:var(--pastel-error)">*</span>
      </label>
      <textarea
        id="job-desc-${cardId}"
        class="job-textarea job-desc-input"
        placeholder="Cole aqui a descrição completa da vaga. Quanto mais detalhada, melhor a otimização..."
        rows="4"
        maxlength="${MAX_CHARS}"
        aria-required="true"
      ></textarea>
      <p class="char-counter" id="char-counter-${cardId}">0 / ${MAX_CHARS}</p>
    </div>
  `;

  /* Remove button */
  const removeBtn = card.querySelector('.btn-remove-job');
  removeBtn.addEventListener('click', () => {
    removeJobByCardId(cardId);
  });

  /* Char counter for textarea */
  const textarea = card.querySelector('.job-desc-input');
  const counter  = card.querySelector(`#char-counter-${cardId}`);

  textarea.addEventListener('input', () => {
    const len = textarea.value.length;
    counter.textContent = `${len} / ${MAX_CHARS}`;

    counter.classList.remove('near-limit', 'at-limit');
    if (len >= MAX_CHARS)           counter.classList.add('at-limit');
    else if (len >= MAX_CHARS * 0.9) counter.classList.add('near-limit');

    setValidationMsg('');
    notifyChange();
  });

  /* Title input triggers notifyChange */
  card.querySelector('.job-title-input').addEventListener('input', () => {
    setValidationMsg('');
    notifyChange();
  });

  return card;
}

/** Re-number visible cards (title + remove-btn visibility) */
function reindexCards() {
  const cards = getJobCards();
  cards.forEach((card, idx) => {
    const num = idx + 1;
    card.setAttribute('aria-label', `Vaga ${num}`);

    const title = card.querySelector('.job-card-title');
    if (title) {
      title.innerHTML = `<span class="material-icons">work_outline</span> Vaga ${num}`;
    }

    const removeBtn = card.querySelector('.btn-remove-job');
    if (removeBtn) {
      // First card remove button is always hidden
      removeBtn.style.visibility = num === 1 ? 'hidden' : 'visible';
      removeBtn.setAttribute('aria-label', `Remover vaga ${num}`);
    }
  });
}

/* ------------------------------------------------------------------ */
/*  Public API                                                          */
/* ------------------------------------------------------------------ */

/**
 * Add a new (empty) job card.
 * @returns {number|null} New card ID, or null if at limit.
 */
export function addJob() {
  if (getJobCount() >= MAX_JOBS) return null;

  jobIdCounter++;
  const index = getJobCount() + 1;
  const card = buildJobCard(index, jobIdCounter);
  jobsListEl.appendChild(card);

  // Scroll new card into view
  card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

  notifyChange();
  return jobIdCounter;
}

/**
 * Remove a job card by its internal card ID.
 * @param {number} cardId
 */
export function removeJobByCardId(cardId) {
  const card = jobsListEl.querySelector(`[data-card-id="${cardId}"]`);
  if (!card) return;

  // Animate out
  card.style.transition = 'opacity 0.2s ease, transform 0.2s ease, max-height 0.3s ease, margin 0.3s ease, padding 0.3s ease';
  card.style.opacity = '0';
  card.style.transform = 'scale(0.97)';
  card.style.overflow = 'hidden';
  card.style.maxHeight = card.offsetHeight + 'px';

  requestAnimationFrame(() => {
    card.style.maxHeight = '0';
    card.style.marginBottom = '0';
    card.style.paddingTop = '0';
    card.style.paddingBottom = '0';
  });

  card.addEventListener('transitionend', () => {
    card.remove();
    reindexCards();
    notifyChange();
  }, { once: true });
}

/**
 * Remove a job card by visible index (1-based).
 * @param {number} index
 */
export function removeJob(index) {
  const cards = getJobCards();
  const card = cards[index - 1];
  if (!card) return;
  const cardId = Number(card.dataset.cardId);
  removeJobByCardId(cardId);
}

/**
 * Return an array of job objects from the current cards.
 * Only returns cards that have at least title and description.
 * @returns {Array<{title, company, description}>}
 */
export function getJobs() {
  return getJobCards().map((card) => {
    const title       = card.querySelector('.job-title-input')?.value.trim()   ?? '';
    const company     = card.querySelector('.job-company-input')?.value.trim() ?? '';
    const description = card.querySelector('.job-desc-input')?.value.trim()    ?? '';
    return { title, company, description };
  });
}

/**
 * Returns true if there is at least one job with title + description.
 * Also sets validation UI feedback.
 * @returns {boolean}
 */
export function validateJobs() {
  const cards = getJobCards();

  if (cards.length === 0) {
    setValidationMsg('Adicione pelo menos uma vaga.');
    return false;
  }

  let allValid = true;

  cards.forEach((card) => {
    const titleInput = card.querySelector('.job-title-input');
    const descInput  = card.querySelector('.job-desc-input');

    const title = titleInput?.value.trim() ?? '';
    const desc  = descInput?.value.trim()  ?? '';

    let cardValid = true;

    if (!title) {
      titleInput?.classList.add('invalid-field');
      cardValid = false;
    } else {
      titleInput?.classList.remove('invalid-field');
    }

    if (!desc) {
      descInput?.classList.add('invalid-field');
      cardValid = false;
    } else {
      descInput?.classList.remove('invalid-field');
    }

    if (!cardValid) allValid = false;
  });

  if (!allValid) {
    setValidationMsg('Preencha o título e a descrição de todas as vagas.');
    return false;
  }

  setValidationMsg('');
  return true;
}

/**
 * Check quickly if the next button should be enabled
 * (at least one job with title + description, no validation messages shown).
 */
export function hasValidJob() {
  const cards = getJobCards();
  return cards.some((card) => {
    const title = card.querySelector('.job-title-input')?.value.trim() ?? '';
    const desc  = card.querySelector('.job-desc-input')?.value.trim()  ?? '';
    return title.length > 0 && desc.length > 0;
  });
}

/**
 * Register a callback to be called whenever jobs change.
 * @param {Function} cb
 */
export function onJobsChange(cb) {
  onChangeCallback = cb;
}

/**
 * Initialise module — bind elements and seed first card.
 */
export function initJobs() {
  jobsListEl      = document.getElementById('jobs-list');
  jobsCountEl     = document.getElementById('jobs-count');
  btnAddJobEl     = document.getElementById('btn-add-job');
  validationMsgEl = document.getElementById('jobs-validation-msg');

  if (!jobsListEl) return;

  btnAddJobEl?.addEventListener('click', () => addJob());

  // Seed with one empty card
  addJob();
}
