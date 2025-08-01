import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from src.db import profiles_collection, checkpoint_collection

URL = "https://www.iosco.org/i-scan/"

def load_checkpoint():
    checkpoint = checkpoint_collection.find_one({"type": "profile"})
    return checkpoint["last_index"] if checkpoint else 0

def save_checkpoint(index):
    checkpoint_collection.update_one(
        {"type": "profile"},
        {"$set": {"last_index": index}},
        upsert=True
    )

def extract_profile_data(row, driver, main_window):
    """Extract comprehensive data from a table row and detail page"""
    try:
        cells = row.find_elements(By.TAG_NAME, "td")
        if len(cells) >= 6:  # Now we know there are 6 cells
            # Basic data from table row
            profile_data = {
                "name": cells[0].text.strip(),
                "website": cells[2].text.strip() if len(cells) > 2 else "",
                "authority": cells[3].text.strip() if len(cells) > 3 else "",
                "date": cells[4].text.strip() if len(cells) > 4 else "",
                "status": "Alert/Warning",  # Default status for I-SCAN entries
                "nature_of_violation": "",
                "actions_taken": "",
                "additional_metadata": {
                    "scraped_at": time.time(),
                    "region": "",
                    "source": "IOSCO I-SCAN"
                }
            }
            
            # Extract region from authority if available
            authority_text = profile_data["authority"]
            if " - " in authority_text:
                parts = authority_text.split(" - ")
                if len(parts) >= 2:
                    profile_data["additional_metadata"]["region"] = parts[0].strip()
                    profile_data["authority"] = parts[1].strip()
            
            # Try to click "View More" for additional details
            try:
                # Look for clickable elements in the "View More" cell
                view_more_cell = cells[5] if len(cells) > 5 else None
                if view_more_cell:
                    # Try different ways to find the clickable element
                    clickable_elements = []
                    
                    # Try to find links
                    links = view_more_cell.find_elements(By.TAG_NAME, "a")
                    clickable_elements.extend(links)
                    
                    # Try to find buttons
                    buttons = view_more_cell.find_elements(By.TAG_NAME, "button")
                    clickable_elements.extend(buttons)
                    
                    # Try to find any clickable element
                    clickable = view_more_cell.find_elements(By.CSS_SELECTOR, "[onclick], [data-toggle], [data-target]")
                    clickable_elements.extend(clickable)
                    
                    if clickable_elements:
                        clickable_element = clickable_elements[0]
                        print(f"  Found clickable element: {clickable_element.tag_name}")
                        
                        # Click the element
                        driver.execute_script("arguments[0].click();", clickable_element)
                        time.sleep(3)
                        
                        # Check if modal opened
                        modals = driver.find_elements(By.CSS_SELECTOR, ".modal.show, .modal-dialog, .modal.fade.show, [class*='modal'][style*='display: block']")
                        
                        if modals:
                            # Extract data from modal
                            modal = modals[0]
                            modal_text = modal.text
                            
                            # Parse modal content for additional fields
                            profile_data["nature_of_violation"] = extract_violation_info(modal_text)
                            profile_data["actions_taken"] = extract_actions_info(modal_text)
                            profile_data["additional_metadata"]["modal_content"] = modal_text[:500]
                            
                            print(f"  Extracted modal data for: {profile_data['name']}")
                            
                            # Close modal
                            close_buttons = driver.find_elements(By.CSS_SELECTOR, ".modal .btn-close, .modal .close, .modal button[data-dismiss='modal'], .modal .btn-secondary")
                            if close_buttons:
                                driver.execute_script("arguments[0].click();", close_buttons[0])
                                time.sleep(1)
                            else:
                                # Try pressing ESC key
                                from selenium.webdriver.common.keys import Keys
                                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                                time.sleep(1)
                        
                        elif len(driver.window_handles) > 1:
                            # New tab/window opened
                            driver.switch_to.window(driver.window_handles[-1])
                            
                            # Extract details from new page
                            detail_soup = BeautifulSoup(driver.page_source, 'html.parser')
                            detail_text = detail_soup.get_text()
                            
                            profile_data["nature_of_violation"] = extract_violation_info(detail_text)
                            profile_data["actions_taken"] = extract_actions_info(detail_text)
                            profile_data["additional_metadata"]["detail_page_content"] = detail_text[:1000]
                            
                            print(f"  Extracted detail page data for: {profile_data['name']}")
                            
                            # Close detail window and return to main
                            driver.close()
                            driver.switch_to.window(main_window)
                            time.sleep(1)
                        else:
                            print(f"  No modal or new window detected for: {profile_data['name']}")
                    else:
                        print(f"  No clickable View More element found for: {profile_data['name']}")
                        
            except Exception as detail_error:
                print(f"⚠️ Could not extract additional details for {profile_data.get('name', 'Unknown')}: {detail_error}")
            
            # Set default violation info based on I-SCAN context
            if not profile_data["nature_of_violation"]:
                profile_data["nature_of_violation"] = "Unauthorized investment services"
            if not profile_data["actions_taken"]:
                profile_data["actions_taken"] = "Regulatory alert issued"
            
            return profile_data
            
    except Exception as e:
        print(f"Error extracting data from row: {e}")
    return None

def extract_violation_info(text):
    """Extract nature of violation from text"""
    keywords = [
        "unauthorized", "unlicensed", "unregistered", "illegal", "fraudulent",
        "misleading", "deceptive", "false", "manipulation", "violation",
        "breach", "contravention", "non-compliance"
    ]
    
    text_lower = text.lower()
    violations = []
    
    for keyword in keywords:
        if keyword in text_lower:
            violations.append(keyword)
    
    return ", ".join(violations) if violations else "Regulatory violation"

def extract_actions_info(text):
    """Extract actions taken from text"""
    actions_keywords = [
        "warning", "alert", "cease and desist", "suspended", "revoked",
        "fined", "penalty", "prohibited", "banned", "restricted",
        "investigation", "enforcement action"
    ]
    
    text_lower = text.lower()
    actions = []
    
    for keyword in actions_keywords:
        if keyword in text_lower:
            actions.append(keyword)
    
    return ", ".join(actions) if actions else "Regulatory alert issued"

def scrape_profiles():
    # Setup Chrome options
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    
    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-notifications")
    
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )
    
    try:
        print(f"🔍 Loading I-SCAN page: {URL}")
        driver.get(URL)
        
        # Wait for page to fully load
        wait = WebDriverWait(driver, 30)
        table = wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
        print(f"📄 Page title: {driver.title}")
        
        # Additional wait for dynamic content
        time.sleep(5)
        
        # Find all data rows in the table
        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        if len(rows) == 0:
            # Try alternative selector if tbody not found
            all_rows = driver.find_elements(By.CSS_SELECTOR, "table tr")
            # Skip header row if present
            if len(all_rows) > 1:
                rows = all_rows[1:]
            print(f"Using alternative selector, found: {len(rows)} rows")
        
        print(f"Total profiles found: {len(rows)}")
        
        if len(rows) == 0:
            print(" No data rows found. The page structure might have changed.")
            return
        
        last_index = load_checkpoint()
        main_window = driver.current_window_handle
        successful_extractions = 0
        
        # Process each row without re-finding DOM elements to avoid corruption
        for i in range(last_index, len(rows)):
            try:
                print(f" Processing row {i+1}/{len(rows)}")
                
                # Use original rows list to avoid DOM re-query issues
                if i >= len(rows):
                    print(f" Row {i+1} index out of bounds, stopping...")
                    break
                    
                row = rows[i]
                
                # Scroll to row for visibility
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", row)
                time.sleep(1)
                
                # Extract cells data
                cells = row.find_elements(By.TAG_NAME, "td")
                print(f"   Found {len(cells)} cells in row {i+1}")
                
                if len(cells) >= 4:  # Minimum required cells (name, website, authority, date)
                    # Extract basic data
                    profile_data = {
                        "name": cells[0].text.strip() if len(cells) > 0 else "",
                        "website": cells[2].text.strip() if len(cells) > 2 else "",
                        "authority": cells[3].text.strip() if len(cells) > 3 else "",
                        "date": cells[4].text.strip() if len(cells) > 4 else "",
                        "status": "Alert/Warning",
                        "nature_of_violation": "Unauthorized investment services",
                        "actions_taken": "Regulatory alert issued",
                        "additional_metadata": {
                            "scraped_at": time.time(),
                            "region": "",
                            "source": "IOSCO I-SCAN",
                            "scraped_index": i
                        }
                    }
                    
                    # Skip empty entries
                    if not profile_data["name"] or profile_data["name"] == "":
                        print(f" Row {i+1} has empty name, skipping...")
                        continue
                    
                    # Extract region from authority
                    if " - " in profile_data["authority"]:
                        parts = profile_data["authority"].split(" - ")
                        if len(parts) >= 2:
                            profile_data["additional_metadata"]["region"] = parts[0].strip()
                            profile_data["authority"] = parts[1].strip()
                    
                    # Skip "View More" interaction to avoid DOM corruption
                    # Just use basic data for reliability
                    
                    # Save to database
                    result = profiles_collection.insert_one(profile_data)
                    if result.inserted_id:
                        successful_extractions += 1
                        print(f"Saved profile {i+1}/{len(rows)}: {profile_data['name']}")
                        print(f"   Authority: {profile_data['authority']} | Region: {profile_data['additional_metadata']['region']}")
                        
                        # Update checkpoint after successful save
                        save_checkpoint(i + 1)
                    else:
                        print(f" Failed to save profile {i+1}")
                        
                    # Small delay between profiles to be respectful
                    time.sleep(0.5)
                    
                else:
                    print(f" Row {i+1} has only {len(cells)} cells, skipping...")
                    # Print the cell contents for debugging
                    for j, cell in enumerate(cells):
                        print(f"     Cell {j}: '{cell.text.strip()}'")
                    
            except Exception as e:
                print(f" Error processing row {i+1}: {e}")
                import traceback
                traceback.print_exc()
                # Continue with next row instead of breaking
                continue
        
        print(f" Scraping completed! Successfully extracted {successful_extractions} profiles.")
        
    except Exception as e:
        print(f" Fatal error during scraping: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()
        print(" Browser closed")
