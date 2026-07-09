/**
 * upload.js — Drag-and-drop + file input handling for Step 1
 *
 * Emits a custom DOM event 'resumeSelected' on document when a valid
 * file is chosen, and 'resumeCleared' when removed.
 */

const ACCEPTED_EXTENSIONS = ['.pdf', '.docx', '.txt'];
const ACCEPTED_MIME = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'text/plain',
];
const MAX_SIZE_BYTES = 5 * 1024 * 1024; // 5 MB

/* ------------------------------------------------------------------ */
/*  Private helpers                                                     */
/* ------------------------------------------------------------------ */

/** Format bytes to human-readable string */
function formatBytes(bytes) {
  if (bytes < 1024)        return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

/** Derive a Material Icons name from file extension */
function iconForFile(filename) {
  const ext = filename.split('.').pop().toLowerCase();
  switch (ext) {
    case 'pdf':  return 'picture_as_pdf';
    case 'docx': return 'article';
    case 'txt':  return 'description';
    default:     return 'insert_drive_file';
  }
}

/** Validate file format and size */
function validateFile(file) {
  if (!file) return { valid: false, error: 'Nenhum arquivo selecionado.' };

  const name = file.name.toLowerCase();
  const hasValidExt = ACCEPTED_EXTENSIONS.some(ext => name.endsWith(ext));
  const hasValidMime = !file.type || ACCEPTED_MIME.includes(file.type);

  if (!hasValidExt || !hasValidMime) {
    return {
      valid: false,
      error: `Formato inválido. Use: ${ACCEPTED_EXTENSIONS.join(', ')}.`,
    };
  }

  if (file.size > MAX_SIZE_BYTES) {
    return {
      valid: false,
      error: `Arquivo muito grande (${formatBytes(file.size)}). Máximo: 5 MB.`,
    };
  }

  return { valid: true, error: '' };
}

/* ------------------------------------------------------------------ */
/*  DOM refs (resolved at init time)                                    */
/* ------------------------------------------------------------------ */
let dropZone;
let fileInput;
let btnSelectFile;
let btnRemoveFile;
let dzEmpty;
let dzFilled;
let fileNameEl;
let fileSizeEl;
let fileTypeIconEl;
let validationMsgEl;

/* ------------------------------------------------------------------ */
/*  State                                                               */
/* ------------------------------------------------------------------ */
let currentFile = null;

/* ------------------------------------------------------------------ */
/*  UI updaters                                                         */
/* ------------------------------------------------------------------ */

function showValidationError(msg) {
  if (!validationMsgEl) return;
  validationMsgEl.innerHTML = msg
    ? `<span class="material-icons" style="font-size:14px">error_outline</span> ${msg}`
    : '';
}

function showFilePreview(file) {
  dzEmpty.hidden = true;
  dzFilled.hidden = false;
  dropZone.classList.remove('drag-over');
  dropZone.classList.add('has-file');
  dropZone.style.cursor = 'default';

  fileNameEl.textContent = file.name;
  fileSizeEl.textContent = formatBytes(file.size);
  fileTypeIconEl.textContent = iconForFile(file.name);

  showValidationError('');
}

function clearPreview() {
  dzEmpty.hidden = false;
  dzFilled.hidden = true;
  dropZone.classList.remove('has-file', 'drag-over');
  dropZone.style.cursor = '';
  fileInput.value = '';

  showValidationError('');
}

/* ------------------------------------------------------------------ */
/*  File selection logic                                               */
/* ------------------------------------------------------------------ */

function handleFile(file) {
  const { valid, error } = validateFile(file);

  if (!valid) {
    showValidationError(error);
    clearPreview();
    currentFile = null;
    document.dispatchEvent(new CustomEvent('resumeCleared'));
    return;
  }

  currentFile = file;
  showFilePreview(file);
  document.dispatchEvent(new CustomEvent('resumeSelected', { detail: { file } }));
}

/* ------------------------------------------------------------------ */
/*  Public API                                                          */
/* ------------------------------------------------------------------ */

/** Programmatically clear the selected file */
export function clearFile() {
  currentFile = null;
  clearPreview();
  document.dispatchEvent(new CustomEvent('resumeCleared'));
}

/** Return the currently selected file (or null) */
export function getFile() {
  return currentFile;
}

/* ------------------------------------------------------------------ */
/*  Initialisation                                                      */
/* ------------------------------------------------------------------ */

export function initUpload() {
  dropZone      = document.getElementById('drop-zone');
  fileInput     = document.getElementById('file-input');
  btnSelectFile = document.getElementById('btn-select-file');
  btnRemoveFile = document.getElementById('btn-remove-file');
  dzEmpty       = document.getElementById('dz-empty');
  dzFilled      = document.getElementById('dz-filled');
  fileNameEl    = document.getElementById('file-name');
  fileSizeEl    = document.getElementById('file-size');
  fileTypeIconEl= document.getElementById('file-type-icon');
  validationMsgEl = document.getElementById('upload-validation-msg');

  if (!dropZone) return; // guard

  /* -- Click handlers -- */

  btnSelectFile.addEventListener('click', (e) => {
    e.stopPropagation();
    fileInput.click();
  });

  dropZone.addEventListener('click', (e) => {
    // Don't open picker when file is already loaded
    if (dropZone.classList.contains('has-file')) return;
    fileInput.click();
  });

  // Keyboard accessibility
  dropZone.addEventListener('keydown', (e) => {
    if ((e.key === 'Enter' || e.key === ' ') && !dropZone.classList.contains('has-file')) {
      e.preventDefault();
      fileInput.click();
    }
  });

  btnRemoveFile.addEventListener('click', (e) => {
    e.stopPropagation();
    clearFile();
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files && fileInput.files[0]) {
      handleFile(fileInput.files[0]);
    }
  });

  /* -- Drag & Drop handlers -- */

  dropZone.addEventListener('dragenter', (e) => {
    e.preventDefault();
    if (!dropZone.classList.contains('has-file')) {
      dropZone.classList.add('drag-over');
    }
  });

  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
    if (!dropZone.classList.contains('has-file')) {
      dropZone.classList.add('drag-over');
    }
  });

  dropZone.addEventListener('dragleave', (e) => {
    // Only remove class when leaving the drop-zone itself, not a child
    if (!dropZone.contains(e.relatedTarget)) {
      dropZone.classList.remove('drag-over');
    }
  });

  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    if (dropZone.classList.contains('has-file')) return; // ignore drop when file loaded
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  });

  // Prevent browser default for drag events on whole window
  window.addEventListener('dragover',  (e) => e.preventDefault(), false);
  window.addEventListener('drop',      (e) => e.preventDefault(), false);
}
