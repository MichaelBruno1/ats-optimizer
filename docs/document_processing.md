# Document Parsing & Generation

Parsing resume text and generating standard layouts is handled by dedicated Python services.

---

## 1. Document Parser (`document_parser.py`)

Handles bytes content uploaded via the REST API depending on the extension:
* **Plain Text (TXT)**: Decodes text using `utf-8-sig` to automatically strip Byte Order Marks (BOM) if present. If it fails, falls back to `latin-1`.
* **Portable Document Format (PDF)**: Uses `PyMuPDF` (`fitz`) to extract text line-by-line.
* **Word (DOCX)**: Uses `python-docx` to load the document. To support complex layouts, it iterates recursively over paragraphs, section headers, section footers, table borders, cells, and nested grids.
* **Filter Cleaning**: Automatically strips out null bytes (`\x00`) from all extracted text across all formats.

---

## 2. PDF Generator (`pdf_generator.py`)

Converts the optimized resume JSON structure into a standard PDF.
* **Engine**: WeasyPrint with Jinja2 templates.
* **Dynamic Language Translation**: Checks the optimized resume content for common vocabulary (heuristics) and loads a translations map (`pt`, `es`, `en`) to output headers (e.g., *Resumo Profissional*, *Habilidades*) matching the candidate's document language.
* **No Score Leak**: Suppresses internal ATS metrics from the printed resume PDF (retains scores for frontend display only).

---

## 3. PDF Generator Layout Styling

The Jinja2 template is located at `backend/app/templates/resume_template.html`.
* **A4 Standard**: Renders using default A4 rules with 2cm margins.
* **No Multicolumns**: Arranges sections sequentially. Multicolumn layouts are avoided because ATS scanners struggle to parse columns left-to-right correctly.
* **Typography**: Clean Arial/Helvetica sans-serif fonts with distinct sizes.
* **Color System**: Primary text in dark gray (`#2C2C2C`), headers in muted slate (`#4A4A4A`), and section dividers in light gray (`#E0E0E0`).
