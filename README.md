# Intellewings Assessment

This project consists of two main components for regulatory data extraction and analysis:

1. **SEBI Scraper** - Extracts and analyzes SEBI enforcement orders with NLP processing
2. **IOSCO Part 2** - Scrapes IOSCO I-SCAN organizational profiles

## Project Structure

```
intellewings_assessment/
├── main.py                     # Main entry point
├── requirements.txt            # Python dependencies
├── pyproject.toml             # Project configuration
├── uv.lock                    # UV lock file
├── README.md                  # This file
├── sebi_scraper/              # SEBI enforcement orders scraper
│   ├── main.py
│   ├── README.md
│   ├── reset_checkpoint.py
│   ├── config/
│   │   └── config.py          # Configuration settings
│   ├── src/
│   │   ├── database.py        # MongoDB operations
│   │   ├── scraper.py         # Web scraping logic
│   │   ├── extractor.py       # PDF processing and entity extraction
│   │   ├── sentiment.py       # Sentiment analysis
│   │   └── utils.py           # Utility functions
│   ├── data/pdfs/             # Downloaded PDF storage
│   └── logs/                  # Application logs
└── IOSCO_part2/               # IOSCO I-SCAN profile scraper
    ├── main.py
    ├── query_data.py
    ├── reset_checkpoint.py
    ├── extracted_profiles.json
    └── src/
        ├── db.py              # Database operations
        └── scrapper.py        # Selenium-based scraping
```

## Features

### SEBI Scraper
- **Web Scraping**: Extracts SEBI enforcement orders from official website
- **PDF Processing**: Downloads and processes PDF documents
- **Entity Recognition**: Uses spaCy NLP for named entity recognition
- **Data Extraction**: Extracts PAN numbers, CIN numbers, and addresses
- **Sentiment Analysis**: Analyzes sentiment using DistilBERT model
- **MongoDB Storage**: Stores extracted data with indexing
- **Checkpoint System**: Resumes processing from last checkpoint
- **Logging**: Comprehensive logging system

### IOSCO Part 2
- **Profile Scraping**: Extracts organization profiles from IOSCO I-SCAN
- **Selenium Automation**: Uses Chrome WebDriver for dynamic content
- **Data Storage**: MongoDB storage with checkpoint system
- **Detail Extraction**: Extracts comprehensive profile information

## Setup Instructions

### Prerequisites
- **Python**: 3.13+ (required for this project)
- **UV Package Manager**: Latest version
- **MongoDB**: Running instance (local or cloud)
- **Chrome Browser**: Latest version (for IOSCO scraper)
- **Internet Connection**: Required for downloading models and scraping

### Step-by-Step Setup

#### 1. Install UV Package Manager
```bash
# Install UV if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh
# or
pip install uv
```

#### 2. Clone and Setup Project
```bash
git clone <repository-url>
cd intellewings_assessment
```

#### 3. Create Virtual Environment with UV
```bash
# Create virtual environment
uv venv

# Activate virtual environment
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Windows Command Prompt:
.venv\Scripts\activate.bat
# macOS/Linux:
source .venv/bin/activate
```

#### 4. Install Dependencies
```bash
# Install all project dependencies
uv pip install -r requirements.txt

# Install spaCy English model (required for NLP)
python -m spacy download en_core_web_sm
```

#### 5. MongoDB Setup
**Option A: Local MongoDB**
```bash
# Install MongoDB Community Edition
# Windows: Download from https://www.mongodb.com/try/download/community
# macOS: brew install mongodb-community
# Ubuntu: sudo apt install mongodb

# Start MongoDB service
# Windows: Start as Windows service
# macOS/Linux: sudo systemctl start mongod
```

**Option B: MongoDB Atlas (Cloud)**
1. Create account at https://cloud.mongodb.com/
2. Create a free cluster
3. Get connection string from "Connect" → "Connect your application"

#### 6. Environment Configuration
Create `.env` file in the project root:
```env
# MongoDB Configuration (choose one)
# Local MongoDB:
MONGO_URI=mongodb://localhost:27017/

# MongoDB Atlas (replace with your connection string):
# MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/

# Optional Settings
RESET_CHECKPOINT=false
```

#### 7. Verify Installation
```bash
# Test SEBI scraper setup
cd sebi_scraper
python -c "from src.database import MongoDB; print('MongoDB connection:', MongoDB().client.admin.command('ping'))"

# Test IOSCO scraper setup
cd ../IOSCO_part2
python -c "from src.db import profiles_collection; print('Database connection successful')"
```

### Running the Applications

#### SEBI Scraper
```bash
cd sebi_scraper

# Run with default settings (pages 1-5)
python main.py

# Reset checkpoint to start from beginning
python reset_checkpoint.py

# Reset to specific page
python reset_checkpoint.py 10
```

#### IOSCO Scraper
```bash
cd IOSCO_part2

# Run profile scraper
python main.py

# Query extracted data
python query_data.py

# Reset checkpoint
python reset_checkpoint.py
```

## Checkpointing Mechanism Details

### Overview
Both scrapers implement robust checkpointing systems to ensure reliable, resumable data extraction processes. This prevents data loss and allows efficient continuation after interruptions.

### SEBI Scraper Checkpointing

#### Multi-Level Checkpointing
1. **Page-Level Checkpointing**
   - Tracks the last successfully processed page number
   - Stored in `checkpoints` collection with `type: "scraping_progress"`
   - Updated after each page is fully processed

2. **PDF-Level Checkpointing**  
   - Tracks individual PDF processing status
   - Three states: `processing`, `completed`, `failed`
   - Prevents reprocessing of already completed PDFs

#### Implementation Details
```python
# Checkpoint Creation/Update
def update_checkpoint(self, page, pdf_url=None):
    update_data = {"last_page": page}
    if pdf_url:
        update_data["last_pdf_url"] = pdf_url
        
    self.checkpoints.update_one(
        {"type": "scraping_progress"},
        {"$set": update_data},
        upsert=True
    )
```

#### Resume Logic
```python
# Resume from last checkpoint
if os.environ.get("RESET_CHECKPOINT", "false").lower() == "true":
    last_page = START_PAGE
    last_pdf = None
else:
    last_page, last_pdf = db.get_last_checkpoint()

start_page = max(last_page, START_PAGE)
```

#### PDF Processing States
- **`processing`**: PDF download/extraction in progress
- **`completed`**: Successfully extracted entities, stored count
- **`failed`**: Processing failed, error message stored
- **Resume behavior**: Skips `completed` PDFs, retries `failed` ones

### IOSCO Scraper Checkpointing

#### Index-Based Checkpointing
- Tracks the last processed table row index
- Enables precise resumption from exact position
- Handles dynamic content loading efficiently

#### Implementation
```python
def load_checkpoint():
    checkpoint = checkpoint_collection.find_one({"type": "profile"})
    return checkpoint["last_index"] if checkpoint else 0

def save_checkpoint(index):
    checkpoint_collection.update_one(
        {"type": "profile"},
        {"$set": {"last_index": index, "updated_at": datetime.now()}},
        upsert=True
    )
```

### Checkpoint Management Commands

#### Reset Checkpoints
```bash
# SEBI Scraper - Reset to beginning
cd sebi_scraper
python reset_checkpoint.py

# SEBI Scraper - Reset to specific page
python reset_checkpoint.py 50

# IOSCO Scraper - Reset to beginning  
cd IOSCO_part2
python reset_checkpoint.py
```

#### Manual Checkpoint Verification
```python
# Check SEBI checkpoint status
from sebi_scraper.src.database import MongoDB
db = MongoDB()
last_page, last_pdf = db.get_last_checkpoint()
print(f"Resume from page: {last_page}, Last PDF: {last_pdf}")

# Check PDF processing status
completed_count = db.checkpoints.count_documents({"status": "completed"})
failed_count = db.checkpoints.count_documents({"status": "failed"})
print(f"Completed: {completed_count}, Failed: {failed_count}")
```

### Checkpoint Data Integrity
- **Atomic Updates**: Each checkpoint update is atomic
- **Timestamp Tracking**: All checkpoints include update timestamps  
- **Error Handling**: Failed operations don't corrupt checkpoint state
- **Validation**: Checkpoint data validated before resume operations

### Recovery Scenarios
1. **Network Interruption**: Resume from last completed page/PDF
2. **Application Crash**: Resume from last saved checkpoint
3. **MongoDB Disconnection**: Retry logic with checkpoint preservation
4. **Partial PDF Processing**: Individual PDF status prevents data duplication

## MongoDB Schema Description

### Database Structure
- **Database Name**: `sebi_enforcement` (SEBI) / `iosco_profiles` (IOSCO)
- **Connection**: Configurable via `MONGO_URI` environment variable
- **Indexing**: Automatic index creation for optimal query performance

### SEBI Scraper Collections

#### 1. `entities` Collection
Stores extracted entities from SEBI enforcement orders with comprehensive metadata.

```javascript
{
  "_id": ObjectId("..."),
  "entity_name": "ABC Private Limited",           // String - Extracted entity name
  "entity_type": "ORG",                          // String - PERSON/ORG (from spaCy NER)
  "sentiment": "Negative",                       // String - Positive/Negative/Neutral
  "sentiment_score": 0.85,                       // Float - Confidence score (0-1)
  "source_pdf_url": "https://sebi.gov.in/...",  // String - Original PDF URL
  "page_number": 125,                            // Integer - Source page number
  "pan": "ABCDE1234F",                          // String - PAN number (if found)
  "cin": "U12345MH2020PTC123456",               // String - CIN number (if found)
  "address": "123 Business District, Mumbai...", // String - Extracted address
  "entity_context": "...text around entity...",  // String - Surrounding text for context
  "extracted_at": ISODate("2025-08-01T10:30:00Z"), // Date - Processing timestamp
  "processing_metadata": {
    "text_length": 15420,                        // Integer - Source text length
    "entity_position": {"start": 1250, "end": 1267}, // Object - Entity position in text
    "extraction_method": "spacy_ner"             // String - Extraction method used
  }
}
```

**Indexes Created:**
- `entity_name` (ascending)
- `entity_type` (ascending) 
- `sentiment` (ascending)
- `source_pdf_url` (ascending)
- `pan` (ascending)
- `cin` (ascending)
- `{entity_name: 1, pan: 1}` (compound index)

#### 2. `checkpoints` Collection  
Manages processing state and resume functionality.

```javascript
{
  "_id": ObjectId("..."),
  "type": "scraping_progress",                   // String - Checkpoint type identifier
  "last_page": 125,                             // Integer - Last successfully processed page
  "last_pdf_url": "https://sebi.gov.in/...",   // String - Last processed PDF URL
  "updated_at": ISODate("2025-08-01T10:30:00Z"), // Date - Last update timestamp
  
  // Individual PDF processing status
  "pdf_url": "https://sebi.gov.in/specific.pdf", // String - Specific PDF URL
  "status": "completed",                         // String - processing/completed/failed
  "started_at": ISODate("2025-08-01T10:25:00Z"), // Date - Processing start time
  "completed_at": ISODate("2025-08-01T10:30:00Z"), // Date - Processing completion time
  "entity_count": 15,                           // Integer - Number of entities extracted
  "error": null,                                // String - Error message (if failed)
  "retry_count": 0                              // Integer - Number of retry attempts
}
```

### IOSCO Scraper Collections

#### 1. `profiles` Collection
Stores organizational profile data from IOSCO I-SCAN.

```javascript
{
  "_id": ObjectId("..."),
  "name": "Securities and Exchange Commission", // String - Organization name
  "website": "https://www.sec.gov",             // String - Official website
  "country": "United States",                   // String - Country/jurisdiction
  "type": "Securities Regulator",               // String - Organization type
  "membership_status": "Ordinary Member",       // String - IOSCO membership status
  "details": {
    "full_name": "U.S. Securities and Exchange Commission",
    "established": "1934",                      // String - Year established
    "jurisdiction": "Federal",                  // String - Regulatory scope
    "contact_info": "...",                      // String - Contact details
    "regulatory_scope": "Securities markets...", // String - Areas of regulation
  },
  "scraped_at": ISODate("2025-08-01T10:30:00Z"), // Date - Extraction timestamp
  "profile_url": "https://iosco.org/profile/...", // String - Source profile URL
  "last_updated": ISODate("2025-08-01T10:30:00Z") // Date - Last data update
}
```

#### 2. `checkpoints` Collection
```javascript
{
  "_id": ObjectId("..."),
  "type": "profile",                            // String - Checkpoint type
  "last_index": 150,                           // Integer - Last processed table row index
  "total_processed": 150,                      // Integer - Total profiles processed
  "updated_at": ISODate("2025-08-01T10:30:00Z"), // Date - Last checkpoint update
  "batch_size": 10,                            // Integer - Processing batch size
  "session_id": "session_20250801_103000"     // String - Current scraping session ID
}
```

### Data Relationships
- **One-to-Many**: One PDF document → Multiple entities
- **One-to-Many**: One checkpoint entry → Multiple PDF processing records
- **Foreign Key Equivalent**: `source_pdf_url` links entities to their source documents

## Assumptions and Limitations

### Technical Assumptions

#### SEBI Scraper
1. **Website Structure Stability**
   - Assumes SEBI website HTML structure remains consistent
   - PDF links follow predictable URL patterns
   - Page pagination works with `pagenum` parameter

2. **PDF Format Consistency**
   - Assumes PDFs contain extractable text (not scanned images)
   - Text encoding is UTF-8 compatible
   - PDF structure allows PyPDF2 parsing

3. **Network and Performance**
   - Stable internet connection for downloading PDFs
   - MongoDB server availability and performance
   - Sufficient memory for NLP model loading (~500MB for spaCy + DistilBERT)

4. **Data Quality**
   - PAN numbers follow standard format: `[A-Z]{5}[0-9]{4}[A-Z]{1}`
   - CIN numbers follow format: `[UL]{1}[0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}`
   - Entity names are properly capitalized and formatted

#### IOSCO Scraper
1. **Dynamic Content Loading**
   - JavaScript-rendered content loads within reasonable timeframes
   - Chrome WebDriver compatibility with current Chrome versions
   - Table structure remains consistent across page loads

2. **Browser Dependencies**
   - Chrome browser installed and accessible
   - WebDriver manager can download compatible ChromeDriver
   - No corporate firewall blocking WebDriver downloads

### Functional Limitations

#### SEBI Scraper
1. **Entity Recognition Accuracy**
   - spaCy NER model accuracy ~85-90% for Indian names/organizations
   - False positives possible in entity classification
   - Context-based sentiment analysis may miss nuanced meanings

2. **PDF Processing Limitations**
   - Cannot process scanned/image-based PDFs without OCR
   - Complex PDF layouts may cause text extraction errors
   - Very large PDFs (>100MB) may cause memory issues

3. **Data Extraction Constraints**
   - PAN/CIN extraction relies on proximity to entity mentions
   - Address extraction uses pattern matching (may miss non-standard formats)
   - Sentiment analysis limited to English text only

4. **Scalability Limits**
   - Single-threaded processing (no parallel PDF downloads)
   - Memory usage scales with document size and batch processing
   - Rate limiting prevents high-speed scraping

#### IOSCO Scraper
1. **Browser Automation Limitations**
   - Selenium WebDriver slower than HTTP requests
   - Chrome browser updates may break compatibility
   - Dynamic content timing issues possible

2. **Data Completeness**
   - Profile detail extraction depends on consistent page structure
   - Some profiles may have incomplete information
   - Language barriers for non-English profiles

### Environmental Limitations

1. **Operating System Compatibility**
   - Tested on Windows PowerShell environment
   - Chrome WebDriver paths may differ on macOS/Linux
   - File path handling assumes Windows-style paths

2. **Resource Requirements**
   - Minimum 4GB RAM recommended for NLP models
   - ~2GB disk space for dependencies and models
   - MongoDB requires additional storage space

3. **Network Dependencies**
   - Requires internet access for model downloads
   - SEBI/IOSCO websites must be accessible
   - MongoDB Atlas requires internet connectivity

### Data Quality Limitations

1. **Source Data Quality**
   - Dependent on SEBI PDF quality and formatting
   - Manual data entry errors in source documents not corrected
   - Historical data may have different formatting standards

2. **Processing Accuracy**
   - NER accuracy varies with entity name complexity
   - Sentiment analysis may not capture regulatory context perfectly
   - Address extraction limited to common Indian address patterns

3. **Temporal Limitations**
   - No real-time data updates
   - Checkpoint system assumes sequential processing
   - Historical data processing may take considerable time

### Mitigation Strategies

1. **Error Handling**
   - Comprehensive try-catch blocks with logging
   - Retry mechanisms for network failures
   - Graceful degradation for partial failures

2. **Data Validation**
   - PAN/CIN format validation before storage
   - Duplicate entity detection and handling
   - Checkpoint integrity verification

3. **Monitoring and Alerting**
   - Detailed logging for debugging
   - Progress tracking and summary reports
   - Database connection health checks

### Future Enhancements

1. **Improved Accuracy**
   - Custom NER model training for Indian regulatory context
   - OCR integration for scanned PDF processing
   - Multi-language support for sentiment analysis

2. **Performance Optimization**
   - Parallel processing implementation
   - Incremental model loading
   - Database connection pooling

3. **Robustness Improvements**
   - Advanced retry logic with exponential backoff
   - Real-time website structure change detection
   - Automated model updates and compatibility checks