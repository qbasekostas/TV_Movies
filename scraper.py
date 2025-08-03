import time
import requests
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# --- Σταθερές ---
URL = "https://www.ertflix.gr/list/movies/oles-oi-tainies-1"
PLAYER_API_URL = "https://api.app.ertflix.gr/v1/Player/AcquireContent"
DEVICE_KEY = "12b9a6425e59ec1fcee9acb0e7fba4f3"
OUTPUT_FILE = "ertflix_playlist.m3u8"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://www.ertflix.gr/"
}

def get_all_movies_with_selenium():
    """
    Χρησιμοποιεί το Selenium για να ανοίξει τη σελίδα, να περιμένει να φορτώσει το περιεχόμενο,
    να κάνει scroll μέχρι το τέλος και να επιστρέψει τον πλήρη HTML κώδικα.
    """
    print("--- Φάση 1: Εκκίνηση browser και scroll για φόρτωση όλων των ταινιών ---")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=" + HEADERS["User-Agent"])

    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(URL)
        
        # --- Η ΚΡΙΣΙΜΗ ΔΙΟΡΘΩΣΗ ---
        # Περιμένουμε ΥΠΟΜΟΝΕΤΙΚΑ μέχρι 20 δευτερόλεπτα, μέχρι να εμφανιστεί
        # τουλάχιστον ΕΝΑΣ σύνδεσμος ταινίας. Μόλις εμφανιστεί, προχωράμε.
        print("Αναμονή για φόρτωση των πρώτων ταινιών...")
        wait = WebDriverWait(driver, 20)
        # Αυτός ο selector ψάχνει για <a href="..."> που περιέχει "/vod/vod."
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/vod/vod.']")))
        print("Οι πρώτες ταινίες φορτώθηκαν. Έναρξη scroll.")
        # --- ΤΕΛΟΣ ΔΙΟΡΘΩΣΗΣ ---

        last_height = driver.execute_script("return document.body.scrollHeight")
        
        while True:
            print("Κάνοντας scroll προς τα κάτω...")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3) 
            
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                print("Φτάσαμε στο τέλος της σελίδας. Ολοκληρώθηκε το scroll.")
                break
            last_height = new_height

        html_content = driver.page_source
        driver.quit()
        return html_content

    except Exception as e:
        print(f"Σφάλμα κατά τη διάρκεια της διαδικασίας του Selenium: {e}")
        if 'driver' in locals():
            driver.quit()
        return None

def main():
    final_playlist = []

    full_html = get_all_movies_with_selenium()
    
    if not full_html:
        print("\nΑποτυχία λήψης του HTML. Τερματισμός.")
        return

    print("\n--- Φάση 2: Επεξεργασία HTML για εξαγωγή πληροφοριών ---")
    soup = BeautifulSoup(full_html, "html.parser")
    
    movie_links = soup.select('a[href*="/vod/vod."]')
    total_movies = len(movie_links)
    print(f"Βρέθηκαν {total_movies} ταινίες στη σελίδα.")

    if total_movies == 0:
        print("Δεν βρέθηκαν σύνδεσμοι ταινιών. Πιθανόν η δομή της σελίδας άλλαξε.")
        return

    print(f"\n--- Φάση 3: Έναρξη επεξεργασίας {total_movies} ταινιών για λήψη stream URL ---")
    for index, link in enumerate(movie_links):
        try:
            img_tag = link.find("img")
            if not img_tag: continue

            title = img_tag.get("alt", "Unknown Title").strip()
            poster_url = img_tag.get("src", "")
            href = link.get("href", "")
            
            if "vod." in href and "-" in href:
                codename_parts = href.split("vod.")[1].split("-", 1)
                if len(codename_parts) > 1:
                    codename = codename_parts[1]
                else: continue
            else:
                continue
            
            print(f"Επεξεργασία {index + 1}/{total_movies}: {title}")

            player_params = {"platformCodename": "www", "deviceKey": DEVICE_KEY, "codename": codename, "t": int(time.time() * 1000)}
            player_resp = requests.get(PLAYER_API_URL, params=player_params, headers=HEADERS, timeout=15)
            player_resp.raise_for_status()
            player_data = player_resp.json()
            
            stream_url = None
            media_files = player_data.get("mediaFiles") or player_data.get("MediaFiles")
            if media_files:
                for media_file in media_files:
                    formats = media_file.get("formats") or media_file.get("Formats")
                    if formats:
                        for file_format in formats:
                            url = file_format.get("url") or file_format.get("Url")
                            if url and url.endswith(".m3u8"):
                                stream_url = url
                                break
                    if stream_url:
                        break

            if stream_url:
                final_playlist.append({'title': title, 'stream_url': stream_url, 'poster_url': poster_url})
                print(f"  -> Επιτυχία!")
            else:
                print(f"  -> Δεν βρέθηκε stream.")
        
        except Exception as e:
            print(f"  -> Σφάλμα κατά την επεξεργασία του συνδέσμου {link.get('href', '')}: {e}")
        
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
