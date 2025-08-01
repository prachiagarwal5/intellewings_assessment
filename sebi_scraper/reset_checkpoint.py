import os
import sys
import logging
from pymongo import MongoClient
from config.config import MONGO_URI, MONGO_DB, CHECKPOINTS_COLLECTION

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def reset_checkpoint(start_page=1):
    try:
        client = MongoClient(MONGO_URI)
        db = client[MONGO_DB]
        checkpoints = db[CHECKPOINTS_COLLECTION]
        
        result = checkpoints.update_one(
            {"type": "scraping_progress"},
            {"$set": {"last_page": start_page, "last_pdf_url": None}},
            upsert=True
        )
        
        logger.info(f"Reset checkpoint to page {start_page}")
        logger.info(f"Modified: {result.modified_count}, Upserted: {bool(result.upserted_id)}")
        
    except Exception as e:
        logger.error(f"Failed to reset checkpoint: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            start_page = int(sys.argv[1])
        except ValueError:
            logger.error("Invalid page number. Please provide a valid integer.")
            sys.exit(1)
    else:
        start_page = 1
        
    reset_checkpoint(start_page)