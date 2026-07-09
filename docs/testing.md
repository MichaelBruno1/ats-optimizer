# Verification & Testing

The project maintains a verification suite of **35 tests** covering document parsing, API routing validations, agent behaviors, and schema models.

---

## 1. Running the Tests

To run all backend tests, execute the command below from the root of the project:
```powershell
docker compose run --rm -v c:/projetos/ats_optimizer/backend/tests:/app/tests app pytest /app/tests -v
```

---

## 2. Test Structure

### 2.1 API Integration (`test_api.py`)
* Asserts health and configuration payloads.
* Tests validation rules for invalid file formats, oversized documents, missing parameters, and malformed job lists.
* Verifies `session_id` creation.

### 2.2 Parser Logic (`test_parser.py`)
* Verifies decoding plain text under UTF-8 and Latin-1 fallback encoders.
* Tests whitelisted/blacklisted file extensions.
* Asserts file size boundaries.

### 2.3 Dynamic Formats (`test_parser_formats.py`)
* Generates PDFs in-memory with PyMuPDF to test text extraction.
* Generates DOCXs with nested table cells, headers, and footers to assert parsing correctness.
* Asserts that BOM sequences and null bytes are cleaned during extraction.

### 2.4 Local LLMs & Schemas (`test_local_llm.py`)
* Asserts `SafeBaseModel` converts missing/null keys to empty defaults.
* Validates `BaseAgent` model name parsing.
* Verifies `BaseAgent` connection host-gateway overrides and local API key fallbacks.
