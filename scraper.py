import requests
import time
import json

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

# Οι κατηγορίες που εσείς βρήκατε
CATEGORIES = {
    "Κωμωδίες": "komodies-1", "Ρομαντικές": "romantikes", "Περιπέτειες": "peripeteies-1",
    "Δραματικές": "dramatikes", "Θρίλερ": "copy-of-thriler", "Βιογραφίες": "biographies-1",
    "Σινεφίλ": "sinephil", "Ελληνικός Κινηματογράφος": "ellenikos-kinematographos",
    "Μικρές Ιστορίες": "mikres-istories", "Παιδικές Ταινίες": "paidikes-tainies-1"
}

def fetch_codenames_from_category(session, section_codename):
    """Παίρνει ΟΛΑ τα codenames από μια κατηγορία, χειριζόμενο τη σελιδοποίηση με ασφάλεια."""
    category_codenames = []
    seen_ids = set()
    current_page = 1
    
    while True:
        page_params = {'platformCodename': 'www', 'sectionCodename': section_codename, 'page': current_page}
        try:
            response = session.get(PAGINATION_URL, params=page_params, headers=HEADERS, timeout=20)
            response.raise_for_status()
            page_data = response.json()

            section_content = page_data.get('SectionContent', {})
            tiles_with_ids = section_content.get('TilesIds', [])
            
            if not tiles_with_ids: break
            
            first_id = tiles_with_ids[0].get('Id')
            if first_id in seen_ids: break # Ανιχνεύτηκε επανάληψη

            new_found = 0
            for tile in tiles_with_ids:
                tile_id = tile.get('Id')
                codename = tile.get('Codename')
                if tile_id and codename and tile_id not in seen_ids:
                    seen_ids.add(tile_id)
                    category_codenames.append(codename)
                    new_found += 1
            
            if new_found == 0: break # Διπλή ασφάλεια

            current_page += 1
            time.sleep(0.1)
        except requests.exceptions.RequestException:
            break
            
    return category_codenames

def main():
    final_playlist = []
    # Χρησιμοποιούμε ένα dict για να αποθηκεύουμε το codename και την πρώτη κατηγορία που το βρήκαμε
    all_codenames_map = {} 

    session = requests.Session()

    print("--- Φάση 1: Έναρξη σάρωσης όλων των κατηγοριών για codenames ---")
    for category_name, section_codename in CATEGORIES.items():
        print(f"\n>>> Σάρωση κατηγορίας: {category_name}")
        codenames_in_category = fetch_codenames_from_category(session, section_codename)
        
        if not codenames_in_category:
            print("  -> Δεν βρέθηκαν νέες ταινίες.")
            continue
        
        # Προσθέτουμε τα νέα codenames στο κεντρικό map
        new_added = 0
        for codename in codenames_in_category:
            if codename not in all_codenames_map:
                all_codenames_map[codename] = category_name # Αποθηκεύουμε την πρώτη κατηγορία
                new_added +=1
        print(f"  -> Βρέθηκαν {len(codenames_in_category)} ταινίες. Προστέθηκαν {new_added} νέες.")
    
    total_movies = len(all_codenames_map)
    if not total_movies:
        print("\nΗ διαδικασία ολοκληρώθηκε, αλλά δεν βρέθηκαν ταινίες.")
        return

    print(f"\n--- Φάση 2: Βρέθηκαν {total_movies} μοναδικές ταινίες. Έναρξη επεξεργασίας... ---")

    for index, (codename, group_title) in enumerate(all_codenames_map.items()):
        print(f"Επεξεργασία {index + 1}/{total_movies}: {codename}")
        title = codename
        poster_url = ""

        try:
            # Λήψη λεπτομερειών (Τίτλος, Αφίσα)
            detail_params = {'platformCodename': 'www', 'codename': codename}
            detail_resp = session.get(TILE_DETAIL_API_URL, params=detail_params, headers=HEADERS, timeout=10)
            if detail_resp.status_code == 200:
                detail_data = detail_resp.json()
                title = detail_data.get('Title', codename).strip()
                poster_url = detail_data.get('Poster', '')
                print(f"  -> Βρέθηκε τίτλος: '{title}'")
            else:
                 print(f"  -> Δεν βρέθηκαν λεπτομέρειες τίτλου (Σφάλμα: {detail_resp.status_code}).")

            # Λήψη stream URL
            player_params = {"platformCodename": "www", "deviceKey": DEVICE_KEY, "codename": codename, "t": int(time.time() * 1000)}
            player_resp = session.get(PLAYER_API_URL, params=player_params, headers=HEADERS, timeout=15)
            player_resp.raise_for_status()
            player_data = player_resp.json()
            
            stream_url = None
            media_files = player_data.get("MediaFiles")
            if media_files:
                for media_file in media_files:
                    formats = media_file.get("Formats")
                    if formats:
                        for file_format in formats:
                            url = file_format.get("Url")
                            if url and url.endswith(".m3u8"):
                                stream_url = url
                                break
                    if stream_url: break
            
            if stream_url:
                final_playlist.append({'title': title, 'stream_url': stream_url, 'poster_url': poster_url, 'group_title': group_title})
                print(f"  -> Επιτυχής λήψη stream!")

        except Exception as e:
            print(f"  -> Σφάλμα: {e}")
        time.sleep(0.05)

    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            sorted_playlist = sorted(final_playlist, key=lambda x: (x['group_title'], x['title']))
            for movie in sorted_playlist:
                group_tag = f'group-title="{movie["group_title"]}"'
                logo_tag = f'tvg-logo="{movie["poster_url"]}"' if movie["poster_url"] else ""
                info_line = f'#EXTINF:-1 {group_tag} {logo_tag},{movie["title"]}\n'
                url_line = f'{movie["stream_url"]}\n'
                f.write(info_line)
                f.write(url_line)
        print(f"\nΤο αρχείο {OUTPUT_FILE} δημιουργήθηκε με επιτυχία με {len(final_playlist)} μοναδικές ταινίες!")
    except IOError as e:
        print(f"\nΣφάλμα εγγραφής στο αρχείο: {e}")

if __name__ == "__main__":
    main()
