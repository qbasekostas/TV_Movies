import requests
import time
import json

# --- API Endpoints ---
# Το ΜΟΝΑΔΙΚΟ URL που θα καλέσουμε για τη λίστα, όπως το δώσατε εσείς.
LIST_URL = "https://api.app.ertflix.gr/v1/InsysGoPage/GetSectionContent"
# Τα APIs για τις λεπτομέρειες και το stream.
TILE_DETAIL_API_URL = "https://api.app.ertflix.gr/v1/tile/GetTile"
PLAYER_API_URL = "https://api.app.ertflix.gr/v1/Player/AcquireContent"

# --- Σταθερές ---
DEVICE_KEY = "12b9a6425e59ec1fcee9acb0e7fba4f3"
OUTPUT_FILE = "ertflix_playlist.m3u8"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def main():
    final_playlist = []
    
    # --- ΒΗΜΑ 1: ΛΗΨΗ ΤΗΣ ΜΙΑΣ ΚΑΙ ΜΟΝΑΔΙΚΗΣ ΛΙΣΤΑΣ ---
    print("--- Φάση 1: Λήψη της βασικής λίστας ταινιών ---")
    
    try:
        # Οι παράμετροι για τη μία και μοναδική κλήση.
        params = {'platformCodename': 'www', 'sectionCodename': 'oles-oi-tainies-1'}
        response = requests.get(LIST_URL, params=params, headers=HEADERS, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        # Διαβάζουμε το JSON με τα σωστά, lowercase keys.
        section_content = data.get('sectionContent', {})
        movies_to_process = section_content.get('tilesIds', [])
        
        if not movies_to_process:
            print("Δεν βρέθηκαν ταινίες στην απάντηση του API. Τέλος.")
            return

    except requests.exceptions.RequestException as e:
        print(f"Σφάλμα κατά τη λήψη της λίστας: {e}")
        return

    # --- ΒΗΜΑ 2: ΕΠΕΞΕΡΓΑΣΙΑ ΤΩΝ ΤΑΙΝΙΩΝ ΠΟΥ ΒΡΕΘΗΚΑΝ ---
    total_movies = len(movies_to_process)
    print(f"\n--- Φάση 2: Βρέθηκαν {total_movies} ταινίες. Έναρξη επεξεργασίας... ---")

    for index, tile in enumerate(movies_to_process):
        # Τα κλειδιά εδώ είναι με κεφαλαία ('Codename')
        codename = tile.get('Codename')
        if not codename:
            continue
        
        print(f"Επεξεργασία {index + 1}/{total_movies}: {codename}")
        title = codename # Προεπιλεγμένος τίτλος
        poster_url = ""

        try:
            # Λήψη λεπτομερειών για κάθε ταινία
            detail_params = {'platformCodename': 'www', 'codename': codename}
            detail_resp = requests.get(TILE_DETAIL_API_URL, params=detail_params, headers=HEADERS, timeout=10)
            if detail_resp.status_code == 200:
                detail_data = detail_resp.json()
                title = detail_data.get('Title', codename).strip()
                poster_url = detail_data.get('Poster', '')
                print(f"  -> Βρέθηκε τίτλος: '{title}'")
            else:
                 print(f"  -> Δεν βρέθηκαν λεπτομέρειες τίτλου (Σφάλμα: {detail_resp.status_code}).")

            # Λήψη του stream URL
            player_params = {"platformCodename": "www", "deviceKey": DEVICE_KEY, "codename": codename, "t": int(time.time() * 1000)}
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
                final_playlist.append({'title': title, 'stream_url': stream_url, 'poster_url': poster_url})
                print(f"  -> Επιτυχής λήψη stream!")
            else:
                print(f"  -> Δεν βρέθηκε stream.")
        except Exception as e:
            print(f"  -> Σφάλμα: {e}")
        
        time.sleep(0.05)

    # --- ΒΗΜΑ 3: ΔΗΜΙΟΥΡΓΙΑ ΤΟΥ ΑΡΧΕΙΟΥ ---
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for movie in final_playlist:
                logo_tag = f'tvg-logo="{movie["poster_url"]}"' if movie["poster_url"] else ""
                f.write(f'#EXTINF:-1 {logo_tag},{movie["title"]}\n{movie["stream_url"]}\n')
        print(f"\nΤο αρχείο {OUTPUT_FILE} δημιουργήθηκε με επιτυχία με {len(final_playlist)} ταινίες!")
    except IOError as e:
        print(f"\nΣφάλμα εγγραφής στο αρχείο: {e}")

if __name__ == "__main__":
    main()
