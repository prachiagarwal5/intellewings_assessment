import logging
import os
import time
from functools import wraps
from datetime import datetime

from config.config import LOGS_PATH

def setup_logging():
    """Configure logging for the application"""
    log_file = os.path.join(LOGS_PATH, f"sebi_scraper_{datetime.now().strftime('%Y%m%d')}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)

def retry_on_exception(max_retries=3, delay=1):
    """Decorator to retry a function on exception"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Retry {retries}/{max_retries} for {func.__name__}: {str(e)}")
                    if retries == max_retries:
                        raise
                    time.sleep(delay * retries)  # Exponential backoff
        return wrapper
    return decorator

def is_valid_pdf_url(url):
    """Check if URL is a valid PDF link or likely leads to a PDF"""
    if not url:
        return False
    
    url_lower = url.lower()
    # Check for direct PDF extensions or patterns indicating a PDF
    return (url_lower.endswith('.pdf') or 
            'viewpdf' in url_lower or 
            'download' in url_lower and ('pdf' in url_lower or 'order' in url_lower))