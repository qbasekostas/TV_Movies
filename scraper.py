import time
import json
import os
import requests
import html
from selenium import webdriver
# --- ΑΛΛΑΓΕΣ ΓΙΑ CHROME ---
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options as ChromeOptions
# -------------------------
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- Ρυθμίσεις που ταιριάζουν με το .yml σου ---
LIST_URL = "https://www.ertflix.gr/list?pageCodename=movies&backUrl=/show/movies§ionCodename=oles-oi-tainies-1"
OUTPUT_M3U_FILE = "ertflix_playlist.m3u8" 
# ---------------------------------------------
PLAYER_API_URL = "https://api.app.ertflix.gr/v1/Player/AcquireContent"
DEVICE_KEY = "12b9a6425e59ec1fcee9acb0e7fba4f3"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://www.ertflix.gr/"
}

def get_movie_list_with_selenium():
    print(">>> ΜΕΡΟΣ 1: Selenium/Chrome - Έναρξη για τη συλλογή της λίστας...")
    
    options = ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    # --- Η ΣΩΣΤΗ ΡΥΘΜΙΣΗ ΓΛΩΣΣΑΣ ΓΙΑ CHROME ---
    options.add_argument("--lang=el")
    # ---------------------------------------------

    driver = None
    try:
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        driver.get(LIST_URL)
        time.sleep(5) 

        try:
            cookie_button_selector = 'button[data-test="button-cookies-accept"]'
            accept_button = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.CSS_SELECTOR, cookie_button_selector)))
            driver.execute_script("arguments[0].click();", accept_button)
            time.sleep(2)
        except TimeoutException:
            pass
        
        scroll_attempts = 0
        while scroll_attempts < 35:
            last_height = driver.execute_script("return document.body.scrollHeight")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(4)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height and last_height > 2000: break
            scroll_attempts += 1
        
        movie_selector = 'a[class^="VideoTile__auditionLink___"]'
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, movie_selector)))
        movie_elements = driver.find_elements(By.CSS_SELECTOR, movie_selector)
        
        movies_info = []
        for element in movie_elements:
            try:
                href = element.get_attribute('href')
                id_part = href.split('/')[-1]
                parts = id_part.split('-', 1)
                codename = parts[1] if len(parts) > 1 else id_part
                
                img_element = element.find_element(By.TAG_NAME, 'img')
                title = img_element.get_attribute('alt')
                poster_url = img_element.get_attribute('src')
                
                if codename and title:
                    movies_info.append({'codename': codename, 'title': title, 'poster_url': poster_url})
            except (NoSuchElementException, IndexError):
                continue
        
        print(f">>> Η συλλογή ολοκληρώθηκε! Βρέθηκαν {len(movies_info)} ταινίες.")
        return movies_info

    finally:
        if driver:
            driver.quit()

def main():
    movies_info = get_movie_list_with_selenium()

    if not movies_info:
        return

    print("\n>>> ΜΕΡΟΣ 2: Requests - Ταχύτατη λήψη των stream links...")
    
    with open(OUTPUT_M3U_FILE, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        
        for index, movie in enumerate(movies_info):
            codename, title, poster_url = movie['codename'], movie['title'], movie['poster_url']
            title = html.unescape(title)
            print(f"    [{index + 1}/{len(movies_info)}] Επεξεργασία: {title}")
            
            try:
                player_params = {
                    "platformCodename": "www", "deviceKey": DEVICE_KEY, 
                    "codename": codename, "t": int(time.time() * 1000)
                }
                player_resp = requests.get(PLAYER_API_URL, params=player_params, headers=HEADERS, timeout=15)
                
                if player_resp.status_code == 404: continue
                player_resp.raise_for_status()
                player_data = player_resp.json()
                
                final_url = None
                if player_data.get("MediaFiles"):
                    for media_file in player_data["MediaFiles"]:
                        if media_file.get("Formats"):
                            for file_format in media_file["Formats"]:
                                url = file_format.get("Url", "")
                                if url.endswith(".m3u8") and "/output1/" not in url:
                                    final_url = url
                                    break
                                elif url.endswith(".mpd") and not final_url:
                                    final_url = url
                        if final_url and ".m3u8" in final_url:
                            break
                
                if final_url and final_url.endswith(".mpd"):
                    final_url = final_url.replace("/index.mpd", "/playlist.m3u8")

                if final_url:
                    logo_tag = f'tvg-logo="{poster_url}"' if poster_url else ""
                    info_line = f'#EXTINF:-1 {logo_tag},{title}\n'
                    user_agent_line = f'#EXTVLCOPT:user-agent={HEADERS["User-Agent"]}\n'
                    
                    f.write(info_line)
                    f.write(user_agent_line)
                    f.write(f'{final_url}\n')

            except Exception:
                pass

    print(f"\n>>> ΟΛΟΚΛΗΡΩΘΗΚΕ! Το αρχείο '{OUTPUT_M3U_FILE}' δημιουργήθηκε.")

if __name__ == "__main__":
    main()
