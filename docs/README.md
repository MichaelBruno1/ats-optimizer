# ATS Optimizer — System Documentation

Welcome to the official documentation for the **ATS Optimizer** project. Below is a map of the decoupled, topic-specific documentation files:

1. [Arquitetura do Sistema](architecture.md): Fluxos visuais, desacoplamento e diagramas de componentes.
2. [Contratos da API](api_contracts.md): Payloads de requisição/resposta, endpoints, limites e eventos SSE.
3. [Modelos de Dados & Schemas](data_models.md): Lógica de resiliência do `SafeBaseModel` e estruturas Pydantic detalhadas.
4. [Agentes Multi-LLM](agents.md): Escopos dos agentes, limites de segurança, configurações de LLM local e regras de idioma.
5. [Processamento de Documentos](document_processing.md): Extratores de texto (PDF, DOCX, TXT BOM), filtros de limpeza e motor de layout WeasyPrint.
6. [Arquitetura do Frontend SPA](frontend.md): Fluxo do wizard, tratamento de conexão EventSource e atualizações de progresso.
7. [Verificação & Testes](testing.md): Cobertura automatizada do Pytest e execução de validações via Docker.
8. [Débitos Técnicos](debitos_tecnicos.md): Levantamento completo de débitos técnicos classificados por severidade para correção futura.
