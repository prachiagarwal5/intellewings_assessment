# intellewings_assessment
# Part A:SEBI Enforcement Orders Scraper

A comprehensive web scraping solution for extracting and analyzing SEBI (Securities and Exchange Board of India) enforcement orders. This project automatically scrapes enforcement order PDFs, extracts entity information, performs sentiment analysis, and stores structured data in MongoDB with advanced checkpointing capabilities.

## 🚀 Features

- **Intelligent PDF Extraction**: Handles both direct PDF links and HTML pages containing embedded PDFs
- **Named Entity Recognition**: Extracts persons and companies using spaCy NLP models
- **Sentiment Analysis**: Analyzes regulatory sentiment using transformer models
- **PAN/CIN Extraction**: Identifies Indian regulatory identifiers (PAN/CIN numbers)
- **Address Extraction**: Extracts address information from documents
- **Robust Checkpointing**: Resume processing from interruption points
- **Ethical Scraping**: Rate limiting and respectful request patterns
- **Comprehensive Logging**: Detailed logs for monitoring and debugging

## 📋 Prerequisites

- Python 3.8 or higher
- MongoDB instance (local or cloud)
- At least 2GB RAM (for NLP models)
- Stable internet connection

## 🛠️ Setup Instructions

### 1. Clone and Navigate
```bash
git clone <repository-url>
cd sebi_scraper
```

### 2. Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Download spaCy Model
```bash
python -m spacy download en_core_web_lg
```

### 5. Environment Configuration
Create a `.env` file in the root directory:
```env
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/
RESET_CHECKPOINT=false
```

### 6. MongoDB Setup
- Ensure MongoDB is running and accessible
- The application will automatically create required databases and collections
- Update `MONGO_URI` in `config/config.py` or `.env` file

### 7. Run the Scraper
```bash
# Run with default settings
python main.py

# Reset checkpoints and start fresh
RESET_CHECKPOINT=true python main.py
```

## 📊 MongoDB Schema Description

### Database: `sebi_enforcement`

#### Collection: `entities`
Stores extracted entities with comprehensive metadata:

```javascript
{
  "_id": ObjectId("..."),
  "entity_name": "John Doe",              // Extracted entity name
  "entity_type": "Person" | "Company",   // Entity classification
  "sentiment": "Positive" | "Negative" | "Neutral",  // Sentiment analysis result
  "source_pdf_url": "https://...",       // Source PDF URL
  "pdf_title": "Enforcement Order Title", // PDF document title
  "pdf_date": "2025-07-31",             // Document date
  "pan": "ABCDE1234F",                  // PAN number (if found)
  "cin": "U12345MH2020PTC123456",       // CIN number (if found)
  "address": "123 Business Street...",   // Address (if found)
  "created_at": ISODate("..."),         // Record creation timestamp
  "updated_at": ISODate("...")          // Last update timestamp
}
```

**Indexes:**
- `entity_name` (ascending)
- `entity_type` (ascending)  
- `sentiment` (ascending)
- `source_pdf_url` (ascending)

#### Collection: `checkpoints`
Manages processing progress and recovery:

```javascript
// Main scraping progress
{
  "_id": ObjectId("..."),
  "type": "scraping_progress",
  "last_page": 425,                     // Last processed page number
  "last_pdf_url": "https://...",        // Last processed PDF URL
  "updated_at": ISODate("...")
}

// Individual PDF processing status
{
  "_id": ObjectId("..."),
  "pdf_url": "https://...",             // PDF URL being tracked
  "status": "processing" | "completed" | "failed",
  "started_at": ISODate("..."),         // Processing start time
  "completed_at": ISODate("..."),       // Completion time (if successful)
  "failed_at": ISODate("..."),          // Failure time (if failed)
  "error": "Error message",             // Error details (if failed)
  "entity_count": 15                    // Number of entities extracted
}
```

## 🔄 Checkpointing Mechanism

### Multi-Level Checkpointing System

#### 1. **Page-Level Checkpointing**
- Tracks the last successfully processed page number
- Automatically resumes from the last page on restart
- Updates after each page is fully processed

#### 2. **PDF-Level Tracking**
- Individual PDF processing status (processing/completed/failed)
- Prevents reprocessing of already completed PDFs
- Tracks entity count per PDF for statistics

#### 3. **Resume Logic**
```python
# Get checkpoint
last_page, last_pdf = db.get_last_checkpoint()
start_page = max(last_page, START_PAGE)

# Resume from specific PDF if provided
if resume_from_pdf:
    # Skip PDFs until reaching the resume point
    resume_found = False
    for pdf in pdf_links:
        if pdf['url'] == resume_from_pdf:
            resume_found = True
        if resume_found:
            process_pdf(pdf)
```

#### 4. **Error Recovery**
- Failed PDFs are marked with error details
- Processing continues with next PDFs
- Failed PDFs can be retried in subsequent runs
- Detailed error logging for debugging

#### 5. **Checkpoint Updates**
- **After each page**: Update page number and last PDF
- **Before PDF processing**: Mark PDF as "processing"
- **After successful extraction**: Mark as "completed" with entity count
- **On error**: Mark as "failed" with error message

## ⚙️ Configuration

### Key Configuration Files

#### `config/config.py`
```python
# MongoDB Settings
MONGO_URI = "mongodb+srv://..."
MONGO_DB = "sebi_enforcement"
ENTITIES_COLLECTION = "entities"
CHECKPOINTS_COLLECTION = "checkpoints"

# Scraping Settings
BASE_URL = "https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=2&ssid=9&smid=6"
START_PAGE = 1
END_PAGE = 5
REQUEST_DELAY = 0.2  # 200ms between requests
DOWNLOAD_DELAY = 0.5  # 500ms for PDF downloads
```

### Customizable Parameters
- **Page Range**: Modify `START_PAGE` and `END_PAGE`
- **Delays**: Adjust `REQUEST_DELAY` and `DOWNLOAD_DELAY` for ethical scraping
- **Text Limits**: Modify `max_text_length` in extractor for memory management

## 📝 Usage Examples

### Basic Usage
```bash
python main.py
```

### Reset and Start Fresh
```bash
RESET_CHECKPOINT=true python main.py
```

### Custom Page Range
Modify `config/config.py`:
```python
START_PAGE = 100
END_PAGE = 200
```

## 🔍 Monitoring and Logs

### Log Files
- Location: `logs/sebi_scraper_YYYYMMDD.log`
- Includes: Request details, extraction results, errors, progress updates

### Key Log Messages
- `"Found X PDF links on page Y"` - Successful page scraping
- `"Saved X entities from PDF"` - Successful entity extraction
- `"Skipping already processed PDF"` - Checkpoint working
- `"Error processing PDF: ..."` - Processing errors

### Progress Monitoring
```bash
# Monitor real-time logs
tail -f logs/sebi_scraper_20250731.log

# Check processing statistics
grep "Saved.*entities" logs/sebi_scraper_20250731.log
```

## 📊 Data Analysis

### Query Examples

```javascript
// Find all entities with negative sentiment
db.entities.find({"sentiment": "Negative"})

// Count entities by type
db.entities.aggregate([
  {"$group": {"_id": "$entity_type", "count": {"$sum": 1}}}
])

// Find entities with PAN numbers
db.entities.find({"pan": {"$exists": true}})

// Processing statistics
db.checkpoints.find({"status": "completed"}).count()
```

## 🚫 Assumptions and Limitations

### Assumptions
1. **SEBI Website Structure**: Assumes current SEBI website structure for enforcement orders
2. **PDF Format**: Expects standard PDF formats or HTML pages with embedded PDFs
3. **MongoDB Availability**: Requires accessible MongoDB instance
4. **Internet Connectivity**: Stable connection for continuous scraping
5. **Page Numbering**: Assumes sequential page numbering system

### Limitations

#### Technical Limitations
- **Text Extraction**: Limited to 100K characters per document to prevent memory issues
- **PDF Processing**: Some scanned PDFs may not extract text properly
- **Entity Recognition**: Accuracy depends on spaCy model performance
- **Language Support**: Optimized for English text only

#### Rate Limiting
- **Request Delays**: Minimum 200ms between requests
- **PDF Downloads**: 500ms delay between PDF downloads
- **Session Management**: Single session to maintain connection efficiency

#### Data Quality
- **Entity Accuracy**: NER model may miss complex entity names
- **Sentiment Context**: Limited to 300-character context window
- **Date Extraction**: Pattern-based date extraction may not catch all formats
- **Address Extraction**: Simplified patterns may miss complex addresses

#### Scalability
- **Memory Usage**: Large documents may cause memory issues
- **Processing Speed**: Sequential processing (no parallel downloads)
- **Storage**: MongoDB storage requirements grow with data volume

### Known Issues
1. **JavaScript-Heavy Pages**: May not capture all dynamically loaded content
2. **CAPTCHA/Rate Limiting**: Website may implement anti-scraping measures
3. **URL Changes**: SEBI website structure changes may break scraping
4. **PDF Corruption**: Some PDFs may be corrupted or inaccessible



## 🙏 Acknowledgments

- [spaCy](https://spacy.io/) for Named Entity Recognition
- [Hugging Face Transformers](https://huggingface.co/transformers/) for sentiment analysis
- [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/) for HTML parsing
- [PyPDF2](https://pypdf2.readthedocs.io/) for PDF text extraction
- [MongoDB](https://www.mongodb.com/) for data storage


