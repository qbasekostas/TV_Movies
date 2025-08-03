import requests
import time
import json

# API endpoint που βρέθηκε στο screenshot σας. Αυτό είναι το σωστό.
LIST_API_URL = "https://api.app.ertflix.gr/v1/section/GetSectionContent"
# Οι παράμετροι που θα στείλουμε μαζί με το URL
LIST_API_PARAMS = {
    'platformCodename': 'www',
    'sectionCodename': 'oles-oi-tainies-1'
}

# Αυτά παραμένουν τα ίδια
DEVICE_KEY = "12b9a6425e59ec1fcee9acb0e7fba4f3"
PLAYER_API_URL = "https://api.app.ertflix.gr/v1/Player/AcquireContent"
OUTPUT_FILE = "ertflix_playlist.m3u8"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def main():
    movies = []
    
    print("Λήψη λίστας ταινιών από το API της ERTFLIX (μέθοδος GetSectionContent)...")
    try:
        # Κάνουμε την κλήση στο σωστό API με τις παραμέτρους του
        list_response = requests.get(LIST_API_URL, params=LIST_API_PARAMS, headers=headers, timeout=20)
        list_response.raise_for_status()
        list_data = list_response.json()
    except requests.exceptions.RequestException as e:
        print(f"Σφάλμα: Αποτυχία λήψης της λίστας ταινιών από το API. {e}")
        return
    except json.JSONDecodeError:
        print("Σφάλμα: Η απάντηση από το API λίστας ταινιών δεν ήταν έγκυρο JSON.")
        return

    # Η λίστα ταινιών βρίσκεται μέσα στο αντικείμενο 'Section', στο κλειδί 'Tiles'
    if 'Section' not in list_data or 'Tiles' not in list_data['Section']:
        print("Δεν βρέθηκαν ταινίες ('Tiles') στην απάντηση του API. Η δομή μπορεί να έχει αλλάξει.")
        return

    movie_tiles = list_data['Section']['Tiles']
    print(f"Βρέθηκαν {len(movie_tiles)} ταινίες. Έναρξη επεξεργασίας...")

    for tile in movie_tiles:
        title = tile.get('Title', 'Unknown Title').strip()
        # Το codename βρίσκεται στο πεδίο 'Codename'
        codename = tile.get('Codename')

        if not codename:
            print(f"INFO: Παράλειψη '{title}' καθώς δεν έχει codename.")
            continue

        t = int(time.time() * 1000)
        params = {
            "platformCodename": "www",
            "deviceKey": DEVICE_KEY,
            "codename": codename,
            "t": t
        }
        
        try:
            player_resp = requests.get(PLAYER_API_URL, params=params, headers=headers, timeout=10)
            player_resp.raise_for_status()
            player_data = player_resp.json()
            
            stream_url = None
            if player_data.get("MediaFiles"):
                for media_file in player_data["MediaFiles"]:
                    if media_file.get("Formats"):
                        for file_format in media_file["Formats"]:
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
        except Exception as e:
            print(f"GENERIC ERROR for {title}: {e}")
        
        time.sleep(0.1)

    if not movies:
        print("\nΔεν βρέθηκαν ταινίες με έγκυρο stream.")
        return

    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for title, url in movies:
                f.write(f'#EXTINF:-1,{title}\n{url}\n')
        print(f"\nΤο αρχείο {OUTPUT_FILE} δημιουργήθηκε/ενημερώθηκε με επιτυχία με {len(movies)} ταινίες!")
    except IOError as e:
        print(f"\nΣφάλμα: Αποτυχία εγγραφής στο αρχείο: {e}")

if __name__ == "__main__":
    main()
