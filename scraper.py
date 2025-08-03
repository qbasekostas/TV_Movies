import requests
import time
import json

# --- API Endpoints ---
# Το ΜΟΝΑΔΙΚΟ API που χρειαζόμαστε για τη λίστα, όπως αποδείχθηκε.
LIST_API_URL = "https://api.app.ertflix.gr/v1/InsysGoPage/GetSectionContent"
# Τα APIs για τις λεπτομέρειες και το stream παραμένουν τα ίδια.
TILE_DETAIL_API_URL = "https://api.app.ertflix.gr/v1/tile/GetTile"
PLAYER_API_URL = "https://api.app.ertflix.gr/v1/Player/AcquireContent"

# --- Σταθερές ---
DEVICE_KEY = "12b9a6425e59ec1fcee9acb0e7fba4f3"
OUTPUT_FILE = "ertflix_playlist.m3u8"
# Ο αριθμός των ταινιών που θα ζητάμε σε κάθε κλήση.
BATCH_SIZE = 100
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def fetch_all_movies():
    """
    Παίρνει όλες τις ταινίες χρησιμοποιώντας τη μέθοδο offset/tileCount.
    """
    all_movies_data = []
    current_offset = 0

    print("Έναρξη λήψης ταινιών (Μέθοδος Offset/Batch)...")

    while True:
        print(f"Λήψη batch ταινιών με offset: {current_offset}...")
        
        params = {
            'platformCodename': 'www',
            'sectionCodename': 'oles-oi-tainies-1',
            'tileCount': BATCH_SIZE,
            'offset': current_offset
        }
        
        try:
            response = requests.get(LIST_API_URL, params=params, headers=HEADERS, timeout=20)
            response.raise_for_status()
            data = response.json()

            section_content = data.get('SectionContent', {})
            new_tiles = section_content.get('Tiles') or section_content.get('TilesIds', [])
            
            # Αν το API επιστρέψει κενή λίστα, τελειώσαμε.
            if not new_tiles:
                print(f"Το API επέστρεψε κενή λίστα. Ολοκληρώθηκε η λήψη.")
                break
            
            all_movies_data.extend(new_tiles)
            print(f"  -> Βρέθηκαν {len(new_tiles)} ταινίες. Σύνολο μέχρι στιγμής: {len(all_movies_data)}")
            
            # Αυξάνουμε το offset για την επόμενη κλήση.
            current_offset += BATCH_SIZE
            time.sleep(0.2) 

        except requests.exceptions.RequestException as e:
            print(f"Σφάλμα κατά τη λήψη του batch με offset {current_offset}: {e}. Διακοπή.")
            break 

    print(f"\nΟλοκληρώθηκε η λήψη. Συνολικά βρέθηκαν {len(all_movies_data)} εγγραφές ταινιών.")
    return all_movies_data

def main():
    final_movies_list = []
    
    # Βήμα 1: Λήψη ΟΛΩΝ των ταινιών
    all_movies_data = fetch_all_movies()
    
    if not all_movies_data:
        print("\nΔεν βρέθηκαν ταινίες για επεξεργασία.")
        return

    total_movies = len(all_movies_data)
    print(f"\nΒήμα 2: Έναρξη επεξεργασίας {total_movies} ταινιών...")

    for index, tile in enumerate(all_movies_data):
        codename = tile.get('Codename') or tile.get('codename')
        
        # Ο τίτλος και η αφίσα από την αρχική κλήψη, αν υπάρχουν
        title = tile.get('Title') or codename or "Unknown Title"
        poster_url = tile.get('Poster') or ""

        if not codename:
            continue
            
        print(f"Επεξεργασία {index + 1}/{total_movies}: {title.strip()}")

        try:
            # Αν η αρχική κλήση δεν είχε τίτλο, κάνουμε μια επιπλέον κλήση για λεπτομέρειες
            if title == codename:
                detail_params = {'platformCodename': 'www', 'codename': codename}
                detail_resp = requests.get(TILE_DETAIL_API_URL, params=detail_params, headers=HEADERS, timeout=10)
                if detail_resp.status_code == 200:
                    detail_data = detail_resp.json()
                    title = detail_data.get('Title', codename).strip()
                    poster_url = detail_data.get('Poster', poster_url)

            # Λήψη του stream URL
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
                final_movies_list.append({'title': title, 'stream_url': stream_url, 'poster_url': poster_url})
                print(f"  -> Επιτυχία!")
            else:
                print(f"  -> Δεν βρέθηκε stream.")
        except Exception as e:
            print(f"  -> Σφάλμα: {e}")
        
        time.sleep(0.05)

    if not final_movies_list:
        print("\nΗ διαδικασία ολοκληρώθηκε, αλλά δεν βρέθηκαν ταινίες με έγκυρο stream.")
        return

    # Βήμα 3: Δημιουργία του αρχείου M3U
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
