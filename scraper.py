import requests
import time
import json

# --- API Endpoints ---
PAGINATION_URL = "https://api.app.ertflix.gr/v1/InsysGoPage/GetSectionContent"
TILE_DETAILS_URL = "https://api.app.ertflix.gr/v2/Tile/GetTiles"
PLAYER_API_URL = "https://api.app.ertflix.gr/v1/Player/AcquireContent"

# --- Σταθερές ---
DEVICE_KEY = "12b9a6425e59ec1fcee9acb0e7fba4f3"
OUTPUT_FILE = "ertflix_playlist.m3u8"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://www.ertflix.gr/"
}
SPECIAL_HEADERS_PARAM = json.dumps({"X-Api-Date-Format": "iso", "X-Api-Camel-Case": "true"})

# Οι κατηγορίες που εσείς βρήκατε
CATEGORIES = {
    "Κωμωδίες": "komodies-1", "Ρομαντικές": "romantikes", "Περιπέτειες": "peripeteies-1",
    "Δραματικές": "dramatikes", "Θρίλερ": "copy-of-thriler", "Βιογραφίες": "biographies-1",
    "Σινεφίλ": "sinephil", "Ελληνικός Κινηματογράφος": "ellenikos-kinematographos",
    "Μικρές Ιστορίες": "mikres-istories", "Παιδικές Ταινίες": "paidikes-tainies-1"
}

def get_movies_from_category(section_codename):
    """Παίρνει ΟΛΕΣ τις ταινίες από μια κατηγορία, χειριζόμενο τη σελιδοποίηση."""
    all_movie_details = []
    seen_ids = set()
    current_page = 1
    
    while True:
        page_params = {'platformCodename': 'www', 'sectionCodename': section_codename, 'page': current_page, 'limit': 40}
        try:
            response = requests.get(PAGINATION_URL, params=page_params, headers=HEADERS, timeout=20)
            response.raise_for_status()
            page_data = response.json()

            section_content = page_data.get('SectionContent', {})
            tiles_with_ids = section_content.get('TilesIds', [])
            
            if not tiles_with_ids: break

            ids_to_fetch = [tile['Id'] for tile in tiles_with_ids if 'Id' in tile and tile['Id'] not in seen_ids]
            if not ids_to_fetch: break # Αν η σελίδα είναι επανάληψη, σταματάμε
            
            seen_ids.update(ids_to_fetch)
            
            details_payload = {"ids": ids_to_fetch}
            details_params = {'$headers': SPECIAL_HEADERS_PARAM}
            details_response = requests.post(TILE_DETAILS_URL, params=details_params, json=details_payload, headers=HEADERS, timeout=20)
            if details_response.status_code == 200:
                all_movie_details.extend(details_response.json())

            if len(tiles_with_ids) < 40: break
            current_page += 1
            time.sleep(0.2)
        except requests.exceptions.RequestException:
            break
            
    return all_movie_details

def main():
    final_playlist = []
    seen_codenames = set()

    print("--- Φάση 1: Έναρξη σάρωσης όλων των κατηγοριών ---")
    for category_name, section_codename in CATEGORIES.items():
        print(f"\n>>> Επεξεργασία κατηγορίας: {category_name}")
        movies_in_category = get_movies_from_category(section_codename)
        
        if not movies_in_category:
            print("  -> Δεν βρέθηκαν νέες ταινίες σε αυτή την κατηγορία.")
            continue
            
        print(f"  -> Βρέθηκαν {len(movies_in_category)} ταινίες. Έναρξη επεξεργασίας...")

        for index, tile in enumerate(movies_in_category):
            codename = tile.get('codename')
            if not codename or codename in seen_codenames: continue
                
            seen_codenames.add(codename)
            title = tile.get('title', codename).strip()
            poster_url = tile.get('poster', '')
            
            print(f"    Επεξεργασία {index + 1}/{len(movies_in_category)}: {title}")
            try:
                player_params = {"platformCodename": "www", "deviceKey": DEVICE_KEY, "codename": codename, "t": int(time.time() * 1000)}
                player_resp = requests.get(PLAYER_API_URL, params=player_params, headers=HEADERS, timeout=15)
                player_resp.raise_for_status()
                player_data = player_resp.json()
                
                stream_url = None
                media_files = player_data.get("mediaFiles")
                if media_files:
                    for media_file in media_files:
                        formats = media_file.get("formats")
                        if formats:
                            for file_format in formats:
                                url = file_format.get("url")
                                if url and url.endswith(".m3u8"):
                                    stream_url = url
                                    break
                        if stream_url: break
                
                if stream_url:
                    final_playlist.append({'title': title, 'stream_url': stream_url, 'poster_url': poster_url, 'group_title': category_name})
                    print(f"      -> Επιτυχία!")
            except Exception as e:
                print(f"      -> Σφάλμα: {e}")
            time.sleep(0.05)

    if not final_playlist:
        print("\nΗ διαδικασία ολοκληρώθηκε, αλλά δεν βρέθηκαν ταινίες με έγκυρο stream.")
        return
        
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            # Ομαδοποιούμε πρώτα τις ταινίες ανά κατηγορία για όμορφη εμφάνιση
            sorted_playlist = sorted(final_playlist, key=lambda x: x['group_title'])
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
