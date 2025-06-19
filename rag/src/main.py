"""
Main entry point for the RAG application.
"""
import logging
import sys
import uvicorn

from src import config
from src.api import app
from src.scanner import DocumentScanner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point for the application."""
    # Log startup information
    logger.info("Starting RAG Application")
    logger.info(f"Pending documents directory: {config.PENDING_DOCUMENTS_DIR}")
    logger.info(f"Indexed documents directory: {config.INDEXED_DOCUMENTS_DIR}")
    logger.info(f"Vector database directory: {config.CHROMA_DB_DIR}")
    
    # Initialize document scanner and scan directory
    logger.info("Initializing document scanner and scanning directory")
    scanner = DocumentScanner()
    scanner.scan_directory()
    
    # Start the API server
    logger.info(f"Starting API server at {config.API_HOST}:{config.API_PORT}")
    uvicorn.run(
        app, 
        host=config.API_HOST, 
        port=config.API_PORT,
        log_level="info"
    )


if __name__ == "__main__":
    main()
