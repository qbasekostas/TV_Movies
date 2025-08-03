import requests
import time
import json

# API Endpoints
LIST_API_URL = "https://api.app.ertflix.gr/v1/InsysGoPage/GetSectionContent"
PLAYER_API_URL = "https://api.app.ertflix.gr/v1/Player/AcquireContent"

# Σταθερές
DEVICE_KEY = "12b9a6425e59ec1fcee9acb0e7fba4f3"
OUTPUT_FILE = "ertflix_playlist.m3u8"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def fetch_all_movies():
    """
    Κάνει κλήση στο API σε βρόχο, ανιχνεύοντας τις επαναλαμβανόμενες σελίδες
    για να σταματήσει με ασφάλεια όταν τελειώσουν οι μοναδικές ταινίες.
    """
    all_movies_data = []
    seen_codenames = set() # Set για να αποθηκεύουμε τα codenames που έχουμε δει
    current_page = 1

    print("Έναρξη λήψης ταινιών (με ανίχνευση επανάληψης)...")

    while True:
        print(f"Λήψη σελίδας {current_page}...")
        params = {'platformCodename': 'www', 'sectionCodename': 'oles-oi-tainies-1', 'page': current_page}
        
        try:
            response = requests.get(LIST_API_URL, params=params, headers=HEADERS, timeout=20)
            response.raise_for_status()
            data = response.json()

            section_content = data.get('SectionContent', {})
            tiles = section_content.get('Tiles') or section_content.get('TilesIds')
            
            # Αν η σελίδα είναι κενή, σταματάμε (ασφαλής έλεγχος)
            if not tiles:
                print(f"Η σελίδα {current_page} είναι κενή. Ολοκληρώθηκε η λήψη.")
                break

            # Παίρνουμε το codename της πρώτης ταινίας στη νέα σελίδα
            first_tile_codename = tiles[0].get('Codename') or tiles[0].get('codename')

            # Αν έχουμε ξαναδεί αυτό το codename, σημαίνει ότι το API επαναλαμβάνεται. Σταματάμε.
            if first_tile_codename in seen_codenames:
                print(f"Εντοπίστηκε επανάληψη στη σελίδα {current_page}. Ολοκληρώθηκε η λήψη.")
                break
            
            # Προσθέτουμε τις νέες, μοναδικές ταινίες στη λίστα και τα codenames στο set
            new_movies_on_page = []
            for tile in tiles:
                codename = tile.get('Codename') or tile.get('codename')
                if codename not in seen_codenames:
                    seen_codenames.add(codename)
                    new_movies_on_page.append(tile)

            all_movies_data.extend(new_movies_on_page)
            print(f"  -> Βρέθηκαν {len(new_movies_on_page)} νέες ταινίες. Σύνολο: {len(all_movies_data)}")
            
            current_page += 1
            time.sleep(0.2) 

        except requests.exceptions.RequestException as e:
            print(f"Σφάλμα κατά τη λήψη της σελίδας {current_page}: {e}. Διακοπή.")
            break 

    print(f"\nΟλοκληρώθηκε η λήψη. Συνολικά βρέθηκαν {len(all_movies_data)} μοναδικές ταινίες.")
    return all_movies_data

def main():
    final_movies_list = []
    all_movies_data = fetch_all_movies()
    
    if not all_movies_data:
        print("Δεν βρέθηκαν ταινίες για επεξεργασία.")
        return

    total_movies = len(all_movies_data)
    print(f"\nΒήμα 2: Έναρξη επεξεργασίας {total_movies} ταινιών...")

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
