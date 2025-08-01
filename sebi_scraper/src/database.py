import logging
import time
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv
load_dotenv()

from config.config import MONGO_URI, MONGO_DB, ENTITIES_COLLECTION, CHECKPOINTS_COLLECTION

logger = logging.getLogger(__name__)

class MongoDB:
    def __init__(self):
        self.client = self.connect_to_mongodb()
        self.db = self.client[MONGO_DB]
        self.entities = self.db[ENTITIES_COLLECTION]
        self.checkpoints = self.db[CHECKPOINTS_COLLECTION]
        
        # Create indexes for better query performance
        self.entities.create_index("entity_name")
        self.entities.create_index("entity_type")
        self.entities.create_index("sentiment")
        self.entities.create_index("source_pdf_url")
        self.entities.create_index("pan")  # Index for PAN numbers
        self.entities.create_index("cin")  # Index for CIN numbers
        self.entities.create_index([("entity_name", 1), ("pan", 1)])  # Compound index
        
        logger.info("Connected to MongoDB successfully")
    
    def connect_to_mongodb(self, retry_count=3, retry_delay=5):
        """Connect to MongoDB with retry logic"""
        if not MONGO_URI:
            raise ValueError("MONGO_URI is not configured. Please check your .env file.")
            
        for attempt in range(retry_count):
            try:
                client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
                # Test the connection
                client.admin.command('ping')
                return client
            except Exception as e:
                if attempt < retry_count - 1:
                    logger.warning(f"MongoDB connection attempt {attempt+1} failed: {str(e)}. Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Failed to connect to MongoDB after {retry_count} attempts: {str(e)}")
                    raise
            
    def get_last_checkpoint(self):
        """Get the last processing checkpoint"""
        checkpoint = self.checkpoints.find_one({"type": "scraping_progress"})
        if checkpoint:
            return checkpoint.get("last_page", 425), checkpoint.get("last_pdf_url")
        return 425, None
        
    def update_checkpoint(self, page, pdf_url=None):
        """Update the checkpoint with latest progress"""
        update_data = {"last_page": page}
        if pdf_url:
            update_data["last_pdf_url"] = pdf_url
            
        self.checkpoints.update_one(
            {"type": "scraping_progress"},
            {"$set": update_data},
            upsert=True
        )
        logger.debug(f"Updated checkpoint: Page {page}, PDF: {pdf_url}")
        
    def is_pdf_processed(self, pdf_url):
        """Check if a PDF has already been processed"""
        return self.checkpoints.find_one({
            "pdf_url": pdf_url, 
            "status": "completed"
        }) is not None
        
    def mark_pdf_processing(self, pdf_url):
        """Mark a PDF as being processed"""
        self.checkpoints.update_one(
            {"pdf_url": pdf_url},
            {"$set": {"status": "processing", "started_at": datetime.now()}},
            upsert=True
        )
        
    def mark_pdf_completed(self, pdf_url, entity_count):
        """Mark a PDF as successfully processed"""
        self.checkpoints.update_one(
            {"pdf_url": pdf_url},
            {
                "$set": {
                    "status": "completed", 
                    "completed_at": datetime.now(),
                    "entity_count": entity_count
                }
            },
            upsert=True
        )
        
    def mark_pdf_failed(self, pdf_url, error):
        """Mark a PDF as failed processing"""
        self.checkpoints.update_one(
            {"pdf_url": pdf_url},
            {
                "$set": {
                    "status": "failed", 
                    "error": str(error),
                    "failed_at": datetime.now()
                }
            },
            upsert=True
        )
        
    def save_entities(self, entities):
        """Save multiple entities to the database"""
        if not entities:
            return 0
            
        result = self.entities.insert_many(entities)
        return len(result.inserted_ids)
        
    def get_negative_entities(self):
        """Get all entities with negative sentiment"""
        return list(self.entities.find({"sentiment": "Negative"}))
    
    def get_entities_with_pan(self):
        """Get all entities that have PAN numbers"""
        return list(self.entities.find({"pan": {"$exists": True, "$ne": None}}))
    
    def get_entities_with_cin(self):
        """Get all entities that have CIN numbers"""
        return list(self.entities.find({"cin": {"$exists": True, "$ne": None}}))
    
    def get_entity_by_pan(self, pan_number):
        """Get entity by PAN number"""
        return self.entities.find_one({"pan": pan_number})
    
    def get_entities_summary(self):
        """Get summary statistics of entities"""
        total_entities = self.entities.count_documents({})
        entities_with_pan = self.entities.count_documents({"pan": {"$exists": True, "$ne": None}})
        entities_with_cin = self.entities.count_documents({"cin": {"$exists": True, "$ne": None}})
        entities_with_address = self.entities.count_documents({"address": {"$exists": True, "$ne": None}})
        negative_entities = self.entities.count_documents({"sentiment": "Negative"})
        
        return {
            "total_entities": total_entities,
            "entities_with_pan": entities_with_pan,
            "entities_with_cin": entities_with_cin,
            "entities_with_address": entities_with_address,
            "negative_sentiment_entities": negative_entities,
            "pan_coverage": (entities_with_pan / total_entities * 100) if total_entities > 0 else 0
        }