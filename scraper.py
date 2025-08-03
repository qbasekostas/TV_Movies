import requests
import time
import json

# --- API Endpoints ---
# 1. Για την αρχική λήψη και το ToplistCodename
INITIAL_LOAD_URL = "https://api.app.ertflix.gr/v1/InsysGoPage/GetSectionContent"
# 2. Για το "άπειρο scroll"
INFINITE_SCROLL_URL = "https://api.app.ertflix.gr/v1/toplist/GetToplistPage"
# 3. Για τις λεπτομέρειες (Τίτλος, Αφίσα) κάθε ταινίας
TILE_DETAIL_API_URL = "https://api.app.ertflix.gr/v1/tile/GetTile"
# 4. Για το τελικό stream URL
PLAYER_API_URL = "https://api.app.ertflix.gr/v1/Player/AcquireContent"

# --- Σταθερές ---
DEVICE_KEY = "12b9a6425e59ec1fcee9acb0e7fba4f3"
OUTPUT_FILE = "ertflix_playlist.m3u8"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def fetch_all_movie_codenames():
    """
    Μιμείται το scroll: παίρνει την πρώτη σελίδα, βρίσκει το 'ToplistCodename'
    και μετά καλεί το API του scroll για να μαζέψει όλα τα υπόλοιπα codenames.
    """
    all_codenames = []
    
    # --- ΒΗΜΑ Α: ΛΗΨΗ ΠΡΩΤΗΣ ΣΕΛΙΔΑΣ ---
    print("Βήμα 1: Λήψη αρχικής σελίδας για τον κωδικό λίστας (ToplistCodename)...")
    try:
        initial_params = {'platformCodename': 'www', 'sectionCodename': 'oles-oi-tainies-1'}
        response = requests.get(INITIAL_LOAD_URL, params=initial_params, headers=HEADERS, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        section_content = data.get('SectionContent', {})
        initial_tiles = section_content.get('TilesIds', [])
        for tile in initial_tiles:
            if tile.get('Codename'):
                all_codenames.append(tile['Codename'])
        
        toplist_codename = section_content.get('ToplistCodename')
        if not toplist_codename:
            print("Προειδοποίηση: Δεν βρέθηκε ToplistCodename. Θα ληφθούν μόνο οι αρχικές ταινίες.")
            return all_codenames
            
        print(f"  -> Επιτυχία! Κωδικός λίστας για scroll: '{toplist_codename}'")

    except requests.exceptions.RequestException as e:
        print(f"Σφάλμα κατά τη λήψη της πρώτης σελίδας: {e}")
        return []

    # --- ΒΗΜΑ Β: ΠΡΟΣΟΜΟΙΩΣΗ SCROLL ---
    print("\nΒήμα 2: Έναρξη λήψης υπόλοιπων σελίδων...")
    current_page = 2
    while True:
        print(f"Λήψη σελίδας {current_page}...")
        scroll_params = {'platformCodename': 'www', 'toplistCodename': toplist_codename, 'page': current_page}
        
        try:
            response = requests.get(INFINITE_SCROLL_URL, params=scroll_params, headers=HEADERS, timeout=20)
            response.raise_for_status()
            data = response.json()
            new_tiles = data.get('Tiles', [])
            
            if not new_tiles:
                print(f"Η σελίδα {current_page} είναι κενή. Ολοκληρώθηκε το scroll.")
                break
            
            for tile in new_tiles:
                if tile.get('Codename'):
                    all_codenames.append(tile['Codename'])

            print(f"  -> Βρέθηκαν {len(new_tiles)} νέες ταινίες. Σύνολο codenames: {len(all_codenames)}")
            current_page += 1
            time.sleep(0.2)

        except requests.exceptions.RequestException as e:
            print(f"Σφάλμα κατά τη λήψη της σελίδας {current_page}: {e}. Διακοπή.")
            break
            
    # Επιστρέφουμε μοναδικά codenames για ασφάλεια
    return list(dict.fromkeys(all_codenames))

def main():
    final_movies_list = []
    
    # Παίρνουμε τη λίστα με ΟΛΑ τα codenames
    all_codenames = fetch_all_movie_codenames()
    
    if not all_codenames:
        print("\nΔεν βρέθηκαν ταινίες για επεξεργασία.")
        return

    total_movies = len(all_codenames)
    print(f"\nΒήμα 3: Έναρξη επεξεργασίας {total_movies} ταινιών (λήψη λεπτομερειών & stream)...")

    for index, codename in enumerate(all_codenames):
        print(f"Επεξεργασία {index + 1}/{total_movies}: {codename}")
        title = codename # Προσωρινός τίτλος σε περίπτωση σφάλματος
        poster_url = ""
        
        try:
            # Βήμα 3α: Λήψη λεπτομερειών (Τίτλος, Αφίσα)
            detail_params = {'platformCodename': 'www', 'codename': codename}
            detail_resp = requests.get(TILE_DETAIL_API_URL, params=detail_params, headers=HEADERS, timeout=15)
            if detail_resp.status_code == 200:
                detail_data = detail_resp.json()
                title = detail_data.get('Title', codename).strip()
                poster_url = detail_data.get('Poster', "")
            
            # Βήμα 3β: Λήψη stream URL
            player_params = {"platformCodename": "www", "deviceKey": DEVICE_KEY, "codename": codename, "t": int(time.time() * 1000)}
            player_resp = requests.get(PLAYER_API_URL, params=player_params, headers=HEADERS, timeout=15)
            player_resp.raise_for_status() # Αν αποτύχει εδώ, προχωράει στο except
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
                final_movies_list.append({'title': title, 'stream_url': stream_url, 'poster_url': poster_url})
                print(f"  -> Επιτυχία για την ταινία '{title}'!")
            else:
                print(f"  -> Δεν βρέθηκε stream για την ταινία '{title}'.")
        except Exception as e:
            print(f"  -> Σφάλμα κατά την πλήρη επεξεργασία του '{codename}': {e}")
        
        time.sleep(0.05)

    if not final_movies_list:
        print("\nΗ διαδικασία ολοκληρώθηκε, αλλά δεν βρέθηκαν ταινίες με έγκυρο stream.")
        return

    # Βήμα 4: Δημιουργία του τελικού αρχείου
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for movie in final_movies_list:
                logo_tag = f'tvg-logo="{movie["poster_url"]}"' if movie["poster_url"] else ""
                f.write(f'#EXTINF:-1 {logo_tag},{movie["title"]}\n{movie["stream_url"]}\n')
        print(f"\nΤο αρχείο {OUTPUT_FILE} δημιουργήθηκε με επιτυχία με {len(final_movies_list)} ταινίες!")
    except IOError as e:
        print(f"\nΣφάλμα εγγραφής στο αρχείο: {e}")

if __name__ == "__main__":
    main()
