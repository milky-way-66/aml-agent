# RAG Solution

This project implements a Retrieval-Augmented Generation (RAG) system with two main features:
1. Resource Scanning & Embedding: Scans a directory, processes documents, generates embeddings, and stores them in a vector database.
2. Document Search API: Provides an API endpoint to accept a search query and return relevant information.

## Setup

```bash
# Install dependencies
poetry install

# Configure environment variables
cp .env.example .env
# Edit .env with your OpenAI API key

# Run the API
poetry run rag-solution
```

## Features

- Scan and process multiple document types (PDF, DOCX, TXT, MD)
- Automatic chunking of documents for embedding generation
- Vector database storage with ChromaDB
- Search API for retrieving relevant documents
- Automatic document indexing with folder management

## API Endpoints

- `POST /query`: Search for documents matching a query
