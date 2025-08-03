import requests
import time
import json

# --- API Endpoints ---
LIST_API_URL = "https://api.app.ertflix.gr/v1/InsysGoPage/GetSectionContent"
TILE_DETAILS_URL = "https://api.app.ertflix.gr/v2/Tile/GetTiles"
PLAYER_API_URL = "https://api.app.ertflix.gr/v1/Player/AcquireContent"

# --- Σταθερές ---
DEVICE_KEY = "12b9a6425e59ec1fcee9acb0e7fba4f3"
OUTPUT_FILE = "ertflix_playlist.m3u8"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://www.ertflix.gr/"
}
SPECIAL_HEADERS_PARAM = json.dumps({
    "X-Api-Date-Format": "iso",
    "X-Api-Camel-Case": "true"
})

def main():
    final_playlist = []
    
    # --- ΒΗΜΑ 1: ΛΗΨΗ ΟΛΩΝ ΤΩΝ ΤΑΙΝΙΩΝ ΜΕ ΜΙΑ ΚΛΗΣΗ (Η ΣΩΣΤΗ ΜΕΘΟΔΟΣ) ---
    print("--- Φάση 1: Λήψη όλων των IDs με μία κλήση (limit=1000)... ---")
    
    try:
        params = {
            'platformCodename': 'www',
            'sectionCodename': 'oles-oi-tainies-1',
            'page': 1,
            'limit': 1000, # Η δική σας, σωστή ανακάλυψη
            'ignoreLimit': 'false',
            '$headers': SPECIAL_HEADERS_PARAM
        }
        response = requests.get(LIST_API_URL, params=params, headers=HEADERS, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Η ΔΙΚΗ ΣΑΣ, ΣΩΣΤΗ ΔΙΟΡΘΩΣΗ: Διαβάζουμε το JSON με lowercase keys
        section_content = data.get('sectionContent', {})
        tiles_with_ids = section_content.get('tilesIds', [])
        
        if not tiles_with_ids:
            print("Δεν βρέθηκαν IDs στην απάντηση του API. Τέλος.")
            return

        # Τα κλειδιά μέσα στη λίστα είναι με κεφαλαία ('Id')
        ids_to_fetch = [tile['Id'] for tile in tiles_with_ids if 'Id' in tile]
        print(f"  -> Βρέθηκαν {len(ids_to_fetch)} IDs. Γίνεται μαζική λήψη λεπτομερειών...")

    except requests.exceptions.RequestException as e:
        print(f"Σφάλμα κατά τη λήψη της λίστας: {e}")
        return

    # --- ΒΗΜΑ 2: ΜΑΖΙΚΗ ΛΗΨΗ ΛΕΠΤΟΜΕΡΕΙΩΝ ---
    all_movies_with_details = []
    if ids_to_fetch:
        try:
            details_payload = {"ids": ids_to_fetch}
            details_params = {'$headers': SPECIAL_HEADERS_PARAM}
            details_response = requests.post(TILE_DETAILS_URL, params=details_params, json=details_payload, headers=HEADERS, timeout=30)
            if details_response.status_code == 200:
                all_movies_with_details = details_response.json()
                print(f"  -> Επιτυχής λήψη λεπτομερειών για {len(all_movies_with_details)} ταινίες.")
            else:
                print(f"  -> Σφάλμα κατά τη λήψη λεπτομερειών: {details_response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"  -> Σφάλμα δικτύου κατά τη λήψη λεπτομερειών: {e}")

    if not all_movies_with_details:
        print("\nΔεν βρέθηκαν ταινίες για επεξεργασία.")
        return

    # --- ΒΗΜΑ 3: ΕΠΕΞΕΡΓΑΣΙΑ ΚΑΙ ΛΗΨΗ STREAM ---
    total_movies = len(all_movies_with_details)
    print(f"\n--- Φάση 2: Έναρξη επεξεργασίας {total_movies} ταινιών... ---")

    for index, tile in enumerate(all_movies_with_details):
        codename = tile.get('codename')
        title = tile.get('title', codename or "Unknown Title").strip()
        poster_url = tile.get('poster') or ""

        if not codename:
            continue
            
        print(f"Επεξεργασία {index + 1}/{total_movies}: {title}")

        try:
            player_params = {"platformCodename": "www", "deviceKey": DEVICE_KEY, "codename": codename, "t": int(time.time() * 1000)}
            player_resp = requests.get(PLAYER_API_URL, params=player_params, headers=HEADERS, timeout=15)
            player_resp.raise_for_status()
            player_data = player_resp.json()
            
            stream_url = None
            # Τα κλειδιά εδώ είναι με κεφαλαία ('MediaFiles', 'Formats', 'Url')
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
                print(f"  -> Επιτυχία!")
            else:
                print(f"  -> Δεν βρέθηκε stream.")
        except Exception as e:
            print(f"  -> Σφάλμα: {e}")
        
        time.sleep(0.05)

    # --- ΒΗΜΑ 4: ΔΗΜΙΟΥΡΓΙΑ ΑΡΧΕΙΟΥ ---
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
