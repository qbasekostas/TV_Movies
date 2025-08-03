import requests
import time
import json

# --- API Endpoints ---
LIST_API_URL = "https://api.app.ertflix.gr/v1/InsysGoPage/GetSectionContent"
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
    "Κωμωδίες": "komodies-1",
    "Ρομαντικές": "romantikes",
    "Περιπέτειες": "peripeteies-1",
    "Δραματικές": "dramatikes",
    "Θρίλερ": "copy-of-thriler",
    "Βιογραφίες": "biographies-1",
    "Σινεφίλ": "sinephil",
    "Ελληνικός Κινηματογράφος": "ellenikos-kinematographos",
    "Μικρές Ιστορίες": "mikres-istories",
    "Παιδικές Ταινίες": "paidikes-tainies-1"
}

def main():
    final_playlist = []
    seen_codenames = set() # Για να αποφεύγουμε τις διπλές εγγραφές

    # --- ΒΗΜΑ 1: ΣΑΡΩΣΗ ΟΛΩΝ ΤΩΝ ΚΑΤΗΓΟΡΙΩΝ ---
    print("--- Φάση 1: Έναρξη σάρωσης όλων των κατηγοριών ---")
    
    for category_name, section_codename in CATEGORIES.items():
        print(f"\n>>> Επεξεργασία κατηγορίας: {category_name}")
        try:
            params = {'platformCodename': 'www', 'sectionCodename': section_codename}
            response = requests.get(LIST_API_URL, params=params, headers=HEADERS, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            section_content = data.get('SectionContent', {})
            movies_in_category = section_content.get('TilesIds', [])
            
            if not movies_in_category:
                print("  -> Δεν βρέθηκαν ταινίες σε αυτή την κατηγορία.")
                continue

            print(f"  -> Βρέθηκαν {len(movies_in_category)} ταινίες. Έναρξη επεξεργασίας...")
            
            # --- ΒΗΜΑ 2: ΕΠΕΞΕΡΓΑΣΙΑ ΤΑΙΝΙΩΝ ΑΝΑ ΚΑΤΗΓΟΡΙΑ ---
            for index, tile in enumerate(movies_in_category):
                codename = tile.get('Codename')
                if not codename or codename in seen_codenames:
                    continue # Παραλείπουμε αν δεν έχει codename ή αν την έχουμε ήδη βρει
                
                seen_codenames.add(codename)
                print(f"    Επεξεργασία {index + 1}/{len(movies_in_category)}: {codename}")
                title = codename
                poster_url = ""

                try:
                    # Λήψη λεπτομερειών (Τίτλος, Αφίσα)
                    detail_params = {'platformCodename': 'www', 'codename': codename}
                    detail_resp = requests.get(TILE_DETAIL_API_URL, params=detail_params, headers=HEADERS, timeout=10)
                    if detail_resp.status_code == 200:
                        detail_data = detail_resp.json()
                        title = detail_data.get('Title', codename).strip()
                        poster_url = detail_data.get('Poster', '')
                    
                    # Λήψη stream URL
                    player_params = {"platformCodename": "www", "deviceKey": DEVICE_KEY, "codename": codename, "t": int(time.time() * 1000)}
                    player_resp = requests.get(PLAYER_API_URL, params=player_params, headers=HEADERS, timeout=15)
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
                            if stream_url:
                                break
                    
                    if stream_url:
                        final_playlist.append({
                            'title': title, 
                            'stream_url': stream_url, 
                            'poster_url': poster_url,
                            'group_title': category_name # Προσθέτουμε την κατηγορία για την ομαδοποίηση
                        })
                        print(f"      -> Επιτυχία για την ταινία '{title}'!")

                except Exception as e:
                    print(f"      -> Σφάλμα κατά την επεξεργασία του '{codename}': {e}")
                
                time.sleep(0.05)

        except requests.exceptions.RequestException as e:
            print(f"  -> Σφάλμα κατά τη λήψη της κατηγορίας '{category_name}': {e}")

    # --- ΒΗΜΑ 3: ΔΗΜΙΟΥΡΓΙΑ ΤΟΥ ΤΕΛΙΚΟΥ ΑΡΧΕΙΟΥ ---
    if not final_playlist:
        print("\nΗ διαδικασία ολοκληρώθηκε, αλλά δεν βρέθηκαν ταινίες με έγκυρο stream.")
        return
        
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for movie in final_playlist:
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
