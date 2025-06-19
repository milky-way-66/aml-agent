# Usage Guide for RAG Solution

This guide explains how to set up and use the RAG (Retrieval Augmented Generation) solution for document indexing and searching.

## Setup

1. **Install Dependencies**:

```bash
# Install poetry if not already installed
pip install poetry

# Install project dependencies
poetry install
```

2. **Configure Environment Variables**:

Copy the example environment file and customize it:

```bash
cp .env.example .env
```

Edit the `.env` file with your OpenAI API key and other configuration options.

## Basic Usage

### Adding Documents for Indexing

Place documents you want to index in the `data/pending_documents` directory, or use the helper script:

```bash
poetry run python src/add_document.py path/to/your/document.pdf
```

Supported file types:
- PDF (`.pdf`)
- Word Documents (`.docx`)
- Text files (`.txt`)
- Markdown files (`.md`)

### Scanning Documents

Documents in the pending directory are automatically scanned when the API server starts. 
To manually trigger a scan:

```bash
poetry run python src/main.py
```

Or you can use the API endpoint:

```bash
curl -X POST http://localhost:8000/scan
```

### Scheduling Automatic Scanning

To set up automatic scanning at regular intervals:

```bash
# Scan every 5 minutes (300 seconds)
poetry run python src/schedule_scanner.py --interval 300
```

### Searching Documents

Use the API to search for documents:

```bash
curl -X POST -H "Content-Type: application/json" -d '{"query": "your search query", "top_k": 5}' http://localhost:8000/query
```

## API Documentation

Once the server is running, visit http://localhost:8000/docs for the Swagger UI documentation.

## Project Structure

- `src/`: Main source code
  - `scanner/`: Document processing and embedding
  - `db/`: Vector database implementation
  - `api/`: FastAPI application
  - `main.py`: Application entry point
  - `add_document.py`: Helper script to add documents
  - `schedule_scanner.py`: Script to schedule automatic scanning
- `data/`: Data directories
  - `pending_documents/`: Documents waiting to be processed
  - `indexed_documents/`: Processed documents
  - `vector_db/`: Vector database storage
- `tests/`: Unit tests

## Testing

Run tests with pytest:

```bash
poetry run pytest
```
