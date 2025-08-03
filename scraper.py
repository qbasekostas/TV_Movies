import requests
import time
import json

# --- API Endpoints (Η ΣΩΣΤΗ ΔΙΑΔΙΚΑΣΙΑ) ---
# 1. Για την αρχική λήψη του ToplistCodename
INITIAL_LOAD_URL = "https://api.app.ertflix.gr/v1/InsysGoPage/GetSectionContent"
# 2. Το API που είναι ΠΡΑΓΜΑΤΙΚΑ υπεύθυνο για το scroll/σελιδοποίηση
PAGINATION_API_URL = "https://api.app.ertflix.gr/v1/toplist/GetToplistPage"
# 3. Το API για το τελικό stream
PLAYER_API_URL = "https://api.app.ertflix.gr/v1/Player/AcquireContent"

# --- Σταθερές ---
DEVICE_KEY = "12b9a6425e59ec1fcee9acb0e7fba4f3"
OUTPUT_FILE = "ertflix_playlist.m3u8"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def fetch_all_movies():
    """
    Μιμείται την πραγματική λειτουργία του ertflix.gr: παίρνει το ToplistCodename
    και μετά χρησιμοποιεί το σωστό API για να πάρει ΟΛΕΣ τις σελίδες.
    """
    all_movies_data = []
    
    # --- ΒΗΜΑ 1: ΛΗΨΗ ΤΟΥ ToplistCodename ---
    print("--- Φάση 1: Λήψη του κωδικού λίστας (ToplistCodename) ---")
    try:
        initial_params = {'platformCodename': 'www', 'sectionCodename': 'oles-oi-tainies-1'}
        response = requests.get(INITIAL_LOAD_URL, params=initial_params, headers=HEADERS, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        section_content = data.get('SectionContent', {})
        toplist_codename = section_content.get('ToplistCodename')
        
        if not toplist_codename:
            print("Μοιραίο σφάλμα: Δεν βρέθηκε ToplistCodename. Αδύνατη η συνέχιση.")
            return []
            
        print(f"  -> Επιτυχία! Ο κωδικός λίστας είναι: '{toplist_codename}'")

    except requests.exceptions.RequestException as e:
        print(f"Σφάλμα κατά τη λήψη του κωδικού λίστας: {e}")
        return []

    # --- ΒΗΜΑ 2: ΛΗΨΗ ΟΛΩΝ ΤΩΝ ΣΕΛΙΔΩΝ ΜΕ ΤΟ ΣΩΣΤΟ API ---
    print("\n--- Φάση 2: Έναρξη λήψης όλων των σελίδων ταινιών ---")
    current_page = 1
    while True:
        print(f"Λήψη σελίδας {current_page}...")
        # Χρησιμοποιούμε το σωστό API και τον κωδικό που βρήκαμε
        page_params = {'platformCodename': 'www', 'toplistCodename': toplist_codename, 'page': current_page}
        
        try:
            response = requests.get(PAGINATION_API_URL, params=page_params, headers=HEADERS, timeout=20)
            response.raise_for_status()
            data = response.json()
            
            # Αυτό το API επιστρέφει πλήρη στοιχεία στο 'Tiles'
            new_tiles = data.get('Tiles', [])
            
            if not new_tiles:
                print(f"Η σελίδα {current_page} είναι κενή. Ολοκληρώθηκε η λήψη.")
                break
            
            all_movies_data.extend(new_tiles)
            print(f"  -> Βρέθηκαν {len(new_tiles)} ταινίες. Σύνολο μέχρι στιγμής: {len(all_movies_data)}")
            
            current_page += 1
            time.sleep(0.2)

        except requests.exceptions.RequestException as e:
            print(f"Σφάλμα κατά τη λήψη της σελίδας {current_page}: {e}. Διακοπή.")
            break
            
    return all_movies_data

def main():
    final_playlist = []
    
    # Το fetch_all_movies πλέον επιστρέφει τα πάντα (τίτλους, codenames, αφίσες)
    all_movies_with_details = fetch_all_movies()
    
    if not all_movies_with_details:
        print("\nΔεν βρέθηκαν ταινίες για επεξεργασία.")
        return

    total_movies = len(all_movies_with_details)
    print(f"\n--- Φάση 3: Έναρξη επεξεργασίας {total_movies} ταινιών για λήψη stream URL ---")

    for index, tile in enumerate(all_movies_with_details):
        codename = tile.get('Codename')
        title = tile.get('Title', codename or "Unknown Title").strip()
        
        if not codename:
            continue
            
        print(f"Επεξεργασία {index + 1}/{total_movies}: {title}")

        try:
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
                poster_url = tile.get('Poster', "")
                final_playlist.append({'title': title, 'stream_url': stream_url, 'poster_url': poster_url})
                print(f"  -> Επιτυχία!")
            else:
                print(f"  -> Δεν βρέθηκε stream.")
        except Exception as e:
            print(f"  -> Σφάλμα: {e}")
        
        time.sleep(0.05)

    # --- Φάση 4: Δημιουργία του τελικού αρχείου ---
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
