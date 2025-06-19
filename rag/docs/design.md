# RAG Solution Design Document

## Overview

This project implements a Retrieval-Augmented Generation (RAG) system with two main features:
1. **Resource Scanning & Embedding**: Scans a directory, processes documents, generates embeddings, and stores them in a vector database.
2. **Document Search API**: Provides an API endpoint to accept a search query and return relevant information.

---

## Architecture

### Components

#### 1. **Resource Scanner**
- **Functionality**:
  - Scans specified directories for documents (e.g., `.txt`, `.pdf`, `.md`, `.docx`).
  - Extracts text content from files using parsers like `langchain`, `PyPDF2`, and `python-docx`.
  - Splits large documents into smaller chunks for efficient embedding generation.
  - Generates embeddings for each chunk using OpenAI's language model.
  - Stores embeddings and metadata (e.g., file name, chunk index) in a vector database.
  - **Index Process**: Automatically runs at scheduled intervals to scan directories for new or updated files. Files that have already been scanned will be ignored based on metadata (e.g., file hash or timestamp).
  - **Folder Management**: Uses two folders to manage documents:
    - `pending_document`: Contains documents that are yet to be indexed.
    - `indexed_document`: Contains documents that have already been indexed. After a document is successfully indexed, it is moved from `pending_document` to `indexed_document`.

- **Workflow**:
  1. User specifies a directory to scan or the index process runs automatically.
  2. The scanner iterates through all supported file types in the `pending_document` folder.
  3. For each file:
     - Check if the file has already been scanned (using metadata like file hash or last modified timestamp).
     - If not scanned or updated, extract text content.
     - Split content into chunks (e.g., 500 tokens per chunk).
     - Generate embeddings for each chunk.
     - Store embeddings and metadata in the vector database.
     - Move the file to the `indexed_document` folder after successful indexing.

- **Error Handling**:
  - Handle unsupported file types gracefully.
  - Log errors for files that fail to process.

#### 2. **Vector Database**
- **Functionality**:
  - Stores document embeddings and metadata.
  - Supports similarity search to retrieve top-k similar embeddings for a given query.

- **Implementation**:
  - Use ChromaDB as the default vector database.
  - Ensure the database is pluggable to support other vector databases in the future.

- **Data Schema**:
  - `embedding`: Vector representation of the document chunk.
  - `metadata`: Includes file name, chunk index, and other relevant details.

#### 3. **Search API (FastAPI)**
- **Functionality**:
  - Exposes RESTful endpoints for:
    - Querying for relevant documents.
  - Accepts a search query, generates its embedding, and retrieves top-k similar documents from the vector database.

- **Endpoints**:
  1. `POST /query`: Accepts a search query and returns relevant documents.

- **Workflow**:
  1. User sends a query to the API.
  2. The API generates an embedding for the query using OpenAI's language model.
  3. The API queries the vector database for top-k similar embeddings.
  4. The API returns the corresponding documents and metadata to the user.

- **Error Handling**:
  - Validate input parameters for each endpoint.
  - Return meaningful error messages for invalid requests.

---

## Technology Stack

- **Programming Language**: Python 3.10+
- **API Framework**: FastAPI
- **Vector Database**: ChromaDB (default), pluggable for others
- **Embeddings**: OpenAI
- **Document Parsing**: `langchain`, `PyPDF2`, `python-docx`, etc.

---

## Detailed Workflow

### Resource Scanning & Embedding
1. **Input**: Directory path containing documents.
2. **Processing**:
   - Iterate through files in the directory.
   - For each file:
     - Parse text content.
     - Split content into chunks.
     - Generate embeddings for each chunk.
     - Store embeddings and metadata in the vector database.
3. **Output**: Embeddings and metadata stored in the vector database.

### Document Search API
1. **Input**: Search query from the user.
2. **Processing**:
   - Generate embedding for the query.
   - Query the vector database for top-k similar embeddings.
   - Retrieve corresponding documents and metadata.
3. **Output**: Relevant documents and metadata returned to the user.

---

## Other Considerations

- **Authentication**: Add API key or OAuth for production. No authentication for now.
- **File Types**: Support for `.txt`, `.pdf`, `.md`, `.docx`, etc.
- **Error Handling**: Robust error and exception handling.
- **Logging**: Use Python logging for monitoring.
- **Scalability**:
  - Use chunking for large documents.
  - Optimize database queries for performance.
- **Extensibility**:
  - Allow integration with other vector databases.
  - Support additional file types and parsers in the future.