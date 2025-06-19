## AML-agent Multi-Repository

This repository is a monorepo containing two main projects:

### 1. analyzer-agent
Located in `agent/`, this is the core agent framework for AML (Automated Machine Learning) workflows. It includes:
- Agent orchestration and workflow logic
- Tools for integration (MCP client, RAG client)
- CLI and UI components
- Utilities and configuration
- Data storage for indexed and pending documents
- Comprehensive tests

### 2. rag
Located in `rag/`, this project provides Retrieval-Augmented Generation (RAG) capabilities, including:
- Document indexing and vector database management
- API for document retrieval and management
- Document scanner and scheduler
- Example data and documentation
- Tests and usage examples

## Structure

- `agent/` - Analyzer agent core, tools, UI, and utilities
- `rag/` - RAG service, API, and document management
- Each subproject contains its own dependencies, configuration, and tests

## Getting Started

See the `README.md` in each subproject (`agent/README.md` and `rag/README.md`) for setup and usage instructions specific to each component.

## Purpose

This monorepo is designed to support advanced AML workflows by combining agent-based automation with RAG-powered document retrieval and analysis.
