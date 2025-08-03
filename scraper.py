import requests
import time
import json
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# --- API Endpoints ---
PAGINATION_URL = "https://api.app.ertflix.gr/v1/InsysGoPage/GetSectionContent"
TILE_DETAIL_API_URL = "https://api.app.ertflix.gr/v1/tile/GetTile"
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

def requests_retry_session(
    retries=3,
    backoff_factor=0.3,
    status_forcelist=(500, 502, 504),
    session=None,
):
    """Δημιουργεί ένα session που κάνει αυτόματη επανάληψη σε περίπτωση σφάλματος δικτύου ή server."""
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def fetch_all_movie_codenames():
    """
    Μαζεύει ΟΛΑ τα codenames από όλες τις σελίδες, σταματώντας με ασφάλεια
    όταν ανιχνεύσει ότι το API έχει αρχίσει να επαναλαμβάνεται.
    """
    all_codenames = []
    seen_ids = set()
    current_page = 1
    session = requests_retry_session()

    print("--- Φάση 1: Συλλογή όλων των codenames (Ανθεκτική Μέθοδος) ---")
    while True:
        print(f"Λήψη σελίδας {current_page}...")
        
        page_params = {
            'platformCodename': 'www',
            'sectionCodename': 'oles-oi-tainies-1',
            'page': current_page
        }
        
        try:
            response = session.get(PAGINATION_URL, params=page_params, headers=HEADERS, timeout=20)
            response.raise_for_status()
            page_data = response.json()

            section_content = page_data.get('SectionContent', {})
            tiles_with_ids = section_content.get('TilesIds', [])
            
            if not tiles_with_ids:
                print(f"Η σελίδα {current_page} είναι κενή. Ολοκληρώθηκε η συλλογή.")
                break
            
            first_id_on_page = tiles_with_ids[0].get('Id')
            if first_id_on_page in seen_ids:
                print(f"Εντοπίστηκε επανάληψη στη σελίδα {current_page}. Ολοκληρώθηκε η συλλογή με ασφάλεια.")
                break
                
            new_codenames_found = 0
            for tile in tiles_with_ids:
                tile_id = tile.get('Id')
                codename = tile.get('Codename')
                if tile_id and codename and tile_id not in seen_ids:
                    seen_ids.add(tile_id)
                    all_codenames.append(codename)
                    new_codenames_found += 1

            if new_codenames_found == 0:
                print(f"Εντοπίστηκε επανάληψη (όλα τα IDs της σελίδας υπάρχουν ήδη). Ολοκληρώθηκε η συλλογή.")
                break

            print(f"  -> Βρέθηκαν {new_codenames_found} νέα, μοναδικά codenames. Σύνολο: {len(all_codenames)}")
            current_page += 1
            time.sleep(0.2)

        except Exception as e:
            print(f"Σφάλμα κατά τη λήψη της σελίδας {current_page}: {e}. Διακοπή.")
            break 
            
    return all_codenames

def main():
    final_playlist = []
    session = requests_retry_session()
    
    all_codenames = fetch_all_movie_codenames()
    
    if not all_codenames:
        print("\nΔεν βρέθηκαν ταινίες για επεξεργασία.")
        return

    total_movies = len(all_codenames)
    print(f"\n--- Φάση 2: Έναρξη επεξεργασίας {total_movies} ταινιών ---")

    for index, codename in enumerate(all_codenames):
        print(f"Επεξεργασία {index + 1}/{total_movies}: {codename}")
        title = codename
        poster_url = ""

        try:
            detail_params = {'platformCodename': 'www', 'codename': codename, '$headers': SPECIAL_HEADERS_PARAM}
            detail_resp = session.get(TILE_DETAIL_API_URL, params=detail_params, headers=HEADERS, timeout=10)
            if detail_resp.status_code == 200:
                detail_data = detail_resp.json()
                title = detail_data.get('title', codename).strip()
                poster_url = detail_data.get('poster', '')
                print(f"  -> Βρέθηκε τίτλος: '{title}'")
            else:
                 print(f"  -> Δεν βρέθηκαν λεπτομέρειες τίτλου (Σφάλμα: {detail_resp.status_code}).")

            player_params = {"platformCodename": "www", "deviceKey": DEVICE_KEY, "codename": codename, "t": int(time.time() * 1000)}
            player_resp = session.get(PLAYER_API_URL, params=player_params, headers=HEADERS, timeout=15)
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
