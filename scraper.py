import time
from playwright.sync_api import sync_playwright
import random

# The specific URL you wanted to scrape
URL = "https://ie.indeed.com/jobs?q=web%20developer&l=Ireland&from=searchOnDesktopSerp"

def run_scraper(page_limit=1, immediatelyProcceed=False):
    fileTimeStamp = time.strftime("%Y%m%d_%H%M%S")
    with sync_playwright() as p:
        # 1. Launch with specific arguments to hide automation
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled", # <--- The most important line
                "--start-maximized"
            ]
        )
        
        # 2. Create a context with a real User Agent (looks like a standard Windows PC)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        
        # 3. Inject a script to ensure 'navigator.webdriver' returns undefined
        page = context.new_page()
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """)

        print(f"--- Navigating to {URL} ---")
        page.goto(URL)
        
        # ... The rest of your logic (clicking cards) goes here ...
        
        # Example of slightly safer clicking:
        job_cards = page.locator('.job_seen_beacon').all()
        print(f"--- Found {len(job_cards)} jobs ---")
        fileName = "data/raw/JobDesc" + fileTimeStamp + ".txt"

       # Open file once, append mode
        with open(fileName, "w", encoding="utf-8") as f:
            
            # --- 2. LOOP THROUGH 5 PAGES ---
            for page_num in range(1, page_limit + 1): 
                print(f"\n--- Processing Page {page_num} of {page_limit} ---")
                
                # Check for and close the annoying "Save this search" popup
                close_popup(page)
                
                scrape_current_page(page, f)
                
                # Don't try to click next on the last loop
                if page_num < page_limit:
                    if not go_to_next_page(page):
                        print("Could not find 'Next' button. Stopping early.")
                        break

        print(f"\n--- Scraping Complete. Data saved to {fileName} ---")
        browser.close()
        
def scrape_current_page(page, file_handle):
    # Get all job cards on the current page
    # Note: We re-query the DOM every page load to avoid stale elements
    page.wait_for_selector('.job_seen_beacon', timeout=10000)
    job_cards = page.locator('.job_seen_beacon').all()
    
    print(f"Found {len(job_cards)} jobs on this page.")

    for i, card in enumerate(job_cards):
        try:
            # Random Human Pause
            time.sleep(random.uniform(0.8, 1.5))
            
            card.scroll_into_view_if_needed()
            card.click()
            
            # 1. Wait for the main description pane to appear
            #    We wait for the title specifically to ensure the new job has loaded
            page.locator('h2[data-testid="jobsearch-JobInfoHeader-title"]').wait_for(state="visible", timeout=5000)
            
            # 2. Extract Metadata (Title, Company, Location)
            #    We use 'first' because sometimes shadow DOMs duplicate elements, 
            #    but usually there is only one visible in the right pane.
            title = page.locator('h2[data-testid="jobsearch-JobInfoHeader-title"]').first.inner_text()
            
            # Company and Location sometimes don't exist (e.g. anonymous post), so we try/except them safely
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
            
            # 4. Write to file
            #    We format it so Gemini sees the metadata at the very top of the block
            file_handle.write("Full job description\n")
            file_handle.write(f"JOB TITLE: {title}\n")
            file_handle.write(f"COMPANY: {company}\n")
            file_handle.write(f"LOCATION: {location}\n")
            file_handle.write("-" * 20 + "\n") # Visual separator
            file_handle.write(description)
            file_handle.write("\n\n" + ("="*50) + "\n\n")
            
            print(f"Saved: {title[:30]}...")
            
            
            
        except Exception as e:
            # Just skip the failed card and keep going
            # print(f"Skipped a card: {e}") 
            pass

def go_to_next_page(page):
    try:
        # Locator for the 'Next' arrow/button at the bottom
        # This selector is usually an anchor tag with data-testid attribute
        next_button = page.locator('a[data-testid="pagination-page-next"]')
        
        if next_button.count() > 0:
            next_button.scroll_into_view_if_needed()
            next_button.click()
            
            # Important: Wait for the page to actually change
            # We wait for the URL to change or a specific loading spinner to vanish
            time.sleep(3) 
            return True
        else:
            return False
    except Exception as e:
        print(f"Pagination error: {e}")
        return False

def close_popup(page):
    # Indeed often shows a popup asking for email. 
    # This tries to find the 'X' button.
    try:
        # Common selector for the close button on Indeed modals
        close_btn = page.locator('button[aria-label="close"]')
        if close_btn.is_visible():
            close_btn.click()
            print("--- Closed a Popup ---")
            time.sleep(1)
    except:
        pass

if __name__ == "__main__":
    run_scraper()