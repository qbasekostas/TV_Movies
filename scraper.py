import requests
import time
import json

# API Endpoints - Αυτά είναι σωστά.
LIST_API_URL = "https://api.app.ertflix.gr/v1/InsysGoPage/GetSectionContent"
PLAYER_API_URL = "https://api.app.ertflix.gr/v1/Player/AcquireContent"

# Παράμετροι για το αρχικό API call - Σωστοί.
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
    
    print("Βήμα 1: Λήψη λίστας ταινιών...")
    try:
        list_response = requests.get(LIST_API_URL, params=LIST_API_PARAMS, headers=HEADERS, timeout=20)
        list_response.raise_for_status()
        list_data = list_response.json()
    except Exception as e:
        print(f"Σφάλμα στο Βήμα 1: Αποτυχία λήψης της λίστας. {e}")
        return

    # ΔΙΟΡΘΩΜΕΝΗ ΔΙΑΔΡΟΜΗ: Ψάχνουμε απευθείας για το κλειδί 'Tiles'
    if 'Tiles' not in list_data or not list_data['Tiles']:
        print("Σφάλμα: Η δομή του JSON έχει αλλάξει. Δεν βρέθηκε το κλειδί 'Tiles'.")
        # Εκτυπώνουμε τα διαθέσιμα κλειδιά για μελλοντική διερεύνηση
        print(f"Διαθέσιμα κλειδιά στο JSON: {list_data.keys()}")
        return

    movie_tiles = list_data['Tiles']
    total_movies = len(movie_tiles)
    print(f"Βρέθηκαν {total_movies} ταινίες. Έναρξη επεξεργασίας...")

    # Ο βρόχος επεξεργάζεται τα δεδομένα από το 'Tiles'
    for index, tile in enumerate(movie_tiles):
        # Τα κλειδιά είναι με κεφαλαίο πρώτο γράμμα ('Title', 'Codename')
        title = tile.get('Title', 'Unknown Title').strip()
        codename = tile.get('Codename')

        if not codename:
            print(f"Παράλειψη ταινίας {index + 1}/{total_movies} χωρίς codename.")
            continue
            
        print(f"Επεξεργασία {index + 1}/{total_movies}: {title}")

        try:
            # Βήμα 2: Λήψη του stream URL (δεν χρειάζεται πλέον βήμα για τον τίτλο)
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
                print(f"  -> Επιτυχία!")
            else:
                print(f"  -> Δεν βρέθηκε stream.")

        except requests.exceptions.HTTPError as e:
             if e.response.status_code == 404:
                print(f"  -> Δεν είναι πλέον διαθέσιμο (404).")
             else:
                print(f"  -> Σφάλμα HTTP: {e}")
        except Exception as e:
            print(f"  -> Άγνωστο σφάλμα: {e}")
        
        time.sleep(0.05) # Μικρή καθυστέρηση

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
