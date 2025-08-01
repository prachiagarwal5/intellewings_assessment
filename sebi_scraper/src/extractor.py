import io
import re
import time
import logging
import requests
import PyPDF2
from bs4 import BeautifulSoup
import urllib.parse

from config.config import DOWNLOAD_DELAY
from src.utils import retry_on_exception

logger = logging.getLogger(__name__)

class PDFExtractor:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    @retry_on_exception(max_retries=3)
    def download_pdf(self, url):
        """Download PDF content with retry logic"""
        logger.info(f"Downloading PDF from {url}")
        time.sleep(DOWNLOAD_DELAY)  # Ethical delay
        
        # Check if this is an HTML page that might contain PDF links
        if url.lower().endswith('.html'):
            return self.extract_pdf_from_html_page(url)
        else:
            # Direct PDF download
            response = self.session.get(url, stream=True)
            response.raise_for_status()
            return response.content
    
    def extract_pdf_from_html_page(self, url):
        """Extract PDF content from an HTML page that contains PDF links"""
        try:
            # First get the HTML page
            response = self.session.get(url)
            response.raise_for_status()
            
            # Parse HTML to find PDF links
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check for iframes first (SEBI uses these to embed PDFs)
            iframes = soup.find_all('iframe')
            for iframe in iframes:
                src = iframe.get('src', '')
                if src:
                    # Extract the actual PDF URL from the iframe src
                    # Handle the format: /web/?file=https://www.sebi.gov.in/sebi_data/attachdocs/...
                    if 'web/?file=' in src:
                        # Extract the actual PDF URL from the query parameter
                        query_parts = urllib.parse.urlparse(src).query.split('=')
                        if len(query_parts) > 1:
                            pdf_url = query_parts[1]  # This is the actual PDF URL
                            logger.info(f"Found PDF URL in iframe: {pdf_url}")
                            
                            try:
                                pdf_response = self.session.get(pdf_url, stream=True)
                                pdf_response.raise_for_status()
                                return pdf_response.content
                            except Exception as e:
                                logger.warning(f"Error downloading PDF from iframe: {str(e)}")
                    
                    # If direct PDF in iframe
                    elif src.lower().endswith('.pdf'):
                        # Make URL absolute
                        if not src.startswith('http'):
                            if src.startswith('/'):
                                src = f"https://www.sebi.gov.in{src}"
                            else:
                                base_url = '/'.join(url.split('/')[:-1])
                                src = f"{base_url}/{src}"
                        
                        logger.info(f"Found direct PDF in iframe: {src}")
                        try:
                            iframe_response = self.session.get(src, stream=True)
                            iframe_response.raise_for_status()
                            return iframe_response.content
                        except Exception as e:
                            logger.warning(f"Error downloading PDF from iframe: {str(e)}")
            
            # If no iframes with PDFs, look for direct PDF links
            pdf_links = []
            for link in soup.find_all('a'):
                href = link.get('href', '')
                if href and href.lower().endswith('.pdf'):
                    # Make URL absolute
                    if not href.startswith('http'):
                        if href.startswith('/'):
                            href = f"https://www.sebi.gov.in{href}"
                        else:
                            base_url = '/'.join(url.split('/')[:-1])
                            href = f"{base_url}/{href}"
                    
                    pdf_links.append(href)
            
            # If direct PDF links found, download the first one
            if pdf_links:
                logger.info(f"Found direct PDF link: {pdf_links[0]}")
                try:
                    pdf_response = self.session.get(pdf_links[0], stream=True)
                    pdf_response.raise_for_status()
                    return pdf_response.content
                except Exception as e:
                    logger.warning(f"Error downloading PDF from direct link: {str(e)}")
            
            # If no PDF found via iframe or direct links, look for embedded objects
            embed_tags = soup.find_all('embed')
            for embed in embed_tags:
                src = embed.get('src', '')
                if src and src.lower().endswith('.pdf'):
                    # Make URL absolute
                    if not src.startswith('http'):
                        if src.startswith('/'):
                            src = f"https://www.sebi.gov.in{src}"
                        else:
                            base_url = '/'.join(url.split('/')[:-1])
                            src = f"{base_url}/{src}"
                    
                    logger.info(f"Found PDF in embed tag: {src}")
                    try:
                        embed_response = self.session.get(src, stream=True)
                        embed_response.raise_for_status()
                        return embed_response.content
                    except Exception as e:
                        logger.warning(f"Error downloading PDF from embed tag: {str(e)}")
            
            # If we reach here, we need to extract text from the HTML page itself
            logger.info("No PDF found, extracting text from HTML page")
            
            # Get main content
            main_content = soup.select_one('main, #main-content, .content, article, .order-content')
            if main_content:
                return main_content.get_text()
            else:
                # Fall back to body text
                body = soup.find('body')
                return body.get_text() if body else "No content found"
                
        except Exception as e:
            logger.error(f"Error extracting PDF from HTML page: {str(e)}")
            return None
    
    def extract_text_from_pdf(self, content):
        """Extract text from PDF binary content or HTML text"""
        # Check if content is already text (from HTML extraction)
        if isinstance(content, str):
            return content
            
        # If no content
        if not content:
            return ""
            
        try:
            # Try to process as PDF
            pdf_file = io.BytesIO(content)
            
            try:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                
                text = ""
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                
                if text:
                    return text
                else:
                    logger.warning("PDF had no extractable text")
                    return "PDF had no extractable text"
                    
            except Exception as pdf_error:
                logger.error(f"Error extracting text from PDF: {str(pdf_error)}")
                
                # Try to treat content as HTML as a fallback
                try:
                    html_text = content.decode('utf-8')
                    soup = BeautifulSoup(html_text, 'html.parser')
                    return soup.get_text()
                except:
                    # If all fails, return empty string
                    return ""
                
        except Exception as e:
            logger.error(f"Error extracting text: {str(e)}")
            return ""
    
    def extract_entities_from_text(self, text, nlp_model):
        """Extract entities from text using spaCy"""
        # Limit text size to avoid memory issues with large documents
        max_text_length = 100000  # 100K characters should be enough for most documents
        if len(text) > max_text_length:
            logger.warning(f"Text too large ({len(text)} chars), truncating to {max_text_length}")
            text = text[:max_text_length]
        
        doc = nlp_model(text)
        entities = []
        
        for ent in doc.ents:
            if ent.label_ in ["PERSON", "ORG"]:
                entity_type = "Person" if ent.label_ == "PERSON" else "Company"
                
                entities.append({
                    "text": ent.text,
                    "type": entity_type,
                    "start": ent.start_char,
                    "end": ent.end_char
                })
        
        return entities
    
    def extract_pan_numbers(self, text):
        """Extract PAN numbers from text with improved pattern matching"""
    
        pan_patterns = [
            r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b',  
            r'PAN[:\s]+([A-Z]{5}[0-9]{4}[A-Z]{1})',
            r'PAN[:\s]*No[.\s]*[:\s]*([A-Z]{5}[0-9]{4}[A-Z]{1})',  
            r'Permanent[:\s]+Account[:\s]+Number[:\s]+([A-Z]{5}[0-9]{4}[A-Z]{1})',  
        ]
        
        pan_numbers = set()  # Use set to avoid duplicates
        
        for pattern in pan_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # If the pattern has groups, take the first group; otherwise, take the whole match
                pan = match if isinstance(match, str) else match[0] if match else None
                if pan and len(pan) == 10:  # PAN should be exactly 10 characters
                    pan_numbers.add(pan.upper())
        
        return list(pan_numbers)
    
    def extract_cin_numbers(self, text):
        """Extract CIN numbers from text with improved pattern matching"""
        # Improved CIN patterns
        cin_patterns = [
            r'\b[UL]{1}[0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}\b',  
            r'CIN[:\s]+([UL]{1}[0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6})',  
            r'CIN[:\s]*No[.\s]*[:\s]*([UL]{1}[0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6})',  
            r'Corporate[:\s]+Identification[:\s]+Number[:\s]+([UL]{1}[0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6})',  
        ]
        
        cin_numbers = set()  # Use set to avoid duplicates
        
        for pattern in cin_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # If the pattern has groups, take the first group; otherwise, take the whole match
                cin = match if isinstance(match, str) else match[0] if match else None
                if cin and len(cin) == 21:  # CIN should be exactly 21 characters
                    cin_numbers.add(cin.upper())
        
        return list(cin_numbers)
    
    def extract_addresses(self, text):
        """Extract potential addresses from text with improved patterns"""
        address_patterns = [
            r'(?:residing at|located at|address[:\s]+)([^\.;,]*(?:Road|Street|Avenue|Lane|Nagar|Colony|Park|Building|Plot|House|Flat)[^\.;,]*)',
            r'(?:Address[:\s]+)([^\.;,\n]{20,100})',  
            r'(?:Registered Office[:\s]+)([^\.;,\n]{20,150})',  
            r'(?:Corporate Office[:\s]+)([^\.;,\n]{20,150})',  
            r'([A-Z][^\.;,\n]*(?:Mumbai|Delhi|Bangalore|Chennai|Kolkata|Hyderabad|Pune|Ahmedabad|Surat|Jaipur|Lucknow|Kanpur|Nagpur|Indore|Bhopal|Visakhapatnam|Patna|Ludhiana|Agra|Nashik|Faridabad|Meerut|Rajkot|Kalyan|Vasai|Varanasi|Srinagar|Aurangabad|Dhanbad|Amritsar|Navi Mumbai|Allahabad|Howrah|Ranchi|Gwalior|Jabalpur|Coimbatore|Vijayawada|Jodhpur|Madurai|Raipur|Kota|Guwahati|Chandigarh|Solapur|Hubli|Tiruchirappalli|Bareilly|Mysore|Tiruppur|Gurgaon|Aligarh|Jalandhar|Bhubaneswar|Salem|Warangal|Guntur|Bhiwandi|Saharanpur|Gorakhpur|Bikaner|Amravati|Noida|Jamshedpur|Bhilai|Cuttack|Firozabad|Kochi|Nellore|Bhavnagar|Dehradun|Durgapur|Asansol|Rourkela|Nanded|Kolhapur|Ajmer|Akola|Gulbarga|Jamnagar|Ujjain|Loni|Siliguri|Jhansi|Ulhasnagar|Jammu|Sangli|Mangalore|Erode|Belgaum|Ambattur|Tirunelveli|Malegaon|Gaya|Jalgaon|Udaipur|Maheshtala)[^\.;,\n]*)',  # Cities
        ]
        
        addresses = set()  # Use set to avoid duplicates
        
        for pattern in address_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                address = match.strip()
                if len(address) > 10:  # Filter out very short matches
                    addresses.add(address[:200])  # Limit length
        
        return list(addresses)
    
    def get_entity_context(self, text, entity, window_size=300):
        """Get text around an entity mention for context analysis"""
        start = max(0, entity["start"] - window_size)
        end = min(len(text), entity["end"] + window_size)
        return text[start:end]
    
    def extract_entity_pan_pairs(self, text, entities):
        """Extract entity-PAN pairs by analyzing proximity and context"""
        entity_pan_pairs = []
        
        # Get all PAN numbers with their positions
        pan_pattern = r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b'
        pan_matches = []
        for match in re.finditer(pan_pattern, text):
            pan_matches.append({
                'pan': match.group(),
                'start': match.start(),
                'end': match.end()
            })
        
        logger.info(f"Found {len(pan_matches)} PAN numbers in text")
        
        # For each entity, find the closest PAN
        for entity in entities:
            closest_pan = None
            min_distance = float('inf')
            
            for pan_match in pan_matches:
                # Calculate distance between entity and PAN
                entity_center = (entity['start'] + entity['end']) / 2
                pan_center = (pan_match['start'] + pan_match['end']) / 2
                distance = abs(entity_center - pan_center)
                
                # If this PAN is closer and within reasonable distance (2000 chars)
                if distance < min_distance and distance < 2000:
                    min_distance = distance
                    closest_pan = pan_match['pan']
            
            if closest_pan:
                entity_pan_pairs.append({
                    'entity': entity['text'],
                    'entity_type': entity['type'],
                    'pan': closest_pan,
                    'distance': min_distance
                })
                logger.info(f"Paired entity '{entity['text']}' with PAN '{closest_pan}' (distance: {min_distance:.0f})")
        
        return entity_pan_pairs