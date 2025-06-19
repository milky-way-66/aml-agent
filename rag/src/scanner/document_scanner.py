"""
Document scanner module for processing and embedding documents.
"""
import hashlib
import logging
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple

from langchain.document_loaders import (
    TextLoader,
    PyPDFLoader,
    Docx2txtLoader,
    UnstructuredMarkdownLoader,
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
import openai
import tiktoken

from src import config
from src.db import get_vector_db

logger = logging.getLogger(__name__)

# Set OpenAI API key
openai.api_key = config.OPENAI_API_KEY

# Initialize tokenizer for token counting
# This is the encoding used by text-embedding-ada-002
TOKENIZER = tiktoken.get_encoding("cl100k_base")


class DocumentScanner:
    """Document scanner for processing and embedding documents."""

    SUPPORTED_EXTENSIONS = {
        ".txt": TextLoader,
        ".pdf": PyPDFLoader,
        ".docx": Docx2txtLoader,
        ".md": UnstructuredMarkdownLoader,
    }

    def __init__(self,
                 pending_dir: Optional[Union[str, Path]] = None,
                 indexed_dir: Optional[Union[str, Path]] = None,
                 db_type: str = "chroma"):
        """Initialize document scanner."""
        self.pending_dir = Path(pending_dir or config.PENDING_DOCUMENTS_DIR)
        self.indexed_dir = Path(indexed_dir or config.INDEXED_DOCUMENTS_DIR)
        self.vector_db = get_vector_db(db_type)

        # Create directories if they don't exist
        self.pending_dir.mkdir(parents=True, exist_ok=True)
        self.indexed_dir.mkdir(parents=True, exist_ok=True)

        # Initialize text splitter for chunking
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
            length_function=self._count_tokens,
        )

    @staticmethod
    def _count_tokens(text: str) -> int:
        """Count the number of tokens in a text."""
        return len(TOKENIZER.encode(text))

    @staticmethod
    def _get_file_hash(file_path: Path) -> str:
        """Get the hash of a file for deduplication."""
        hasher = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _get_loader(self, file_path: Path):
        """Get the appropriate document loader for a file."""
        ext = file_path.suffix.lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {ext}")

        loader_cls = self.SUPPORTED_EXTENSIONS[ext]
        return loader_cls(str(file_path))

    def _process_document(self, file_path: Path) -> Tuple[List[str], List[Dict[str, Any]]]:
        """Process a document and return its chunks and metadata."""
        logger.info(f"Processing document: {file_path}")

        # Load document
        loader = self._get_loader(file_path)
        documents = loader.load()

        # Split document into chunks
        chunks = self.text_splitter.split_documents(documents)

        # Extract text and create metadata
        texts = []
        metadatas = []

        file_hash = self._get_file_hash(file_path)

        for i, chunk in enumerate(chunks):
            texts.append(chunk.page_content)
            metadatas.append({
                "source": file_path.name,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "file_hash": file_hash
            })

        return texts, metadatas

    def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        try:
            response = openai.Embedding.create(
                input=texts,
                model=config.EMBEDDING_MODEL
            )
            return [data["embedding"] for data in response["data"]]
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise

    def scan_directory(self) -> None:
        """Scan pending directory for new documents to process."""
        logger.info(f"Scanning directory: {self.pending_dir}")

        for file_path in self.pending_dir.glob("**/*"):
            # Skip directories and non-supported files
            if not file_path.is_file() or file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
                continue

            try:
                # Process document
                texts, metadatas = self._process_document(file_path)

                # Skip empty documents
                if not texts:
                    logger.warning(
                        f"No content extracted from {file_path}. Skipping.")
                    continue

                # Generate embeddings
                embeddings = self._generate_embeddings(texts)

                # Generate unique IDs for each chunk
                ids = [f"{file_path.stem}-{meta['file_hash'][:8]}-{i}" for i,
                       meta in enumerate(metadatas)]

                # Add to vector database
                self.vector_db.add_documents(
                    embeddings=embeddings,
                    metadatas=metadatas,
                    documents=texts,
                    ids=ids
                )

                # Move file to indexed directory
                indexed_path = self.indexed_dir / file_path.name
                shutil.move(str(file_path), str(indexed_path))
                logger.info(f"Moved {file_path} to {indexed_path}")

            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")

    def query_documents(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """Query for relevant documents."""
        # Generate query embedding
        query_embedding = self._generate_embeddings([query])[0]

        # Query vector database
        results = self.vector_db.query(query_embedding, top_k=top_k)

        return results
