# PART A: SEBI Enforcement Orders Scraper

A Python web scraper that extracts and analyzes SEBI enforcement orders with NLP capabilities.

## ✨ Features

- 🔍 **PDF Extraction** - Scrapes enforcement order PDFs from SEBI website
- 🤖 **NLP Analysis** - Named Entity Recognition + Sentiment Analysis
- 🏢 **Entity Detection** - Extracts persons, companies, PAN/CIN numbers
- 📊 **MongoDB Storage** - Structured data storage with indexing
- ⚡ **Smart Checkpointing** - Resume from interruptions
- 🛡️ **Ethical Scraping** - Rate limiting and respectful requests

## 🚀 Quick Start

### Installation
```bash
# Clone & setup
git clone <repo-url> && cd sebi_scraper
python -m venv venv && venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_lg
```

### Configuration
Create `.env`:
```env
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/
```

### Run
```bash
python main.py
```

## 📊 Database Schema

### Collection: `entities`
```javascript
{
  "entity_name": "John Doe",
  "entity_type": "Person|Company", 
  "sentiment": "Positive|Negative|Neutral",
  "pan": "ABCDE1234F",
  "cin": "U12345MH2020PTC123456",
  "source_pdf_url": "https://...",
  "created_at": "2025-07-31T..."
}
```

### Collection: `checkpoints`
```javascript
{
  "pdf_url": "https://...",
  "status": "completed|processing|failed",
  "entity_count": 15,
  "completed_at": "2025-07-31T..."
}
```

## ⚙️ Key Settings

```python
# config/config.py
BASE_URL = "https://www.sebi.gov.in/..."
START_PAGE = 1
END_PAGE = 5
REQUEST_DELAY = 0.2  # Rate limiting
```

## 🔄 Checkpointing

- **Page-level**: Resumes from last processed page
- **PDF-level**: Skips already processed documents  
- **Error handling**: Marks failed PDFs for retry
- **Progress tracking**: Entity counts and timestamps

## 📝 Usage Examples

```bash
# Basic run
python main.py

# Fresh start (reset checkpoints)
RESET_CHECKPOINT=true python main.py

# View logs
tail -f logs/sebi_scraper_*.log
```

## 🛠️ Tech Stack

- **Web Scraping**: Beautiful Soup + Requests
- **NLP**: spaCy (NER) + Transformers (Sentiment)
- **PDF Processing**: PyPDF2 + pdfplumber
- **Database**: MongoDB + PyMongo
- **Language**: Python 3.8+

## 📈 Output

The scraper produces:
- **Structured entities** with sentiment scores
- **Progress checkpoints** for reliability  
- **Detailed logs** for monitoring
- **MongoDB collections** ready for analysis
