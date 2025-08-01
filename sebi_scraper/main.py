import os
import spacy
from tqdm import tqdm

from src.utils import setup_logging
from src.database import MongoDB
from src.scraper import SEBIScraper
from src.extractor import PDFExtractor
from src.sentiment import SentimentAnalyzer
from config.config import START_PAGE, END_PAGE, BASE_URL

def main():
    # Set up logging
    logger = setup_logging()
    logger.info("Starting SEBI enforcement orders scraper")
    
    try:
        # Connect to MongoDB
        db = MongoDB()
        
        # Initialize components
        scraper = SEBIScraper(db)
        extractor = PDFExtractor()
        
        # Load NLP model for NER
        logger.info("Loading spaCy NLP model...")
        nlp = spacy.load("en_core_web_sm")
        
        # Initialize sentiment analyzer
        sentiment_analyzer = SentimentAnalyzer()
        
        # Get last checkpoint or reset if requested
        if os.environ.get("RESET_CHECKPOINT", "false").lower() == "true":
            logger.info("Resetting checkpoint to start from page 1")
            last_page = START_PAGE
            last_pdf = None
        else:
            last_page, last_pdf = db.get_last_checkpoint()
        
        start_page = max(last_page, START_PAGE)
        logger.info(f"Resuming from page {start_page}, last PDF: {last_pdf}")
        
        # Validate base URL
        try:
            logger.info(f"Validating base URL: {BASE_URL}")
            test_url = f"{BASE_URL}?pagenum=1"
            response = scraper.session.get(test_url, timeout=10)
            response.raise_for_status()
            logger.info("Base URL validation successful")
        except Exception as e:
            logger.error(f"Base URL validation failed: {str(e)}")
            logger.error("Please check the URL format in config.py")
            return
        
        # Scrape PDF links
        pdf_links = scraper.scrape_pdf_links(start_page, END_PAGE, last_pdf)
        logger.info(f"Found {len(pdf_links)} PDF links to process")
        
        if not pdf_links:
            logger.warning("No PDF links found. Check URL format or page range.")
            return
        
        # Process each PDF
        for pdf_info in tqdm(pdf_links, desc="Processing PDFs"):
            pdf_url = pdf_info['url']
            
            # Skip if already processed
            if db.is_pdf_processed(pdf_url):
                logger.info(f"Skipping already processed PDF: {pdf_url}")
                continue
            
            try:
                # Mark as processing
                db.mark_pdf_processing(pdf_url)
                
                # Download and extract text
                pdf_content = extractor.download_pdf(pdf_url)
                text = extractor.extract_text_from_pdf(pdf_content)
                
                if not text:
                    logger.warning(f"No text extracted from {pdf_url}")
                    db.mark_pdf_failed(pdf_url, "No text extracted")
                    continue
                
                # Extract entities
                raw_entities = extractor.extract_entities_from_text(text, nlp)
                
                if not raw_entities:
                    logger.warning(f"No entities found in {pdf_url}")
                    db.mark_pdf_completed(pdf_url, 0)
                    continue
                
                # Extract PAN, CIN, addresses
                pan_numbers = extractor.extract_pan_numbers(text)
                cin_numbers = extractor.extract_cin_numbers(text)
                addresses = extractor.extract_addresses(text)
                
                # Get entity-PAN pairs using proximity analysis
                entity_pan_pairs = extractor.extract_entity_pan_pairs(text, raw_entities)
                
                # Process entities and analyze sentiment
                processed_entities = []
                
                logger.info(f"Found {len(pan_numbers)} PAN numbers: {pan_numbers}")
                logger.info(f"Found {len(cin_numbers)} CIN numbers: {cin_numbers}")
                logger.info(f"Found {len(addresses)} addresses")
                logger.info(f"Found {len(entity_pan_pairs)} entity-PAN pairs")
                
                for entity in raw_entities:
                    # Get context around this entity (larger window for better matching)
                    context = extractor.get_entity_context(text, entity, window_size=500)
                    
                    # Analyze sentiment
                    sentiment = sentiment_analyzer.analyze_entity_sentiment(context)
                    
                    # Find PAN for this entity from the entity-PAN pairs
                    entity_pan = None
                    entity_cin = None
                    entity_address = None
                    
                    # First, check if we have a direct entity-PAN pair
                    for pair in entity_pan_pairs:
                        if pair['entity'] == entity['text']:
                            entity_pan = pair['pan']
                            logger.info(f"Using paired PAN {entity_pan} for entity {entity['text']}")
                            break
                    
                    # If no direct pair, try the original proximity method
                    if not entity_pan:
                        for pan in pan_numbers:
                            # Check if PAN appears in the context around this entity
                            if pan in context:
                                entity_pan = pan
                                logger.info(f"Matched PAN {pan} to entity {entity['text']} via context")
                                break
                            # Also check if entity name appears near PAN in the full text
                            elif entity["text"] in text:
                                entity_start = text.find(entity["text"])
                                pan_start = text.find(pan)
                                if abs(entity_start - pan_start) < 1000:  # Within 1000 characters
                                    entity_pan = pan
                                    logger.info(f"Matched PAN {pan} to entity {entity['text']} (proximity match)")
                                    break
                    
                    # Look for CIN near this entity (primarily for companies)
                    for cin in cin_numbers:
                        if cin in context:
                            entity_cin = cin
                            logger.info(f"Matched CIN {cin} to entity {entity['text']}")
                            break
                        # Also check proximity in full text
                        elif entity["text"] in text:
                            entity_start = text.find(entity["text"])
                            cin_start = text.find(cin)
                            if abs(entity_start - cin_start) < 1000:  # Within 1000 characters
                                entity_cin = cin
                                logger.info(f"Matched CIN {cin} to entity {entity['text']} (proximity match)")
                                break
                    
                    # Look for addresses near this entity
                    for addr in addresses:
                        if any(word in addr.lower() for word in entity["text"].lower().split()):
                            entity_address = addr
                            logger.info(f"Matched address to entity {entity['text']}")
                            break
                        # Check if address appears in context
                        elif addr[:50] in context:  # Check first 50 chars of address
                            entity_address = addr
                            break
                    
                    # Create the entity record
                    entity_record = {
                        "entity_name": entity["text"],
                        "entity_type": entity["type"],
                        "sentiment": sentiment,
                        "source_pdf_url": pdf_url,
                        "pdf_title": pdf_info.get('title', 'Unknown'),
                        "pdf_date": pdf_info.get('date', 'Unknown')
                    }
                    
                    if entity_pan:
                        entity_record["pan"] = entity_pan
                    if entity_cin:
                        entity_record["cin"] = entity_cin
                    if entity_address:
                        entity_record["address"] = entity_address
                    
                    processed_entities.append(entity_record)
                
                # Save to database
                if processed_entities:
                    count = db.save_entities(processed_entities)
                    logger.info(f"Saved {count} entities from {pdf_url}")
                
                # Mark as completed
                db.mark_pdf_completed(pdf_url, len(processed_entities))
                
            except Exception as e:
                logger.error(f"Error processing {pdf_url}: {str(e)}")
                db.mark_pdf_failed(pdf_url, str(e))
        
        logger.info("SEBI enforcement orders processing completed")
        
        # Get comprehensive summary
        summary = db.get_entities_summary()
        logger.info("="*60)
        logger.info("EXTRACTION SUMMARY")
        logger.info("="*60)
        logger.info(f"Total entities extracted: {summary['total_entities']}")
        logger.info(f"Entities with PAN numbers: {summary['entities_with_pan']} ({summary['pan_coverage']:.1f}%)")
        logger.info(f"Entities with CIN numbers: {summary['entities_with_cin']}")
        logger.info(f"Entities with addresses: {summary['entities_with_address']}")
        logger.info(f"Entities with negative sentiment: {summary['negative_sentiment_entities']}")
        logger.info("="*60)
        
        # Show some sample entities with PAN numbers
        entities_with_pan = db.get_entities_with_pan()
        if entities_with_pan:
            logger.info("SAMPLE ENTITIES WITH PAN NUMBERS:")
            for i, entity in enumerate(entities_with_pan[:5]):  # Show first 5
                logger.info(f"{i+1}. {entity['entity_name']} ({entity['entity_type']}) - PAN: {entity['pan']}")
                if entity.get('cin'):
                    logger.info(f"   CIN: {entity['cin']}")
                if entity.get('address'):
                    logger.info(f"   Address: {entity['address'][:100]}...")
            logger.info("="*60)
        
    except Exception as e:
        logger.error(f"Fatal error in main process: {str(e)}")

if __name__ == "__main__":
    print("Starting SEBI Scraper...")
    main()