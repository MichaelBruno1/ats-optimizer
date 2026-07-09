# ATS Optimizer — System Documentation

Welcome to the official documentation for the **ATS Optimizer** project. Below is a map of the decoupled, topic-specific documentation files:

1. [System Architecture](architecture.md): Visual flows, decoupling, and high-level component diagrams.
2. [API Contracts](api_contracts.md): Request/response payloads, endpoints, limits, and SSE stream events.
3. [Data Models & Schemas](data_models.md): Resilient `SafeBaseModel` mapping logic and detailed Pydantic object structures.
4. [Multi-Agent Workflows](agents.md): Specialized agent scopes, safety boundaries, local LLM configurations, and language rules.
5. [Document Parsing & Generation](document_processing.md): Text extractors (PDF, DOCX cells/headers/footers, TXT BOM), cleaning filters, and WeasyPrint PDF layout engine.
6. [Frontend SPA Architecture](frontend.md): Single Page App wizard steps flow, EventSource connection handling, and progress UI updates.
7. [Verification & Testing](testing.md): Automated Pytest suite coverage and how to execute validations under Docker.
