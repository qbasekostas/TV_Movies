import requests
from bs4 import BeautifulSoup
import time

LIST_URL = "https://www.ertflix.gr/list?pageCodename=movies§ionCodename=oles-oi-tainies-1&tileCount=300"
DEVICE_KEY = "12b9a6425e59ec1fcee9acb0e7fba4f3"
API_URL = "https://api.app.ertflix.gr/v1/Player/AcquireContent"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def main():
    try:
        print("Λήψη της λίστας ταινιών από το ERTFLIX...")
        response = requests.get(LIST_URL, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
    except requests.exceptions.RequestException as e:
        print(f"Σφάλμα: Αποτυχία λήψης της λίστας ταινιών. {e}")
        return

    movies = []
    # Βρίσκουμε τους συνδέσμους χρησιμοποιώντας ένα χαρακτηριστικό που είναι πιο σταθερό
    movie_links = soup.select('a[href*="/vod/vod."]')
    
    if not movie_links:
        print("Δεν βρέθηκαν σύνδεσμοι ταινιών. Η δομή της σελίδας μπορεί να έχει αλλάξει.")
        return
        
    print(f"Βρέθηκαν {len(movie_links)} πιθανές ταινίες. Έναρξη επεξεργασίας...")

    for link in movie_links:
        img = link.find("img", alt=True)
        if img and img["alt"].strip():
            title = img["alt"].strip()
            href = link["href"]
            
            codename = None
            if "vod." in href:
                try:
                    # Εξάγουμε το codename από το href
                    codename_parts = href.split("vod.")[1].split("-", 1)
                    if len(codename_parts) > 1:
                        codename = codename_parts[1]
                except IndexError:
                    pass
            
            if not codename:
                print(f"INFO: Παράλειψη συνδέσμου χωρίς έγκυρο codename: {href}")
                continue

            t = int(time.time() * 1000)
            params = {
                "platformCodename": "www",
                "deviceKey": DEVICE_KEY,
                "codename": codename,
                "t": t
            }
            try:
                api_resp = requests.get(API_URL, params=params, headers=headers, timeout=10)
                api_resp.raise_for_status()
                data = api_resp.json()
                
                stream_url = None
                if data.get("MediaFiles"):
                    for media_file in data["MediaFiles"]:
                        if media_file.get("Formats"):
                            for file_format in media_file["Formats"]:
                                # Αναζήτηση για URL που τελειώνει σε .m3u8
                                if file_format.get("Url", "").endswith(".m3u8"):
                                    stream_url = file_format["Url"]
                                    break
                        if stream_url:
                            break

                if stream_url:
                    movies.append((title, stream_url))
                    print(f"OK: {title}")
                else:
                    print(f"NO STREAM: {title}")
            except requests.exceptions.HTTPError as http_err:
                if http_err.response.status_code == 404:
                    print(f"INFO: Το περιεχόμενο για '{title}' δεν είναι πλέον διαθέσιμο (404).")
                else:
                    print(f"HTTP ERROR for {title}: {http_err}")
            except requests.exceptions.RequestException as req_err:
                print(f"REQUEST ERROR for {title}: {req_err}")
            except Exception as e:
                print(f"GENERIC ERROR for {title}: {e}")
            
            # Μικρή καθυστέρηση για να μην υπερφορτωθεί ο server
            time.sleep(0.3)

    if not movies:
        print("\nΔεν βρέθηκαν ταινίες με έγκυρο stream για δημιουργία λίστας.")
        return

    try:
        with open("ertflix_playlist.m3u8", "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for title, url in movies:
                f.write(f'#EXTINF:-1,{title}\n{url}\n')
        print(f"\nΤο αρχείο ertflix_playlist.m3u8 δημιουργήθηκε με επιτυχία με {len(movies)} ταινίες!")
    except IOError as e:
        print(f"\nΣφάλμα: Αποτυχία εγγραφής στο αρχείο: {e}")

if __name__ == "__main__":
    main()
