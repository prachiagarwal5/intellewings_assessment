import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# MongoDB connection settings
MONGO_URI = os.environ.get("MONGO_URI")
if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable is not set. Please check your .env file.")
    
MONGO_DB = "sebi_enforcement"
ENTITIES_COLLECTION = "entities"
CHECKPOINTS_COLLECTION = "checkpoints"

# SEBI website settings - Updated with the correct URL format
BASE_URL = "https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=2&ssid=9&smid=6"
START_PAGE = 1
END_PAGE = 5  # Start with a reasonable range

# Scraping settings
REQUEST_DELAY = 0.2  # 200ms minimum delay between requests
DOWNLOAD_DELAY = 0.5  # 500ms delay when downloading PDFs

# Paths
PDF_STORAGE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "pdfs")
LOGS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")

# Create directories if they don't exist
os.makedirs(PDF_STORAGE_PATH, exist_ok=True)
os.makedirs(LOGS_PATH, exist_ok=True)