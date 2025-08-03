import requests
import time
import json

# API Endpoints
LIST_API_URL = "https://api.app.ertflix.gr/v1/InsysGoPage/GetSectionContent"
TILE_API_URL = "https://api.app.ertflix.gr/v1/tile/GetTile" # Νέο API για τη λήψη του τίτλου
PLAYER_API_URL = "https://api.app.ertflix.gr/v1/Player/AcquireContent"

# Παράμετροι για το αρχικό API call
LIST_API_PARAMS = {
    'platformCodename': 'www',
    'sectionCodename': 'oles-oi-tainies-1'
}

# Σταθερές
DEVICE_KEY = "12b9a6425e59ec1fcee9acb0e7fba4f3"
OUTPUT_FILE = "ertflix_playlist.m3u8"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def main():
    movies = []
    
    print("Βήμα 1: Λήψη λίστας με τα codenames των ταινιών...")
    try:
        list_response = requests.get(LIST_API_URL, params=LIST_API_PARAMS, headers=HEADERS, timeout=20)
        list_response.raise_for_status()
        list_data = list_response.json()
    except Exception as e:
        print(f"Σφάλμα στο Βήμα 1: Αποτυχία λήψης της λίστας. {e}")
        return

    # Σωστή διαδρομή στο JSON, σύμφωνα με την απάντησή σας
    if 'sectionContent' not in list_data or 'tilesIds' not in list_data['sectionContent']:
        print("Σφάλμα: Η δομή του JSON έχει αλλάξει. Δεν βρέθηκε το 'sectionContent.tilesIds'.")
        return

    movie_tiles = list_data['sectionContent']['tilesIds']
    total_movies = len(movie_tiles)
    print(f"Βρέθηκαν {total_movies} ταινίες. Έναρξη επεξεργασίας...")

    # Ο βρόχος τώρα επεξεργάζεται τα δεδομένα από το 'tilesIds'
    for index, tile_info in enumerate(movie_tiles):
        codename = tile_info.get('codename')
        if not codename:
            continue

        print(f"\nΕπεξεργασία ταινίας {index + 1}/{total_movies}: {codename}")
        
        try:
            # Βήμα 2: Λήψη του τίτλου της ταινίας
            print("  Βήμα 2: Λήψη τίτλου...")
            tile_params = {'platformCodename': 'www', 'codename': codename}
            tile_resp = requests.get(TILE_API_URL, params=tile_params, headers=HEADERS, timeout=10)
            tile_resp.raise_for_status()
            title_data = tile_resp.json()
            title = title_data.get('Title', codename).strip() # Αν δεν βρεθεί τίτλος, χρησιμοποιούμε το codename
            print(f"  OK: Ο τίτλος είναι '{title}'")

            # Βήμα 3: Λήψη του stream URL
            print("  Βήμα 3: Λήψη stream URL...")
            player_params = {
                "platformCodename": "www",
                "deviceKey": DEVICE_KEY,
                "codename": codename,
                "t": int(time.time() * 1000)
            }
            player_resp = requests.get(PLAYER_API_URL, params=player_params, headers=HEADERS, timeout=10)
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
                print(f"  ΕΠΙΤΥΧΙΑ: Βρέθηκε το stream για την ταινία '{title}'.")
            else:
                print(f"  ΣΦΑΛΜΑ: Δεν βρέθηκε stream για την ταινία '{title}'.")

        except requests.exceptions.RequestException as e:
            print(f"  ΣΦΑΛΜΑ ΔΙΚΤΥΟΥ για το codename '{codename}': {e}")
        except Exception as e:
            print(f"  ΓΕΝΙΚΟ ΣΦΑΛΜΑ για το codename '{codename}': {e}")
        
        time.sleep(0.1) # Μικρή καθυστέρηση για να μην μπλοκαριστούμε

    if not movies:
        print("\nΗ διαδικασία ολοκληρώθηκε, αλλά δεν βρέθηκαν ταινίες με έγκυρο stream.")
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
