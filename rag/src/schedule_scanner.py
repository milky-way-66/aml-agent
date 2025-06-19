"""
Scheduler script to periodically scan for new documents.
"""
import argparse
import logging
import sys
import time
from datetime import datetime

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
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Schedule periodic document scanning")
    parser.add_argument("--interval", type=int, default=300, help="Scan interval in seconds (default: 300)")
    
    args = parser.parse_args()
    interval = args.interval
    
    # Initialize document scanner
    scanner = DocumentScanner()
    
    logger.info(f"Starting scheduled scanning with interval of {interval} seconds")
    
    try:
        while True:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.info(f"[{current_time}] Scanning for new documents...")
            
            try:
                scanner.scan_directory()
                logger.info(f"[{current_time}] Scan completed")
            except Exception as e:
                logger.error(f"[{current_time}] Error during scan: {e}")
            
            logger.info(f"Next scan in {interval} seconds")
            time.sleep(interval)
    
    except KeyboardInterrupt:
        logger.info("Scanning scheduler stopped")


if __name__ == "__main__":
    main()
