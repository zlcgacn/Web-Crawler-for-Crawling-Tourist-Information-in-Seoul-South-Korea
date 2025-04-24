import requests
from bs4 import BeautifulSoup, Tag # Import Tag for type checking
import re # Import regex module
import time # Import time module for delays
import json # Import json module for saving data
from urllib.parse import urljoin # To construct absolute URLs

# --- Function to scrape details from an attraction page ---
def scrape_details(detail_url, session):
    """Fetches and parses an attraction detail page to extract description and transport info."""
    print(f"  Scraping details from: {detail_url}")
    description = "Description not found"
    transport = "Transportation info not found"
    try:
        # Use the session object for the request
        response = session.get(detail_url, timeout=15)
        response.raise_for_status()
        detail_soup = BeautifulSoup(response.text, 'html.parser')

        # --- Extract Description ---
        # ** Placeholder - Replace with actual selector identified by inspecting the detail page HTML **
        # Example guesses (likely need adjustment):
        # desc_area = detail_soup.find('div', class_='article-content')
        # desc_area = detail_soup.find('section', id='description-section')
        desc_area = detail_soup.find('div', class_=re.compile(r'cont-in-box|content|desc|summary|article', re.I))
        if desc_area:
            # Remove potential script/style tags within the description area
            for unwanted_tag in desc_area.find_all(['script', 'style']):
                unwanted_tag.extract()
            description = desc_area.get_text(separator='\n', strip=True)
        else:
            # Fallback: find the main content area (often <main> or div#content)
            main_content = detail_soup.find('main') or detail_soup.find('div', id='content')
            if main_content:
                description = main_content.find('p').get_text(strip=True) if main_content.find('p') else "Main content found, but no <p> tag."

        # --- Extract Transportation ---
        # ** Placeholder - Replace with actual selector identified by inspecting the detail page HTML **
        # Example guesses:
        # transport_section = detail_soup.find('section', id='transport-info')
        # transport_heading = detail_soup.find(['h2', 'h3'], string=re.compile(r'Transportation|Access', re.I))
        transport_heading = detail_soup.find(['h2', 'h3', 'h4'], string=re.compile(r'Transportation|Getting Here|Directions|Access', re.I))
        if transport_heading:
            # Try to find the content block immediately following the heading
            # This is highly dependent on structure (e.g., next sibling, parent's next sibling, specific div)
            next_element = transport_heading.find_next_sibling()
            if next_element and isinstance(next_element, Tag):
                # Check if the next sibling seems like a content block (e.g., div, p, ul)
                if next_element.name in ['div', 'p', 'ul', 'section']:
                    transport = next_element.get_text(separator='\n', strip=True)
                else: # Maybe the content is further down or nested differently
                    transport = f"Found heading '{transport_heading.string.strip()}', but next sibling structure unclear."
            else:
                 # If no direct sibling, try finding the parent's next content sibling
                 parent_next = transport_heading.find_parent().find_next_sibling()
                 if parent_next and isinstance(parent_next, Tag):
                      transport = parent_next.get_text(separator='\n', strip=True)
                 else:
                      transport = f"Found heading '{transport_heading.string.strip()}', but couldn't find subsequent content."
        else:
            # Fallback: Search for keywords in the whole page (less reliable)
            all_text = detail_soup.get_text(" ", strip=True)
            if re.search(r'(Subway|Bus|Station|Line [0-9])', all_text, re.I):
                 transport = "Found transport keywords, but couldn't isolate section."

    except requests.exceptions.RequestException as e:
        print(f"    Error fetching detail URL {detail_url}: {e}")
        description = f"Error fetching page: {e}"
        transport = f"Error fetching page: {e}"
    except Exception as e:
        print(f"    Error parsing detail URL {detail_url}: {e}")
        description = f"Error parsing page: {e}"
        transport = f"Error parsing page: {e}"

    # Clean up potentially long descriptions for printing
    if len(description) > 300:
        description = description[:300].strip() + "... (truncated)"

    return description.strip(), transport.strip()

# --- Main Script Logic ---
BASE_URL = "https://english.visitseoul.net"
START_URL = urljoin(BASE_URL, "/attractions") # Start at the attractions page
all_attraction_data = []
processed_urls = set() # Keep track of visited list pages to avoid loops
# MAX_PAGES = 10 # Safety limit to prevent infinite loops - REMOVED as requested

# Use a session object for connection pooling and potential cookie handling
session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (compatible; MySeoulScraper/1.0; +http://mywebsite.com)'}) # More specific user agent

current_url = START_URL
page_count = 0

print(f"Starting scraper at: {START_URL}")

while current_url: # Removed 'and page_count < MAX_PAGES'
    if current_url in processed_urls:
        print(f"Already processed {current_url}, stopping pagination loop.")
        break

    print(f"\nFetching list page {page_count + 1}: {current_url}")
    processed_urls.add(current_url)
    page_count += 1

    try:
        response = session.get(current_url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        print(f"Successfully fetched and parsed: {current_url}")

        # --- Find Attraction List Items ---
        # ** Placeholder - Replace with actual selector for the list container **
        # Example Guesses:
        # list_container = soup.find('div', class_='attraction-list-area')
        # list_container = soup.find('ul', id='item-results')
        list_container = soup.find('div', {'class': re.compile(r'list-container|items-wrap|attraction-items', re.I)}) or soup.find('ul', {'class': re.compile(r'card-list|item-list', re.I)})

        if not list_container:
             print(f"  Warning: Could not find specific list container on {current_url}. Searching all 'li' or 'div.card'...")
             # Fallback: Look for list items more broadly (less reliable)
             # ** Placeholder - Replace with actual selector for individual items **
             attraction_items = soup.find_all('li', {'class': re.compile(r'item|card', re.I)}) or soup.find_all('div', {'class': re.compile(r'card|list-item', re.I)})
        else:
             print(f"  Found list container: <{list_container.name} class='{list_container.get('class', '')}'>")
             # ** Placeholder - Replace with actual selector for items *within* the container **
             attraction_items = list_container.find_all('li', recursive=False) or list_container.find_all('div', recursive=False) # Find direct children li or div

        if not attraction_items:
             print(f"  Could not find any attraction items on this page.")
             # Attempt to find next page even if no items found on current page
        else:
            print(f"  Found {len(attraction_items)} potential attraction items on this page.")
            item_count_on_page = 0
            for item in attraction_items:
                item_count_on_page += 1
                print(f"\n--- Processing Item {item_count_on_page} on Page {page_count} --- ")

                # --- Extract Name and Link from List Item ---
                name = "Name not found"
                link = None
                # ** Placeholder - Replace with actual name selector within the item **
                name_tag = item.find('h3') or item.find('strong', class_=re.compile(r'title|name', re.I))
                if not name_tag:
                    name_tag = item.find('a') # Fallback

                if name_tag:
                    name = name_tag.get_text(strip=True) # Simpler extraction for now

                # ** Placeholder - Replace with actual link selector within the item **
                link_tag = item.find('a', href=True)
                if link_tag:
                    link_href = link_tag['href']
                    link = urljoin(BASE_URL, link_href) # Construct absolute URL

                print(f"Name: {name}")
                print(f"Link: {link}")

                # --- Scrape Details if Link is Valid ---
                if link and link.startswith(BASE_URL): # Only scrape details from the same site
                    description, transport = scrape_details(link, session)
                    print(f"Description: {description}")
                    print(f"Transportation: {transport}")

                    # Store data
                    all_attraction_data.append({
                        'page': page_count,
                        'name': name,
                        'link': link,
                        'description': description,
                        'transport': transport
                    })
                elif link:
                    print(f"  Skipping detail scraping (external link or invalid): {link}")
                else:
                    print("  Skipping detail scraping (no link found).")

                # --- Polite Delay ---
                print("  Pausing for 1.5 seconds...")
                time.sleep(1.5) # Slightly longer delay

        # --- Find Next Page Link --- 
        next_link_tag = None
        # ** Placeholder - Replace with actual selector for the 'Next' pagination link **
        # Try common patterns for pagination links
        pagination_area = soup.find('div', class_=re.compile(r'pagination|paging', re.I))
        if pagination_area:
             next_link_tag = pagination_area.find('a', string=re.compile(r'Next', re.I))
             if not next_link_tag:
                  next_link_tag = pagination_area.find('a', {'class': re.compile(r'next|forward', re.I)})
        # Fallback if no specific pagination area found
        if not next_link_tag:
             next_link_tag = soup.find('a', string=re.compile(r'Next', re.I), class_=re.compile(r'btn|page', re.I))

        if next_link_tag and next_link_tag.has_attr('href'):
            next_href = next_link_tag['href']
            current_url = urljoin(BASE_URL, next_href) # Make absolute URL
            print(f"  Found next page link: {current_url}")
        else:
            print("  No 'Next' page link found or link invalid. Stopping pagination.")
            current_url = None # Stop the loop

    except requests.exceptions.RequestException as e:
        print(f"Error fetching list page {current_url}: {e}")
        print("Stopping scraper due to network error.")
        break # Exit pagination loop on error
    except Exception as e:
        print(f"An unexpected error occurred processing page {current_url}: {e}")
        # Decide whether to continue or stop on other errors
        print("Attempting to find next page link anyway...")
        # Try to find next page even after error on current page (may fail)
        try:
            next_link_tag = soup.find('a', string=re.compile(r'Next', re.I)) # Simplified search after error
            if next_link_tag and next_link_tag.has_attr('href'):
                next_href = next_link_tag['href']
                current_url = urljoin(BASE_URL, next_href)
                print(f"  Found next page link after error: {current_url}")
            else:
                 current_url = None
        except:
             print("Could not find next page link after error.")
             current_url = None

# --- End of Loop --- 
print(f"\n--- Finished scraping. Processed {page_count} pages and collected {len(all_attraction_data)} items. ---")

# --- Save Data to JSON --- 
if all_attraction_data:
    try:
        filename = 'seoul_attractions.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(all_attraction_data, f, ensure_ascii=False, indent=4)
        print(f"Data saved successfully to {filename}")
    except Exception as e:
        print(f"Error saving data to JSON file: {e}")
else:
    print("No data collected to save.")

print("Scraper finished.") 