"""
Utility script to manually add documents to the pending folder for processing.
"""
import argparse
import logging
import os
import shutil
import sys
from pathlib import Path

from src import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def add_document(file_path: str):
    """Add a document to the pending folder for processing."""
    file_path = Path(file_path).resolve()
    
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return False
    
    if not file_path.is_file():
        logger.error(f"Not a file: {file_path}")
        return False
    
    # Check if file extension is supported
    ext = file_path.suffix.lower()
    supported_extensions = [".txt", ".pdf", ".docx", ".md"]
    
    if ext not in supported_extensions:
        logger.error(f"Unsupported file type: {ext}. Supported types: {', '.join(supported_extensions)}")
        return False
    
    # Copy file to pending folder
    dest_path = config.PENDING_DOCUMENTS_DIR / file_path.name
    shutil.copy2(file_path, dest_path)
    logger.info(f"Added {file_path.name} to pending folder for processing")
    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Add documents to the RAG system for processing")
    parser.add_argument("file_paths", nargs="+", help="Paths to document files to add")
    
    args = parser.parse_args()
    
    success_count = 0
    for file_path in args.file_paths:
        if add_document(file_path):
            success_count += 1
    
    logger.info(f"Added {success_count} out of {len(args.file_paths)} documents to pending folder")


if __name__ == "__main__":
    main()
