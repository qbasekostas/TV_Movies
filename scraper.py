import requests
import time
import json

# --- API Endpoints (Όπως τα βρήκατε εσείς) ---
PAGINATION_URL = "https://api.app.ertflix.gr/v1/InsysGoPage/GetSectionContent" # Για τις σελίδες με τα IDs
TILE_DETAILS_URL = "https://api.app.ertflix.gr/v2/Tile/GetTiles" # Για τους ελληνικούς τίτλους & αφίσες
PLAYER_API_URL = "https://api.app.ertflix.gr/v1/Player/AcquireContent" # Για το τελικό stream

# --- Σταθερές ---
DEVICE_KEY = "12b9a6425e59ec1fcee9acb0e7fba4f3"
OUTPUT_FILE = "ertflix_playlist.m3u8"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "X-Api-Date-Format": "iso",
    "X-Api-Camel-Case": "true"
}

def fetch_all_movie_details():
    """
    Μιμείται την πραγματική διαδικασία: παίρνει τις σελίδες με τα IDs και μετά
    ζητάει μαζικά τις λεπτομέρειες (τίτλους, αφίσες).
    """
    all_movies = []
    current_page = 1

    print("--- Φάση 1: Συλλογή IDs από όλες τις σελίδες ---")
    while True:
        print(f"Λήψη σελίδας {current_page}...")
        page_params = {'platformCodename': 'www', 'sectionCodename': 'oles-oi-tainies-1', 'page': current_page}
        
        try:
            response = requests.get(PAGINATION_URL, params=page_params, headers=HEADERS, timeout=20)
            response.raise_for_status()
            page_data = response.json()

            section_content = page_data.get('sectionContent', {})
            tiles_with_ids = section_content.get('tilesIds', [])
            
            if not tiles_with_ids:
                print(f"Η σελίδα {current_page} είναι κενή. Ολοκληρώθηκε η συλλογή IDs.")
                break
            
            # Παίρνουμε τα IDs από αυτή τη σελίδα
            ids_to_fetch = [tile['id'] for tile in tiles_with_ids if 'id' in tile]
            print(f"  -> Βρέθηκαν {len(ids_to_fetch)} IDs. Γίνεται λήψη των λεπτομερειών τους...")

            # --- Φάση 2: Λήψη Τίτλων & Εικόνων για τη συγκεκριμένη σελίδα ---
            if ids_to_fetch:
                details_payload = {"Ids": ids_to_fetch}
                details_response = requests.post(TILE_DETAILS_URL, json=details_payload, headers=HEADERS, timeout=20)
                if details_response.status_code == 200:
                    detailed_tiles = details_response.json()
                    all_movies.extend(detailed_tiles)
                    print(f"  -> Επιτυχής λήψη λεπτομερειών. Σύνολο ταινιών μέχρι στιγμής: {len(all_movies)}")
                else:
                    print(f"  -> Σφάλμα κατά τη λήψη λεπτομερειών: {details_response.status_code}")
            
            current_page += 1
            time.sleep(0.2)

        except requests.exceptions.RequestException as e:
            print(f"Σφάλμα κατά τη λήψη της σελίδας {current_page}: {e}. Διακοπή.")
            break 
            
    return all_movies

def main():
    final_playlist = []
    
    # Βήμα 1 & 2 συνδυασμένα: Παίρνουμε μια πλήρη λίστα με όλες τις ταινίες και τις λεπτομέρειές τους
    all_movies_with_details = fetch_all_movie_details()
    
    if not all_movies_with_details:
        print("\nΔεν βρέθηκαν ταινίες για επεξεργασία.")
        return

    total_movies = len(all_movies_with_details)
    print(f"\n--- Φάση 3: Έναρξη επεξεργασίας {total_movies} ταινιών για λήψη stream URL ---")

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
            if player_data.get("mediaFiles"):
                for media_file in player_data["mediaFiles"]:
                    if media_file.get("formats"):
                        for file_format in media_file["formats"]:
                            if file_format.get("url", "").endswith(".m3u8"):
                                stream_url = file_format["url"]
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

    if not final_playlist:
        print("\nΗ διαδικασία ολοκληρώθηκε, αλλά δεν βρέθηκαν ταινίες με έγκυρο stream.")
        return

    # Βήμα 4: Δημιουργία του αρχείου M3U
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
