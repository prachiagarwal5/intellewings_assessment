import time
import logging
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import re
import json

from config.config import BASE_URL, REQUEST_DELAY
from src.utils import retry_on_exception, is_valid_pdf_url

logger = logging.getLogger(__name__)

class SEBIScraper:
    def __init__(self, db):
        self.db = db
        self.session = requests.Session()
        # Set a reasonable user agent
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    @retry_on_exception(max_retries=3)
    def fetch_page(self, url):
        """Fetch a page with retry logic and delays"""
        logger.info(f"Fetching page: {url}")
        time.sleep(REQUEST_DELAY)  # Ethical delay between requests
        response = self.session.get(url)
        response.raise_for_status()
        return response.text
    
    def extract_data_from_js(self, html_content):
        """Try to extract data from JavaScript if the page uses JS to load content"""
        # Pattern for finding data arrays in JavaScript
        pattern = re.compile(r'var\s+data\s*=\s*(\[.*?\]);', re.DOTALL)
        match = pattern.search(html_content)
        
        if match:
            data_str = match.group(1)
            try:
                data = json.loads(data_str)
                logger.info(f"Successfully extracted {len(data)} items from JavaScript data")
                return data
            except json.JSONDecodeError:
                logger.warning("Found data variable but couldn't parse as JSON")
        
        return []
    
    def get_pdf_links_from_page(self, page_number):
        """Extract PDF links from a specific page"""
        # Try different URL formats
        url_formats = [
            f"{BASE_URL}?pagenum={page_number}",
            f"https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=2&ssid=9&smid=6&page={page_number}",
            f"https://www.sebi.gov.in/enforcement/orders/jul-2025.html?pagenum={page_number}"
        ]
        
        for url in url_formats:
            try:
                html_content = self.fetch_page(url)
                soup = BeautifulSoup(html_content, 'html.parser')
                
                logger.info(f"Searching for order links on page {page_number} using URL: {url}")
                
                # Try to extract data from JavaScript first
                js_data = self.extract_data_from_js(html_content)
                if js_data:
                    # If data was found in JavaScript, process it
                    pdf_links = []
                    for item in js_data:
                        # The structure depends on SEBI's specific implementation
                        # Common fields might include 'title', 'link', 'date', etc.
                        if isinstance(item, dict):
                            pdf_url = item.get('pdfLink') or item.get('link') or item.get('url')
                            title = item.get('title') or item.get('name') or "Unknown Title"
                            print(f"Found PDF: {title}")
                            date = item.get('date') or self.extract_date_from_text(title)
                            
                            if pdf_url and pdf_url.lower().endswith('.pdf'):
                                # Make URL absolute
                                if not pdf_url.startswith('http'):
                                    if pdf_url.startswith('/'):
                                        pdf_url = f"https://www.sebi.gov.in{pdf_url}"
                                    else:
                                        pdf_url = f"https://www.sebi.gov.in/{pdf_url}"
                                
                                pdf_links.append({
                                    'url': pdf_url,
                                    'title': title,
                                    'date': date
                                })
                    
                    if pdf_links:
                        logger.info(f"Found {len(pdf_links)} PDF links in JavaScript data")
                        return pdf_links
                
                # If no JS data, try different HTML patterns for SEBI orders
                
                # 1. Try to find orders in tables
                tables = soup.select('table')
                pdf_links = []
                
                for table in tables:
                    rows = table.select('tr')
                    for row in rows[1:]:  # Skip header row
                        cells = row.select('td')
                        if len(cells) >= 2:
                            # Look for links in cells
                            links = row.select('a')
                            for link in links:
                                href = link.get('href', '')
                                text = link.get_text(strip=True)
                                
                                if href and ('pdf' in href.lower() or 'order' in href.lower()):
                                    # Make URL absolute
                                    if not href.startswith('http'):
                                        if href.startswith('/'):
                                            href = f"https://www.sebi.gov.in{href}"
                                        else:
                                            href = f"https://www.sebi.gov.in/{href}"
                                    
                                    date_cell = cells[0] if len(cells) > 0 else None
                                    date = date_cell.get_text(strip=True) if date_cell else "Unknown"
                                    
                                    pdf_links.append({
                                        'url': href,
                                        'title': text,
                                        'date': date
                                    })
                
                # 2. Try to find orders in list items
                list_items = soup.select('ul.doclinks li, ul.listing li, div.order-item')
                for item in list_items:
                    links = item.select('a')
                    for link in links:
                        href = link.get('href', '')
                        text = link.get_text(strip=True)
                        
                        if href and ('pdf' in href.lower() or 'order' in href.lower()):
                            # Make URL absolute
                            if not href.startswith('http'):
                                if href.startswith('/'):
                                    href = f"https://www.sebi.gov.in{href}"
                                else:
                                    href = f"https://www.sebi.gov.in/{href}"
                            
                            date = self.extract_date_from_text(text)
                            
                            pdf_links.append({
                                'url': href,
                                'title': text,
                                'date': date
                            })
                
                # 3. Try to find orders in any container that looks like a list
                containers = soup.select('div.listing, div.orders-container, div.sebi-list')
                for container in containers:
                    links = container.select('a')
                    for link in links:
                        href = link.get('href', '')
                        text = link.get_text(strip=True)
                        
                        if href and ('pdf' in href.lower() or 'order' in href.lower()):
                            # Make URL absolute
                            if not href.startswith('http'):
                                if href.startswith('/'):
                                    href = f"https://www.sebi.gov.in{href}"
                                else:
                                    href = f"https://www.sebi.gov.in/{href}"
                            
                            date = self.extract_date_from_text(text)
                            
                            pdf_links.append({
                                'url': href,
                                'title': text,
                                'date': date
                            })
                
                # 4. Try to find links to detail pages that might contain PDFs
                order_detail_links = []
                for link in soup.select('a'):
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    # This pattern matches links to specific enforcement order detail pages
                    if (href and 
                        ('enforcement/orders' in href.lower() or 
                         'adjudication-order' in href.lower() or 
                         'sebi.gov.in/enforcement' in href.lower()) and 
                        '.html' in href.lower() and 
                        'pdf' not in href.lower()):  # Not a direct PDF link
                        
                        # Make URL absolute
                        if not href.startswith('http'):
                            if href.startswith('/'):
                                href = f"https://www.sebi.gov.in{href}"
                            else:
                                href = f"https://www.sebi.gov.in/{href}"
                        
                        order_detail_links.append({
                            'url': href,
                            'title': text
                        })
                
                # If we found detail links, visit them to find PDFs
                if order_detail_links and len(pdf_links) < 5:  # Only if we don't already have many PDFs
                    logger.info(f"Found {len(order_detail_links)} order detail links to check")
                    for detail_link in order_detail_links[:5]:  # Limit to first 5
                        try:
                            detail_html = self.fetch_page(detail_link['url'])
                            detail_soup = BeautifulSoup(detail_html, 'html.parser')
                            
                            # Find PDF links on the detail page
                            for detail_link_elem in detail_soup.select('a'):
                                detail_href = detail_link_elem.get('href', '')
                                
                                if detail_href and detail_href.lower().endswith('.pdf'):
                                    detail_text = detail_link_elem.get_text(strip=True) or detail_link['title']
                                    
                                    # Make URL absolute
                                    if not detail_href.startswith('http'):
                                        if detail_href.startswith('/'):
                                            detail_href = f"https://www.sebi.gov.in{detail_href}"
                                        else:
                                            detail_href = f"https://www.sebi.gov.in/{detail_href}"
                                    
                                    date = self.extract_date_from_text(detail_text)
                                    
                                    pdf_links.append({
                                        'url': detail_href,
                                        'title': detail_text,
                                        'date': date,
                                        'source_page': detail_link['url']
                                    })
                            
                            logger.info(f"Found {len(detail_soup.select('a[href$=\'.pdf\']'))} PDF links on detail page")
                                
                        except Exception as e:
                            logger.error(f"Error processing detail page {detail_link['url']}: {str(e)}")
                
                # Return links if we found any with this URL format
                if pdf_links:
                    logger.info(f"Found {len(pdf_links)} PDF links on page {page_number}")
                    return pdf_links
                
            except Exception as e:
                logger.error(f"Error scraping URL {url}: {str(e)}")
        
        # If we couldn't find any PDFs with any URL format
        logger.warning(f"Could not find any PDF links on page {page_number}")
        return []
    
    def extract_date_from_text(self, text):
        """Extract date information from text"""
        # Look for date patterns in text
        date_match = re.search(r'(\d{1,2})[-/\.](\d{1,2})[-/\.](\d{2,4})', text)
        if date_match:
            return f"{date_match.group(1)}/{date_match.group(2)}/{date_match.group(3)}"
        
        # Look for month name patterns
        month_match = re.search(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* (\d{1,2})[,\s]+(\d{4})', text, re.IGNORECASE)
        if month_match:
            return f"{month_match.group(1)} {month_match.group(2)}, {month_match.group(3)}"
            
        return "Unknown"
    
    def scrape_pdf_links(self, start_page, end_page, resume_from_pdf=None):
        """Scrape PDF links from multiple pages with checkpointing"""
        all_pdf_links = []
        resume_found = False if resume_from_pdf else True
        
        # If no PDF links are found on the first few pages, try a different approach
        if start_page == 1:
            # First try to get latest orders directly
            try:
                # Try to access month archives directly
                current_month_links = self.get_month_archive_links()
                if current_month_links:
                    logger.info(f"Found {len(current_month_links)} month archive links")
                    for month_link in current_month_links[:3]:  # Check first 3 months
                        try:
                            month_html = self.fetch_page(month_link['url'])
                            month_soup = BeautifulSoup(month_html, 'html.parser')
                            
                            # Look for PDF links on month page
                            for link in month_soup.select('a'):
                                href = link.get('href', '')
                                text = link.get_text(strip=True)
                                
                                if href and href.lower().endswith('.pdf'):
                                    # Make URL absolute
                                    if not href.startswith('http'):
                                        if href.startswith('/'):
                                            href = f"https://www.sebi.gov.in{href}"
                                        else:
                                            href = f"https://www.sebi.gov.in/{href}"
                                    
                                    all_pdf_links.append({
                                        'url': href,
                                        'title': text,
                                        'date': month_link['month']
                                    })
                            
                            logger.info(f"Found {len(month_soup.select('a[href$=\'.pdf\']'))} PDF links in {month_link['month']} archive")
                                
                        except Exception as e:
                            logger.error(f"Error processing month archive {month_link['url']}: {str(e)}")
                
            except Exception as e:
                logger.error(f"Error fetching month archives: {str(e)}")
        
        # Regular page-by-page scraping
        for page_num in tqdm(range(start_page, end_page + 1), desc="Scraping pages"):
            pdf_links = self.get_pdf_links_from_page(page_num)
            
            # Update checkpoint for this page
            if pdf_links:
                self.db.update_checkpoint(page_num, pdf_links[-1]['url'])
            else:
                self.db.update_checkpoint(page_num)
            
            # Handle resuming logic
            if not resume_found:
                for i, pdf in enumerate(pdf_links):
                    if pdf['url'] == resume_from_pdf:
                        # Found the PDF to resume from, include all subsequent PDFs
                        all_pdf_links.extend(pdf_links[i+1:])
                        resume_found = True
                        break
            else:
                # Already found resume point or not resuming, include all PDFs
                all_pdf_links.extend(pdf_links)
        
        return all_pdf_links
    
    def get_month_archive_links(self):
        """Try to get direct links to monthly archives"""
        try:
            # First try the main orders page
            main_url = "https://www.sebi.gov.in/enforcement/orders.html"
            html_content = self.fetch_page(main_url)
            soup = BeautifulSoup(html_content, 'html.parser')
            
            month_links = []
            for link in soup.select('a'):
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Look for month archive patterns
                if href and re.search(r'/(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)-\d{4}', href, re.IGNORECASE):
                    # Extract month and year from URL
                    month_match = re.search(r'/(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)-(\d{4})', href, re.IGNORECASE)
                    if month_match:
                        month = f"{month_match.group(1).capitalize()} {month_match.group(2)}"
                    else:
                        month = "Unknown"
                    
                    # Make URL absolute
                    if not href.startswith('http'):
                        if href.startswith('/'):
                            href = f"https://www.sebi.gov.in{href}"
                        else:
                            href = f"https://www.sebi.gov.in/{href}"
                    
                    month_links.append({
                        'url': href,
                        'text': text,
                        'month': month
                    })
            
            return month_links
            
        except Exception as e:
            logger.error(f"Error getting month archive links: {str(e)}")
            return []