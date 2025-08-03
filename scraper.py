import requests
import time
import json

# API Endpoints
LIST_API_URL = "https://api.app.ertflix.gr/v1/InsysGoPage/GetSectionContent"
TILE_DETAIL_API_URL = "https://api.app.ertflix.gr/v1/tile/GetTile"  # API για να πάρουμε τον ΤΙΤΛΟ
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
        list_response = requests.get(LIST_API_URL, params=LIST_API_PARAMS, headers=HEADERS, timeout=30)
        list_response.raise_for_status()
        list_data = list_response.json()
    except Exception as e:
        print(f"Σφάλμα στο Βήμα 1: Αποτυχία λήψης της λίστας. {e}")
        return

    if 'SectionContent' not in list_data or 'TilesIds' not in list_data.get('SectionContent', {}):
        print("Μοιραίο σφάλμα: Δεν βρέθηκε η διαδρομή 'SectionContent.TilesIds' στην απάντηση του API.")
        return

    movie_tiles_info = list_data['SectionContent']['TilesIds']
    total_movies = len(movie_tiles_info)
    print(f"Βρέθηκαν {total_movies} ταινίες. Έναρξη επεξεργασίας...")

    for index, tile_info in enumerate(movie_tiles_info):
        codename = tile_info.get('codename') or tile_info.get('Codename')

        if not codename:
            print(f"Παράλειψη ταινίας {index + 1}/{total_movies} χωρίς codename.")
            continue
            
        print(f"\nΕπεξεργασία {index + 1}/{total_movies}: {codename}")

        try:
            # Βήμα 2: Λήψη του ΤΙΤΛΟΥ κάνοντας νέα κλήση
            print("  -> Βήμα 2: Λήψη τίτλου...")
            detail_params = {'platformCodename': 'www', 'codename': codename}
            detail_resp = requests.get(TILE_DETAIL_API_URL, params=detail_params, headers=HEADERS, timeout=15)
            detail_resp.raise_for_status()
            detail_data = detail_resp.json()
            title = detail_data.get('Title', codename).strip() # Αν αποτύχει, βάζει το codename

            print(f"  -> Βήμα 3: Λήψη stream URL για την ταινία '{title}'...")
            # Βήμα 3: Λήψη του stream URL
            player_params = {
                "platformCodename": "www",
                "deviceKey": DEVICE_KEY,
                "codename": codename,
                "t": int(time.time() * 1000)
            }
            player_resp = requests.get(PLAYER_API_URL, params=player_params, headers=HEADERS, timeout=15)
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
             if e.response and e.response.status_code == 404:
                print(f"  -> Δεν είναι πλέον διαθέσιμο (404).")
             else:
                print(f"  -> Σφάλμα HTTP: {e}")
        except Exception as e:
            print(f"  -> Άγνωστο σφάλμα: {e}")
        
        time.sleep(0.1)

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
