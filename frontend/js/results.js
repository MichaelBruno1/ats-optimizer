/**
 * results.js — Results rendering for Step 5
 *
 * Renders the ATS score, resume analysis, job accordion,
 * experience coach recommendations, and on-demand PDF downloads.
 */

import api from './api.js';

/* ------------------------------------------------------------------ */
/*  Score circle SVG animation                                          */
/* ------------------------------------------------------------------ */

/**
 * Animate and render a circular SVG score indicator.
 * @param {number} score      - 0 to 100
 * @param {string} elementId  - ID of the container element
 */
export function renderScoreCircle(score, elementId = 'score-circle-wrapper') {
  const RADIUS       = 58;
  const CIRCUMFERENCE = 2 * Math.PI * RADIUS; // ≈ 364.42

  // Score number
  const numberEl = document.getElementById('ats-score-number');
  if (numberEl) numberEl.textContent = Math.round(score);

  // SVG arc
  const fgCircle = document.getElementById('score-fg-circle');
  if (!fgCircle) return;

  // Color by score
  let strokeColor;
  if (score < 50)       strokeColor = 'var(--pastel-error)';
  else if (score < 75)  strokeColor = 'var(--pastel-warning)';
  else                  strokeColor = 'var(--pastel-success)';

  fgCircle.style.stroke = strokeColor;

  // Animate from 0 to score
  const offset = CIRCUMFERENCE - (score / 100) * CIRCUMFERENCE;
  fgCircle.style.transition = 'stroke-dashoffset 1.2s cubic-bezier(0.4, 0, 0.2, 1)';

  // Force reflow so transition fires
  requestAnimationFrame(() => {
    fgCircle.style.strokeDashoffset = offset;
  });

  // Animate number counter
  animateCounter(numberEl, 0, Math.round(score), 1200);
}

function animateCounter(el, from, to, duration) {
  if (!el) return;
  const start    = performance.now();
  const range    = to - from;

  function step(now) {
    const elapsed  = now - start;
    const progress = Math.min(elapsed / duration, 1);
    // ease-out cubic
    const eased    = 1 - Math.pow(1 - progress, 3);
    el.textContent = Math.round(from + range * eased);
    if (progress < 1) requestAnimationFrame(step);
  }

  requestAnimationFrame(step);
}

/* ------------------------------------------------------------------ */
/*  Resume Analysis                                                     */
/* ------------------------------------------------------------------ */

/**
 * Render strengths, weaknesses, suggestions columns.
 * @param {Object} analysis - resume_analysis from API
 */
export function renderResumeAnalysis(analysis) {
  const container = document.getElementById('analysis-columns');
  if (!container) return;

  const {
    strengths = [],
    weaknesses = [],
    improvement_suggestions = [],
  } = analysis;

  container.innerHTML = `
    <div class="analysis-col analysis-col-strengths">
      <div class="col-header">
        <span class="material-icons col-strengths-icon">check_circle</span>
        <span class="col-title col-title-strengths">Pontos Fortes</span>
      </div>
      <ul class="col-list">
        ${strengths.length
          ? strengths.map(s => `<li class="col-item">${escapeHtml(s)}</li>`).join('')
          : '<li class="col-item" style="color:var(--pastel-text-light)">Nenhum identificado</li>'}
      </ul>
    </div>

    <div class="analysis-col analysis-col-weaknesses">
      <div class="col-header">
        <span class="material-icons col-weaknesses-icon">cancel</span>
        <span class="col-title col-title-weaknesses">Pontos Fracos</span>
      </div>
      <ul class="col-list">
        ${weaknesses.length
          ? weaknesses.map(w => `<li class="col-item">${escapeHtml(w)}</li>`).join('')
          : '<li class="col-item" style="color:var(--pastel-text-light)">Nenhum identificado</li>'}
      </ul>
    </div>

    <div class="analysis-col analysis-col-suggestions">
      <div class="col-header">
        <span class="material-icons col-suggestions-icon">lightbulb</span>
        <span class="col-title col-title-suggestions">Sugestões</span>
      </div>
      <ul class="col-list">
        ${improvement_suggestions.length
          ? improvement_suggestions.map(s => `<li class="col-item">${escapeHtml(s)}</li>`).join('')
          : '<li class="col-item" style="color:var(--pastel-text-light)">Nenhuma sugestão</li>'}
      </ul>
    </div>
  `;
}

/* ------------------------------------------------------------------ */
/*  Job Analyses Accordion                                              */
/* ------------------------------------------------------------------ */

/**
 * Render the collapsible accordion of job analyses.
 * @param {Array} jobAnalyses - job_analyses from API
 */
export function renderJobAnalyses(jobAnalyses) {
  const accordion = document.getElementById('jobs-accordion');
  if (!accordion) return;

  accordion.innerHTML = '';

  if (!jobAnalyses || jobAnalyses.length === 0) {
    accordion.innerHTML = '<li style="padding:16px;color:var(--pastel-text-light);font-size:0.9rem">Nenhuma análise de vaga disponível.</li>';
    return;
  }

  jobAnalyses.forEach((job, idx) => {
    const {
      title = `Vaga ${idx + 1}`,
      company = '',
      compatibility_score = 0,
      ats_keywords = [],
      missing_keywords = [],
      gap_analysis = '',
    } = job;

    const compatClass = compatBadgeClass(compatibility_score);
    const li = document.createElement('li');

    li.innerHTML = `
      <div class="collapsible-header" role="button" tabindex="0" aria-expanded="false">
        <span class="material-icons" style="color:var(--pastel-primary);font-size:20px">work_outline</span>
        <div style="flex:1;min-width:0">
          <p class="accordion-job-title">${escapeHtml(title)}</p>
          ${company ? `<p class="accordion-company">${escapeHtml(company)}</p>` : ''}
        </div>
        <span class="compat-badge ${compatClass}">${Math.round(compatibility_score)}%</span>
        <span class="material-icons" style="color:var(--pastel-text-light);font-size:20px;transition:transform 0.25s ease" aria-hidden="true">expand_more</span>
      </div>
      <div class="collapsible-body">
        ${renderKeywordsSection('Palavras-chave encontradas', ats_keywords, 'found')}
        ${renderKeywordsSection('Palavras-chave faltando', missing_keywords, 'missing')}
        ${gap_analysis ? `
          <div class="accordion-section">
            <div class="accordion-section-title">
              <span class="material-icons">analytics</span>
              Análise de Lacunas
            </div>
            <div class="gap-panel">
              <p>${escapeHtml(gap_analysis)}</p>
            </div>
          </div>
        ` : ''}
      </div>
    `;

    accordion.appendChild(li);
  });

  // Init Materialize collapsible
  M.Collapsible.init(accordion, {
    accordion: true,
    onOpenStart(el) {
      const header = el.querySelector('.collapsible-header');
      const icon   = header?.querySelector('.material-icons:last-child');
      if (icon) icon.style.transform = 'rotate(180deg)';
      if (header) header.setAttribute('aria-expanded', 'true');
    },
    onCloseStart(el) {
      const header = el.querySelector('.collapsible-header');
      const icon   = header?.querySelector('.material-icons:last-child');
      if (icon) icon.style.transform = 'rotate(0deg)';
      if (header) header.setAttribute('aria-expanded', 'false');
    },
  });
}

function renderKeywordsSection(label, keywords, type) {
  const iconName = type === 'found' ? 'check' : 'close';
  const badgeClass = type === 'found' ? 'badge-found' : 'badge-missing';
  return `
    <div class="accordion-section">
      <div class="accordion-section-title">
        <span class="material-icons">${type === 'found' ? 'verified' : 'highlight_off'}</span>
        ${escapeHtml(label)}
      </div>
      <div class="keywords-wrap">
        ${keywords && keywords.length
          ? keywords.map(kw => `
              <span class="badge-keyword ${badgeClass}">
                <span class="material-icons">${iconName}</span>
                ${escapeHtml(kw)}
              </span>
            `).join('')
          : `<span style="font-size:0.82rem;color:var(--pastel-text-light)">Nenhuma identificada</span>`}
      </div>
    </div>
  `;
}

function compatBadgeClass(score) {
  if (score >= 75) return 'compat-high';
  if (score >= 50) return 'compat-medium';
  return 'compat-low';
}

/* ------------------------------------------------------------------ */
/*  Experience Coach Examples (Educational section)                   */
/* ------------------------------------------------------------------ */

/**
 * Render educational before/after experience descriptions.
 * @param {Array} examples - experience_examples array from API
 */
export function renderExperienceExamples(examples) {
  const container = document.getElementById('experience-coach-container');
  if (!container) return;

  container.innerHTML = '';

  if (!examples || examples.length === 0) {
    container.innerHTML = '<p style="color:var(--pastel-text-light);font-size:0.9rem">Nenhum exemplo disponível no momento.</p>';
    return;
  }

  examples.forEach((item, index) => {
    const card = document.createElement('div');
    card.className = 'coach-card card';

    const bulletListHtml = item.suggested_bullet_points && item.suggested_bullet_points.length
      ? `<div class="coach-bullets">
           <p class="coach-subtitle"><span class="material-icons">format_list_bulleted</span> Sugestões de Realizações no Formato XYZ:</p>
           <ul>
             ${item.suggested_bullet_points.map(b => `<li>${escapeHtml(b)}</li>`).join('')}
           </ul>
         </div>`
      : '';

    card.innerHTML = `
      <div class="coach-card-header">
        <span class="material-icons coach-icon">psychology</span>
        <div>
          <h4 class="coach-role">${escapeHtml(item.role || 'Função Profissional')}</h4>
          ${item.company ? `<span class="coach-company">${escapeHtml(item.company)}</span>` : ''}
        </div>
      </div>

      <div class="coach-comparison">
        <div class="coach-box coach-box-before">
          <div class="coach-box-title">
            <span class="material-icons">history</span> Como você descreveu:
          </div>
          <p class="coach-box-text">${escapeHtml(item.original_description || 'Descrição padrão')}</p>
        </div>

        <div class="coach-box coach-box-after">
          <div class="coach-box-title">
            <span class="material-icons">auto_awesome</span> Como descrever com alto impacto:
          </div>
          <p class="coach-box-text">${escapeHtml(item.suggested_description || '')}</p>
          ${bulletListHtml}
        </div>
      </div>

      ${item.reasoning ? `
        <div class="coach-reasoning">
          <span class="material-icons">tips_and_updates</span>
          <p><strong>Por que funciona:</strong> ${escapeHtml(item.reasoning)}</p>
        </div>
      ` : ''}
    `;

    container.appendChild(card);
  });
}

/* ------------------------------------------------------------------ */
/*  Downloads (On-Demand PDF Generation)                              */
/* ------------------------------------------------------------------ */

/**
 * Handle on-demand PDF generation and download trigger.
 */
async function handlePdfDownload(btn, sessionId, jobIndex) {
  const originalHtml = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '<span class="material-icons left" style="animation: spin 1s infinite linear">sync</span> Gerando PDF...';

  try {
    // 1. Call on-demand generation endpoint
    await api.generatePdf(sessionId, jobIndex);
    // 2. Open download URL
    window.open(api.getDownloadUrl(sessionId, jobIndex), '_blank');
  } catch (err) {
    console.error('Failed to generate PDF:', err);
    M.toast({ html: `Erro ao gerar PDF: ${err.message || 'Tente novamente.'}`, classes: 'red' });
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalHtml;
  }
}

/**
 * Render download buttons/cards.
 * @param {Array}  optimizations - optimizations array from API
 * @param {string} outputMode    - 'single' | 'per_job'
 * @param {string} sessionId
 * @param {Array}  jobs          - original jobs array for titles
 */
export function renderDownloads(optimizations, outputMode, sessionId, jobs = []) {
  const container = document.getElementById('downloads-container');
  if (!container) return;

  container.innerHTML = '';

  if (!optimizations || optimizations.length === 0) {
    container.innerHTML = '<p style="color:var(--pastel-text-light);font-size:0.9rem">Nenhum currículo otimizado disponível para download.</p>';
    return;
  }

  if (outputMode === 'single') {
    const opt = optimizations[0];
    const estimatedScore = opt.estimated_score_after ?? null;
    const jobIndex = opt.job_index ?? 0;

    const div = document.createElement('div');
    div.className = 'download-single card';
    div.innerHTML = `
      <span class="material-icons download-single-icon">picture_as_pdf</span>
      <h3 class="download-single-title">Currículo Otimizado para ATS</h3>
      ${estimatedScore !== null
        ? `<p class="download-single-sub">Score ATS calculado: <strong>${Math.round(estimatedScore)}%</strong></p>`
        : '<p class="download-single-sub">Seu currículo foi otimizado para todas as vagas</p>'}
      ${opt.changes_summary && opt.changes_summary.length
        ? `<p style="font-size:0.82rem;color:var(--pastel-text-light);margin-bottom:20px;max-width:480px;margin-inline:auto">${escapeHtml(opt.changes_summary.join(' • '))}</p>`
        : ''}
      <button class="btn btn-primary waves-effect waves-light" id="btn-download-single">
        <span class="material-icons left">download</span>
        Gerar e Baixar PDF Otimizado
      </button>
    `;
    container.appendChild(div);

    const downloadBtn = div.querySelector('#btn-download-single');
    downloadBtn.addEventListener('click', () => {
      handlePdfDownload(downloadBtn, sessionId, jobIndex);
    });

  } else {
    // per_job mode — grid of cards
    const grid = document.createElement('div');
    grid.className = 'downloads-grid';

    optimizations.forEach((opt, i) => {
      const jobTitle   = opt.title   || jobs[i]?.title   || `Vaga ${i + 1}`;
      const jobCompany = opt.company || jobs[i]?.company  || '';
      const estimated  = opt.estimated_score_after ?? null;
      const jobIndex   = opt.job_index ?? i;

      const card = document.createElement('div');
      card.className = 'download-card';
      card.innerHTML = `
        <span class="material-icons download-card-icon">picture_as_pdf</span>
        <p class="download-job-title">${escapeHtml(jobTitle)}</p>
        ${jobCompany ? `<p class="download-company">${escapeHtml(jobCompany)}</p>` : ''}
        ${estimated !== null
          ? `<div class="estimated-score">
               <span class="material-icons">trending_up</span>
               ${Math.round(estimated)}% score ATS
             </div>`
          : ''}
        <button class="btn btn-primary waves-effect waves-light btn-dl-job" style="font-size:0.8rem;height:38px;line-height:38px;padding:0 18px" data-job-index="${jobIndex}">
          <span class="material-icons left" style="font-size:16px">download</span>Baixar PDF
        </button>
      `;
      grid.appendChild(card);
    });

    container.appendChild(grid);

    grid.querySelectorAll('.btn-dl-job').forEach((btn) => {
      btn.addEventListener('click', () => {
        const jobIndex = Number(btn.dataset.jobIndex);
        handlePdfDownload(btn, sessionId, jobIndex);
      });
    });
  }
}

/* ------------------------------------------------------------------ */
/*  Main render entry point                                             */
/* ------------------------------------------------------------------ */

/**
 * Render all results sections from the API response.
 * @param {Object} data      - full API response
 * @param {string} outputMode - 'single' | 'per_job'
 * @param {Array}  jobs       - original jobs submitted
 */
export function renderResults(data, outputMode, jobs = []) {
  const {
    resume_analysis = {},
    job_analyses = [],
    optimizations = [],
    experience_examples = [],
    session_id,
  } = data;

  // 1. Score circle
  const atsScore = resume_analysis.ats_readability_score ?? 0;
  renderScoreCircle(atsScore);

  // 2. Resume analysis columns
  renderResumeAnalysis(resume_analysis);

  // 3. Job accordion
  renderJobAnalyses(job_analyses);

  // 4. Educational Experience Coach suggestions
  renderExperienceExamples(experience_examples);

  // 5. Downloads (On-demand PDF)
  renderDownloads(optimizations, outputMode, session_id, jobs);
}

/* ------------------------------------------------------------------ */
/*  Utility                                                             */
/* ------------------------------------------------------------------ */

function escapeHtml(str) {
  if (typeof str !== 'string') return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;');
}
