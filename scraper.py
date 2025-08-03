import requests
import time
import json

# --- API Endpoints ---
PAGINATION_URL = "https://api.app.ertflix.gr/v1/InsysGoPage/GetSectionContent"
# Χρησιμοποιούμε το API που παίρνει λεπτομέρειες για ΜΙΑ ταινία. Είναι αξιόπιστο.
TILE_DETAIL_API_URL = "https://api.app.ertflix.gr/v1/tile/GetTile"
PLAYER_API_URL = "https://api.app.ertflix.gr/v1/Player/AcquireContent"

# --- Σταθερές ---
DEVICE_KEY = "12b9a6425e59ec1fcee9acb0e7fba4f3"
OUTPUT_FILE = "ertflix_playlist.m3u8"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def fetch_all_movie_codenames():
    """
    Μαζεύει ΟΛΑ τα codenames από όλες τις σελίδες, σταματώντας με ασφάλεια
    όταν ανιχνεύσει ότι το API έχει αρχίσει να επαναλαμβάνεται.
    """
    all_codenames = []
    seen_ids = set() # Η "ασφάλεια" μας για να μην κολλήσουμε ποτέ
    current_page = 1

    print("--- Φάση 1: Συλλογή όλων των codenames (με ανίχνευση επανάληψης) ---")
    while True:
        print(f"Λήψη σελίδας {current_page}...")
        page_params = {'platformCodename': 'www', 'sectionCodename': 'oles-oi-tainies-1', 'page': current_page}
        
        try:
            response = requests.get(PAGINATION_URL, params=page_params, headers=HEADERS, timeout=20)
            response.raise_for_status()
            page_data = response.json()

            section_content = page_data.get('SectionContent', {})
            tiles_with_ids = section_content.get('TilesIds', [])
            
            if not tiles_with_ids:
                print(f"Η σελίδα {current_page} είναι κενή. Ολοκληρώθηκε η συλλογή.")
                break
            
            # Έλεγχος για επανάληψη. Παίρνουμε το ID του πρώτου αντικειμένου.
            first_id_on_page = tiles_with_ids[0].get('Id')
            if first_id_on_page in seen_ids:
                print(f"Εντοπίστηκε επανάληψη στη σελίδα {current_page}. Ολοκληρώθηκε η συλλογή με ασφάλεια.")
                break
                
            # Προσθήκη των νέων codenames
            new_codenames_found = 0
            for tile in tiles_with_ids:
                tile_id = tile.get('Id')
                codename = tile.get('Codename')
                if tile_id and codename and tile_id not in seen_ids:
                    seen_ids.add(tile_id)
                    all_codenames.append(codename)
                    new_codenames_found += 1

            print(f"  -> Βρέθηκαν {new_codenames_found} νέα, μοναδικά codenames. Σύνολο: {len(all_codenames)}")
            current_page += 1
            time.sleep(0.2)

        except requests.exceptions.RequestException as e:
            print(f"Σφάλμα κατά τη λήψη της σελίδας {current_page}: {e}. Διακοπή.")
            break 
            
    return all_codenames

def main():
    final_playlist = []
    
    # Βήμα 1: Παίρνουμε ΟΛΑ τα codenames
    all_codenames = fetch_all_movie_codenames()
    
    if not all_codenames:
        print("\nΔεν βρέθηκαν ταινίες για επεξεργασία.")
        return

    total_movies = len(all_codenames)
    print(f"\n--- Φάση 2: Έναρξη επεξεργασίας {total_movies} ταινιών (Λήψη λεπτομερειών & stream) ---")

    for index, codename in enumerate(all_codenames):
        print(f"Επεξεργασία {index + 1}/{total_movies}: {codename}")
        title = codename # Προεπιλεγμένος τίτλος σε περίπτωση σφάλματος
        poster_url = ""

        try:
            # Βήμα 2α: Λήψη λεπτομερειών για ΚΑΘΕ ταινία ξεχωριστά (Αξιόπιστη Μέθοδος)
            detail_params = {'platformCodename': 'www', 'codename': codename}
            detail_resp = requests.get(TILE_DETAIL_API_URL, params=detail_params, headers=HEADERS, timeout=10)
            if detail_resp.status_code == 200:
                detail_data = detail_resp.json()
                title = detail_data.get('Title', codename).strip()
                poster_url = detail_data.get('Poster', '')
                print(f"  -> Βρέθηκε τίτλος: '{title}'")
            else:
                 print(f"  -> Δεν βρέθηκαν λεπτομέρειες για τον τίτλο (Σφάλμα: {detail_resp.status_code}).")

            # Βήμα 2β: Λήψη του stream URL
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

    # Βήμα 3: Δημιουργία του αρχείου M3U
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
