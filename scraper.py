
**3. `scraper.py`:** Αντικαταστήστε το περιεχόμενό του με την παρακάτω, πιο ανθεκτική έκδοση του κώδικα για Chrome.

```python
import time
import json
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# --- Σταθερές ---
LIST_URL = "https://www.ertflix.gr/list/movies/oles-oi-tainies-1"
PLAYER_API_URL = "https://api.app.ertflix.gr/v1/Player/AcquireContent"
DEVICE_KEY = "12b9a6425e59ec1fcee9acb0e7fba4f3"
OUTPUT_FILE = "ertflix_playlist.m3u8"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://www.ertflix.gr/"
}

def get_all_movies_from_hidden_data():
    """
    Χρησιμοποιεί τη μέθοδο __NEXT_DATA__ με Chrome για να πάρει ΟΛΑ τα δεδομένα
    των ταινιών με μία κίνηση, χωρίς scroll.
    """
    print("--- Φάση 1: Λήψη των κρυμμένων δεδομένων (__NEXT_DATA__) με Chrome ---")
    
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=" + HEADERS["User-Agent"])
    options.add_argument("window-size=1920,1080")

    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        driver.get(LIST_URL)

        print("Αναμονή για το <script> με τα δεδομένα της σελίδας...")
        data_script_element = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "__NEXT_DATA__"))
        )
        
        json_data_str = data_script_element.get_attribute('innerHTML')
        data = json.loads(json_data_str)
        
        items = data.get('props', {}).get('pageProps', {}).get('page', {}).get('items', [])
        all_movies = []
        for section in items:
            if section.get('sectionCode') == 'oles-oi-tainies-1':
                all_movies = section.get('items', [])
                break
        
        if all_movies:
            print(f"  -> Επιτυχία! Βρέθηκαν {len(all_movies)} ταινίες στα αρχικά δεδομένα.")
            return all_movies
        else:
            print("  -> Δεν βρέθηκαν ταινίες στα αρχικά δεδομένα.")
            return None

    except Exception as e:
        print(f"  -> Σφάλμα κατά τη διαδικασία του Selenium.")
        # Προσπαθούμε να πάρουμε ένα screenshot για να δούμε τι πήγε στραβά
        try:
            driver.save_screenshot("debug_screenshot.png")
            print("  -> Αποθηκεύτηκε screenshot: debug_screenshot.png")
        except:
            pass
        print(f"  -> Λεπτομέρειες σφάλματος: {e}")
        return None
    finally:
        if driver:
            driver.quit()

def main():
    final_playlist = []
    
    all_movies_data = get_all_movies_from_hidden_data()
    
    if not all_movies_data:
        print("\nΔεν βρέθηκαν ταινίες για επεξεργασία. Τερματισμός.")
        return

    total_movies = len(all_movies_data)
    print(f"\n--- Φάση 2: Έναρξη επεξεργασίας {total_movies} ταινιών για λήψη stream URL ---")

    for index, movie_data in enumerate(all_movies_data):
        codename = movie_data.get('codename')
        title = movie_data.get('title', codename or "Unknown Title").strip()
        poster_url = movie_data.get('poster', '')

        if not codename:
            continue
            
        print(f"Επεξεργασία {index + 1}/{total_movies}: {title}")

        try:
            player_params = {"platformCodename": "www", "deviceKey": DEVICE_KEY, "codename": codename, "t": int(time.time() * 1000)}
            player_resp = requests.get(PLAYER_API_URL, params=player_params, headers=HEADERS, timeout=15)
            player_resp.raise_for_status()
            player_data = player_resp.json()
            
            stream_url = None
            media_files = player_data.get("MediaFiles")
            if media_files:
                for media_file in media_files:
                    formats = media_file.get("Formats")
                    if formats:
                        for file_format in formats:
                            url = file_format.get("Url")
                            if url and url.endswith(".m3u8"):
                                stream_url = url
                                break
                    if stream_url: break
            
            if stream_url:
                final_playlist.append({'title': title, 'stream_url': stream_url, 'poster_url': poster_url})
                print(f"  -> Επιτυχία!")
            else:
                print(f"  -> Δεν βρέθηκε stream.")
        except Exception as e:
            print(f"  -> Σφάλμα: {e}")
        
        time.sleep(0.05)

    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for movie in final_playlist:
                logo_tag = f'tvg-logo="{movie["poster_url"]}"' if movie["poster_url"] else ""
                info_line = f'#EXTINF:-1 {logo_tag},{movie["title"]}\n'
                url_line = f'{movie["stream_url"]}\n'
                f.write(info_line)
                f.write(url_line)
        print(f"\nΤο αρχείο {OUTPUT_FILE} δημιουργήθηκε με επιτυχία με {len(final_playlist)} ταινίες!")
    except IOError as e:
        print(f"\nΣφάλμα εγγραφής στο αρχείο: {e}")

if __name__ == "__main__":
    main()
