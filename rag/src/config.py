"""
Configuration module for the RAG application.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# OpenAI API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Document Directory Configuration
PENDING_DOCUMENTS_DIR = Path(os.getenv("PENDING_DOCUMENTS_DIR", "./data/pending_documents"))
INDEXED_DOCUMENTS_DIR = Path(os.getenv("INDEXED_DOCUMENTS_DIR", "./data/indexed_documents"))

# Vector Database Configuration
CHROMA_DB_DIR = os.getenv("CHROMA_DB_DIR", "./data/vector_db")

# Embedding Configuration
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

# Create directories if they don't exist
PENDING_DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
INDEXED_DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
Path(CHROMA_DB_DIR).mkdir(parents=True, exist_ok=True)
