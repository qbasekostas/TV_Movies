import time
import json
import os
import requests
import html
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- Ρυθμίσεις ---
LIST_URL = "https://www.ertflix.gr/list?pageCodename=movies&backUrl=/show/movies&sectionCodename=oles-oi-tainies-1"
OUTPUT_M3U_FILE = "ertflix_playlist.m3u8"
PLAYER_API_URL = "https://api.app.ertflix.gr/v1/Player/AcquireContent"
DEVICE_KEY = "12b9a6425e59ec1fcee9acb0e7fba4f3"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://www.ertflix.gr/"
}

def main():
    print(">>> ΜΕΡΟΣ 1: Selenium/Chrome - Έναρξη για τη συλλογή της λίστας...")
    
    options = ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=el")

    driver = None
    try:
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        driver.get(LIST_URL)
        print(">>> Αναμονή 10 δευτερολέπτων για να φορτώσει η σελίδα...")
        time.sleep(10) # Περισσότερος χρόνος για το αργό περιβάλλον του GitHub

        try:
            # Προσπάθεια να πατήσουμε ΟΠΟΙΟΔΗΠΟΤΕ κουμπί αποδοχής
            accept_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'accept') or contains(text(), 'Accept') or contains(text(), 'Αποδοχή')]"))
            )
            print(">>> Βρέθηκε κουμπί αποδοχής. Κλικ...")
            driver.execute_script("arguments[0].click();", accept_button)
            time.sleep(2)
        except TimeoutException:
            print("(!) Δεν βρέθηκε κάποιο κουμπί για cookies/GDPR.")
            pass
        
        print(">>> Ξεκινά η φόρτωση όλων των ταινιών με scroll down...")
        scroll_attempts = 0
        while scroll_attempts < 40: # Περισσότερες προσπάθειες
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(5) # Περισσότερος χρόνος ανάμεσα στα scroll
            scroll_attempts += 1
        
        print(">>> Συλλογή ταινιών...")
        movie_selector = 'a[class^="VideoTile__auditionLink___"]'
        
        # Περιμένουμε για τις ταινίες. Αν αποτύχει, θα σώσει τα αρχεία διάγνωσης.
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
        # (Το υπόλοιπο script παραμένει ίδιο)

    except Exception as e:
        print(f"\n!!! ΠΑΡΟΥΣΙΑΣΤΗΚΕ ΣΦΑΛΜΑ: {e}")
        print(">>> Αποθήκευση αρχείων διάγνωσης...")
        if driver:
            try:
                driver.save_screenshot("debug_screenshot.png")
                with open("debug_page_source.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                print(">>> Τα αρχεία debug_screenshot.png και debug_page_source.html αποθηκεύτηκαν.")
            except Exception as save_e:
                print(f"!!! Αποτυχία αποθήκευσης αρχείων διάγνωσης: {save_e}")
        # Τερματίζουμε το script με κωδικό σφάλματος για να ενεργοποιηθεί το 'if: failure()'
        exit(1)

    finally:
        if driver:
            driver.quit()

    # (Ο κώδικας για το Μέρος 2 παραμένει ίδιος)
    print("\n>>> ΜΕΡΟΣ 2: Requests - Ταχύτατη λήψη των stream links...")
    # ... (ο υπόλοιπος κώδικας)

if __name__ == "__main__":
    main()
