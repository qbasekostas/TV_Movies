import requests
import time
import json

# API Endpoints
INITIAL_LOAD_URL = "https://api.app.ertflix.gr/v1/InsysGoPage/GetSectionContent" # Για την πρώτη σελίδα
INFINITE_SCROLL_URL = "https://api.app.ertflix.gr/v1/toplist/GetToplistPage"  # Για όλες τις επόμενες

# Σταθερές
DEVICE_KEY = "12b9a6425e59ec1fcee9acb0e7fba4f3"
PLAYER_API_URL = "https://api.app.ertflix.gr/v1/Player/AcquireContent"
OUTPUT_FILE = "ertflix_playlist.m3u8"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def fetch_all_movies():
    """
    Μιμείται τη λειτουργία του "infinite scroll" του ertflix.gr, καλώντας δύο διαφορετικά API.
    """
    all_movies_data = []
    
    # --- ΒΗΜΑ 1: ΛΗΨΗ ΤΗΣ ΠΡΩΤΗΣ ΣΕΛΙΔΑΣ ---
    print("Βήμα 1: Λήψη πρώτης σελίδας (αρχικό φόρτωμα)...")
    try:
        initial_params = {'platformCodename': 'www', 'sectionCodename': 'oles-oi-tainies-1'}
        response = requests.get(INITIAL_LOAD_URL, params=initial_params, headers=HEADERS, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        section_content = data.get('SectionContent', {})
        
        # Προσθήκη των πρώτων ταινιών στη λίστα
        initial_tiles = section_content.get('Tiles') or section_content.get('TilesIds', [])
        all_movies_data.extend(initial_tiles)
        
        # ΕΞΑΓΩΓΗ ΤΟΥ ΚΡΙΣΙΜΟΥ ToplistCodename ΓΙΑ ΤΟ SCROLL
        toplist_codename = section_content.get('ToplistCodename')
        if not toplist_codename:
            print("Προειδοποίηση: Δεν βρέθηκε ToplistCodename. Θα ληφθεί μόνο η πρώτη σελίδα.")
            return all_movies_data
            
        print(f"  -> Βρέθηκαν {len(initial_tiles)} ταινίες. Εξαγωγή κωδικού λίστας: '{toplist_codename}'")

    except requests.exceptions.RequestException as e:
        print(f"Σφάλμα κατά τη λήψη της πρώτης σελίδας: {e}")
        return []

    # --- ΒΗΜΑ 2: ΛΗΨΗ ΤΩΝ ΥΠΟΛΟΙΠΩΝ ΣΕΛΙΔΩΝ (SCROLL) ---
    print("\nΒήμα 2: Έναρξη λήψης υπόλοιπων σελίδων (προσομοίωση scroll)...")
    current_page = 2
    while True:
        print(f"Λήψη σελίδας {current_page}...")
        scroll_params = {
            'platformCodename': 'www',
            'toplistCodename': toplist_codename,
            'page': current_page
        }
        
        try:
            response = requests.get(INFINITE_SCROLL_URL, params=scroll_params, headers=HEADERS, timeout=20)
            response.raise_for_status()
            data = response.json()
            
            new_tiles = data.get('Tiles', [])
            
            # Αν η σελίδα δεν έχει ταινίες, τελειώσαμε.
            if not new_tiles:
                print(f"Η σελίδα {current_page} είναι κενή. Ολοκληρώθηκε το scroll.")
                break
            
            all_movies_data.extend(new_tiles)
            print(f"  -> Βρέθηκαν {len(new_tiles)} νέες ταινίες. Σύνολο μέχρι στιγμής: {len(all_movies_data)}")
            
            current_page += 1
            time.sleep(0.2)

        except requests.exceptions.RequestException as e:
            print(f"Σφάλμα κατά τη λήψη της σελίδας {current_page}: {e}. Διακοπή.")
            break
            
    return all_movies_data

def main():
    final_movies_list = []
    
    # Το fetch_all_movies πλέον κάνει όλη τη μαγεία
    all_movies_data = fetch_all_movies()
    
    if not all_movies_data:
        print("\nΔεν βρέθηκαν ταινίες για επεξεργασία.")
        return

    total_movies = len(all_movies_data)
    print(f"\nΒήμα 3: Έναρξη επεξεργασίας {total_movies} ταινιών για λήψη stream URL...")

    for index, tile in enumerate(all_movies_data):
        codename = tile.get('Codename') or tile.get('codename')
        title = tile.get('Title') or codename or "Unknown Title"
        poster_url = tile.get('Poster') or ""

        if not codename:
            continue
            
        print(f"Επεξεργασία {index + 1}/{total_movies}: {title.strip()}")

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
                final_movies_list.append({'title': title.strip(), 'stream_url': stream_url, 'poster_url': poster_url})
                print(f"  -> Επιτυχία!")
            else:
                print(f"  -> Δεν βρέθηκε stream.")
        except Exception as e:
            print(f"  -> Σφάλμα: {e}")
        
        time.sleep(0.05)

    if not final_movies_list:
        print("\nΗ διαδικασία ολοκληρώθηκε, αλλά δεν βρέθηκαν ταινίες με έγκυρο stream.")
        return

    # Δημιουργία του τελικού αρχείου
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
