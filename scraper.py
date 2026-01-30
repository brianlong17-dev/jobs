import csv
import json
import time
import os
import random
from playwright.sync_api import sync_playwright
from config import QUEUE_FILE, DATABASE_FILE

class IndeedScraper:
    def __init__(self, url=None, page_limit=1):
        self.url = url or "https://ie.indeed.com/jobs?q=web%20developer&l=Ireland"
        self.page_limit = page_limit
        self.processed_ids = set()
        
        # Generate a timestamped filename for this run
        self.output_file = QUEUE_FILE
        self.databaseFile = DATABASE_FILE
        # Ensure the directory for the queue file exists
        queue_dir = os.path.dirname(self.output_file)
        if queue_dir:
            os.makedirs(queue_dir, exist_ok=True)

    def load_processed_ids(self):
        if not os.path.exists(self.output_file):
            return #needed?
            
        with open(self.output_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if "id" in data:
                        self.processed_ids.add(data["id"])
                except json.JSONDecodeError:
                    pass
        print('skipped IDs from queue file: ',  self.processed_ids)
        databaseIDs = set()
                
        with open(self.databaseFile, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            # Skip the header row
            next(reader, None) 
            for row in reader:
                if row:  # Ensure the row isn't empty
                    # Assuming ID is the first element (index 0)
                   self.processed_ids.add(row[0])
                   databaseIDs.add(row[0])
                   
        print('skipped IDs from database file: ', (databaseIDs))
                
        
        print("Current processed IDS: ", self.processed_ids)
        #queue ids
        #self.current_output_file - read ids.
        #self.database_file - read ids.
        
        #return
        
        #
        return ()

    def get_job_id_from_card(self, card):
        """Extracts the unique data-jk ID from a job card."""
        job_id = card.get_attribute("data-jk")
        if not job_id:
            # Fallback: try finding the anchor tag inside
            job_id = card.locator("a").first.get_attribute("data-jk")
        return job_id

    def close_popup(self, page):
        """Attempts to close the 'Save this search' or email popup."""
        try:
            close_btn = page.locator('button[aria-label="close"]')
            if close_btn.is_visible():
                close_btn.click()
                print("--- Closed a Popup ---")
                time.sleep(1)
        except:
            pass

    def go_to_next_page(self, page):
        """Handles pagination."""
        try:
            next_button = page.locator('a[data-testid="pagination-page-next"]')
            if next_button.count() > 0:
                next_button.scroll_into_view_if_needed()
                next_button.click()
                # Wait for the URL to change or page to settle
                page.wait_for_load_state("domcontentloaded") 
                time.sleep(3) 
                return True
            return False
        except Exception as e:
            print(f"Pagination error: {e}")
            return False

    def scrape_current_page(self, page, file_handle):
        """Iterates through all cards on the current view."""
        # Wait for cards to ensure page is loaded
        page.wait_for_selector('.job_seen_beacon', timeout=10000)
        job_cards = page.locator('.job_seen_beacon').all()
        
        print(f"Found {len(job_cards)} jobs on this page.")

        for card in job_cards:
            try:
                # Random Human Pause
                time.sleep(random.uniform(0.8, 1.5))
                
                card.scroll_into_view_if_needed()
                
                job_id = self.get_job_id_from_card(card)
                
                # --- DEDUPLICATION CHECK ---
                if job_id in self.processed_ids:
                    print(f"Skipping {job_id} (Already Scraped)")
                    continue 
                
                # Click to load details
                card.click()
                
                # 1. Wait for title to ensure details pane loaded
                page.locator('h2[data-testid="jobsearch-JobInfoHeader-title"]').wait_for(state="visible", timeout=5000)
                
                # 2. Extract Metadata
                title_raw = page.locator('h2[data-testid="jobsearch-JobInfoHeader-title"]').first.inner_text()
                title = title_raw.replace("\n", " ").replace("- job post", "").strip()
                try:
                    company = page.locator('[data-testid="inlineHeader-companyName"]').first.inner_text()
                except:
                    company = "Unknown Company"
                    
                try:
                    location = page.locator('[data-testid="inlineHeader-companyLocation"]').first.inner_text()
                except:
                    location = "Unknown Location"

                # 3. Extract Description
                description = page.locator('#jobDescriptionText').inner_text()
                
                # 4. Save Data
                job_data = {
                    "id": job_id,
                    "title": title,
                    "company": company,
                    "location": location,
                    "description": description
                }
                
                # Write JSON line
                file_handle.write(json.dumps(job_data) + "\n")
                
                # Update processed list so we don't scrape it again *in this run*
                self.processed_ids.add(job_id)
                
                print(f"Saved: {title[:30]}...")

            except Exception:
                # Silently skip failed cards to keep the scraper moving
                pass

    def sortByDate(self, page):
        try:
            # 3. Find the "Date" sort link
            # Indeed usually lists "Sort by: relevance - date"
            # We look for a link that strictly contains the text "date"
            # The 'exact=True' helps avoid clicking unrelated dates in job descriptions
            sort_button = page.get_by_role("link", name="date", exact=True)
            
            # If the exact role doesn't work, try a text locator (fallback):
            if sort_button.count() == 0:
                sort_button = page.locator("a", has_text="date")

            print("Clicking 'Sort by Date'...")
            sort_button.click()

            # 4. CRITICAL: Wait for the sort to actually happen
            # The URL usually changes to include "&sort=date"
            page.wait_for_url("*sort=date*")
            
            # 5. Another small pause to let the new list settle
            time.sleep(random.uniform(2, 4))

        except Exception as e:
            print(f"Could not sort by date: {e}")
    # You might want to decide here: do you crash? or just scrape the relevance list?
    def run(self):
        """Main execution method."""
        
        # Load history before starting
        self.load_processed_ids()
        
        with sync_playwright() as p:
            # 1. Launch Browser
            browser = p.chromium.launch(
                headless=False,
                args=["--disable-blink-features=AutomationControlled", "--start-maximized"]
            )
            
            # 2. Context with Real User Agent
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            
            # 3. Stealth Script
            page = context.new_page()
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            print(f"--- Navigating to {self.url} ---")
            page.goto(self.url)
            time.sleep(random.uniform(1, 3))
            self.sortByDate(page)

            # Open the file for writing
            with open(self.output_file, "a", encoding="utf-8") as f:
                
                # Loop through pages
                for page_num in range(1, self.page_limit + 1):
                    print(f"\n--- Processing Page {page_num} of {self.page_limit} ---")
                    
                    self.close_popup(page)
                    self.scrape_current_page(page, f)
                    
                    # Pagination logic
                    if page_num < self.page_limit:
                        if not self.go_to_next_page(page):
                            print("Could not find 'Next' button. Stopping early.")
                            break

            print(f"\n--- Scraping Complete. Data saved to {self.output_file} ---")
            browser.close()

# --- Usage ---
if __name__ == "__main__":
    # You can customize the limit and URL here
    scraper = IndeedScraper(page_limit=10)
    scraper.run()