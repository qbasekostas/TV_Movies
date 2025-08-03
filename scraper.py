import requests
import time
import json

# --- API Endpoints (Η ΣΩΣΤΗ ΔΙΑΔΙΚΑΣΙΑ) ---
PAGINATION_URL = "https://api.app.ertflix.gr/v1/InsysGoPage/GetSectionContent"
TILE_DETAILS_URL = "https://api.app.ertflix.gr/v2/Tile/GetTiles"
PLAYER_API_URL = "https://api.app.ertflix.gr/v1/Player/AcquireContent"

# --- Σταθερές ---
DEVICE_KEY = "12b9a6425e59ec1fcee9acb0e7fba4f3"
OUTPUT_FILE = "ertflix_playlist.m3u8"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
# Η κρίσιμη παράμετρος '$headers' ΜΟΝΟ για το GetTiles
SPECIAL_HEADERS_PARAM = json.dumps({
    "X-Api-Date-Format": "iso",
    "X-Api-Camel-Case": "true"
})

def fetch_all_movie_ids():
    """
    Μαζεύει ΟΛΑ τα IDs από όλες τις σελίδες, χρησιμοποιώντας ΑΠΛΕΣ παραμέτρους
    και σταματώντας με ασφάλεια όταν ανιχνεύσει επανάληψη.
    """
    all_ids = []
    seen_ids = set()
    current_page = 1

    print("--- Φάση 1: Συλλογή όλων των IDs (Απλή Μέθοδος) ---")
    while True:
        print(f"Λήψη σελίδας {current_page}...")
        
        # Απλή κλήση, ΧΩΡΙΣ την παράμετρο '$headers'
        page_params = {'platformCodename': 'www', 'sectionCodename': 'oles-oi-tainies-1', 'page': current_page}
        
        try:
            response = requests.get(PAGINATION_URL, params=page_params, headers=HEADERS, timeout=20)
            response.raise_for_status()
            page_data = response.json()

            section_content = page_data.get('sectionContent', {})
            tiles_with_ids = section_content.get('tilesIds', [])
            
            if not tiles_with_ids:
                print(f"Η σελίδα {current_page} είναι κενή. Ολοκληρώθηκε η συλλογή.")
                break
            
            # Έλεγχos για επανάληψη
            first_id_on_page = tiles_with_ids[0].get('Id')
            if first_id_on_page in seen_ids:
                print(f"Εντοπίστηκε επανάληψη στη σελίδα {current_page}. Ολοκληρώθηκε η συλλογή με ασφάλεια.")
                break
            
            new_ids_found = 0
            for tile in tiles_with_ids:
                tile_id = tile.get('Id')
                if tile_id and tile_id not in seen_ids:
                    seen_ids.add(tile_id)
                    all_ids.append(tile_id)
                    new_ids_found += 1
            
            if new_ids_found == 0:
                print(f"Εντοπίστηκε επανάληψη (δευτερεύων έλεγχος). Ολοκληρώθηκε η συλλογή.")
                break

            print(f"  -> Βρέθηκαν {new_ids_found} νέα, μοναδικά IDs. Σύνολο: {len(all_ids)}")
            current_page += 1
            time.sleep(0.2)

        except requests.exceptions.RequestException as e:
            print(f"Σφάλμα κατά τη λήψη της σελίδας {current_page}: {e}. Διακοπή.")
            break 
            
    return all_ids

def get_details_in_batches(all_ids, batch_size=50):
    """Παίρνει τη λίστα με τα IDs και ζητάει τις λεπτομέρειες σε παρτίδες."""
    all_movie_details = []
    print(f"\n--- Φάση 2: Λήψη λεπτομερειών για {len(all_ids)} ταινίες (σε παρτίδες των {batch_size}) ---")
    for i in range(0, len(all_ids), batch_size):
        batch_ids = all_ids[i:i + batch_size]
        print(f"Λήψη λεπτομερειών για την παρτίδα {i//batch_size + 1}...")
        try:
            details_payload = {"ids": batch_ids}
            details_params = {'$headers': SPECIAL_HEADERS_PARAM} # ΜΟΝΟ ΕΔΩ χρειάζεται
            details_response = requests.post(TILE_DETAILS_URL, params=details_params, json=details_payload, headers=HEADERS, timeout=20)
            if details_response.status_code == 200:
                detailed_tiles = details_response.json()
                all_movie_details.extend(detailed_tiles)
                print(f"  -> Επιτυχία! Σύνολο ταινιών με λεπτομέρειες: {len(all_movie_details)}")
            else:
                print(f"  -> Σφάλμα κατά τη λήψη λεπτομερειών: {details_response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"  -> Σφάλμα δικτύου κατά τη λήψη παρτίδας: {e}")
        time.sleep(0.2)
    return all_movie_details

def main():
    final_playlist = []
    
    # Βήμα 1: Παίρνουμε ΟΛΑ τα IDs
    all_ids = fetch_all_movie_ids()
    
    # Βήμα 2: Παίρνουμε ΟΛΕΣ τις λεπτομέρειες
    all_movies_with_details = get_details_in_batches(all_ids)
    
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

    # Βήμα 4: Δημιουργία του αρχείου M3U
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
