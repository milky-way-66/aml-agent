"""
Vector database module for storing and retrieving document embeddings.
"""
from abc import ABC, abstractmethod
import logging
from typing import Dict, List, Any, Optional

import chromadb
from chromadb.config import Settings

from src import config

logger = logging.getLogger(__name__)


class VectorDatabase(ABC):
    """Abstract base class for vector database implementations."""
    
    @abstractmethod
    def add_documents(self, embeddings: List[List[float]], metadatas: List[Dict[str, Any]], 
                     documents: List[str], ids: List[str]) -> None:
        """Add document embeddings to the database."""
        pass
    
    @abstractmethod
    def query(self, query_embedding: List[float], top_k: int = 5) -> Dict[str, Any]:
        """Query for similar document embeddings."""
        pass


class ChromaDatabase(VectorDatabase):
    """ChromaDB vector database implementation."""
    
    def __init__(self, collection_name: str = "documents", persist_directory: Optional[str] = None):
        """Initialize ChromaDB database."""
        persist_dir = persist_directory or config.CHROMA_DB_DIR
        
        self.client = chromadb.PersistentClient(path=persist_dir, settings=Settings(anonymized_telemetry=False))
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(name=collection_name)
            logger.info(f"Loaded existing collection: {collection_name}")
        except ValueError:
            self.collection = self.client.create_collection(name=collection_name)
            logger.info(f"Created new collection: {collection_name}")
    
    def add_documents(self, embeddings: List[List[float]], metadatas: List[Dict[str, Any]], 
                     documents: List[str], ids: List[str]) -> None:
        """Add document embeddings to the database."""
        self.collection.add(
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents,
            ids=ids
        )
        logger.info(f"Added {len(embeddings)} document chunks to the database")
    
    def query(self, query_embedding: List[float], top_k: int = 5) -> Dict[str, Any]:
        """Query for similar document embeddings."""
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=top_k
        )
        
        return results


def get_vector_db(db_type: str = "chroma") -> VectorDatabase:
    """Factory function to get the appropriate vector database implementation."""
    if db_type.lower() == "chroma":
        return ChromaDatabase()
    else:
        raise ValueError(f"Unsupported vector database type: {db_type}")
