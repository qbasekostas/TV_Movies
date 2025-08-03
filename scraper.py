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

# Header parameter για το API της λίστας σελίδων (Pagination)
PAGINATION_HEADERS_PARAM = json.dumps({
    "X-Api-Date-Format": "iso",
    "X-Api-Camel-Case": "true"
})

# ΔΙΟΡΘΩΣΗ: Ξεχωριστό και πλήρες header parameter για το API λήψης λεπτομερειών (GetTiles)
# Αυτό περιλαμβάνει το "Content-Type" που απαιτεί το συγκεκριμένο endpoint
DETAILS_HEADERS_PARAM = json.dumps({
    "Content-Type": "application/json;charset=utf-8",
    "X-Api-Date-Format": "iso",
    "X-Api-Camel-Case": "true"
})


def fetch_all_movie_details():
    """
    Παίρνει τα IDs από κάθε σελίδα και μετά ζητά μαζικά τις λεπτομέρειες των ταινιών.
    """
    all_movies = []
    current_page = 1

    print("--- Φάση 1: Συλλογή IDs και Λεπτομερειών ανά σελίδα ---")
    while True:
        print(f"Λήψη σελίδας {current_page}...")

        page_params = {
            'platformCodename': 'www',
            'sectionCodename': 'oles-oi-tainies-1',
            'page': current_page,
            'limit': 40,
            'ignoreLimit': 'false',
            '$headers': PAGINATION_HEADERS_PARAM
        }

        try:
            response = requests.get(PAGINATION_URL, params=page_params, headers=HEADERS, timeout=20)
            response.raise_for_status()
            page_data = response.json()

            section_content = page_data.get('SectionContent', {})
            tiles_with_ids = section_content.get('TilesIds', [])

            if not tiles_with_ids:
                print(f"Η σελίδα {current_page} είναι κενή. Ολοκληρώθηκε η συλλογή.")
                break

            ids_to_fetch = [tile['Id'] for tile in tiles_with_ids if 'Id' in tile]
            print(f"  -> Βρέθηκαν {len(ids_to_fetch)} IDs. Γίνεται λήψη των λεπτομερειών τους...")

            if ids_to_fetch:
                details_payload = {"ids": ids_to_fetch}
                # Χρησιμοποιούμε το νέο, διορθωμένο header parameter εδώ
                details_params = {'$headers': DETAILS_HEADERS_PARAM}
                details_response = requests.post(TILE_DETAILS_URL, params=details_params, json=details_payload, headers=HEADERS, timeout=20)

                if details_response.status_code == 200:
                    detailed_tiles = details_response.json()
                    all_movies.extend(detailed_tiles)
                    print(f"  -> Επιτυχής λήψη λεπτομερειών. Σύνολο ταινιών μέχρι στιγμής: {len(all_movies)}")
                else:
                    print(f"  -> Σφάλμα κατά τη λήψη λεπτομερειών: {details_response.status_code}")

            if len(tiles_with_ids) < 40:
                print("Βρέθηκε η τελευταία σελίδα. Ολοκληρώθηκε η συλλογή.")
                break

            current_page += 1
            time.sleep(0.2) # Μικρή καθυστέρηση για να είμαστε καλοί με τον server

        except requests.exceptions.RequestException as e:
            print(f"Σφάλμα δικτύου κατά τη λήψη της σελίδας {current_page}: {e}. Διακοπή.")
            break

    return all_movies


def main():
    """
    Κύρια συνάρτηση που εκτελεί τη διαδικασία και γράφει το τελικό αρχείο.
    """
    # Βήμα 1: Λήψη όλων των ταινιών με τις λεπτομέρειές τους
    all_movies_with_details = fetch_all_movie_details()

    if not all_movies_with_details:
        print("\nΔεν βρέθηκαν ταινίες για επεξεργασία. Τερματισμός.")
        return

    final_playlist = []
    total_movies = len(all_movies_with_details)
    print(f"\n--- Φάση 2: Έναρξη επεξεργασίας {total_movies} ταινιών για λήψη stream URL ---")

    # Βήμα 2: Λήψη του stream URL για κάθε ταινία
    for index, tile in enumerate(all_movies_with_details):
        codename = tile.get('codename')
        title = tile.get('title', codename or "Unknown Title").strip()
        poster_url = tile.get('poster') or ""

        if not codename:
            continue

        print(f"Επεξεργασία {index + 1}/{total_movies}: {title}")

        try:
            player_params = {
                "platformCodename": "www",
                "deviceKey": DEVICE_KEY,
                "codename": codename,
                "t": int(time.time() * 1000)
            }
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
                print("  -> Επιτυχία!")
            else:
                print("  -> Δεν βρέθηκε stream URL (.m3u8).")

        except Exception as e:
            print(f"  -> Σφάλμα κατά τη λήψη του stream: {e}")

        time.sleep(0.05) # Πολύ μικρή καθυστέρηση

    # Βήμα 3: Δημιουργία του αρχείου M3U
    if not final_playlist:
        print("\nΔεν ήταν δυνατή η δημιουργία λίστας αναπαραγωγής, δεν βρέθηκαν έγκυρα streams.")
        return
        
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for movie in final_playlist:
                logo_tag = f'tvg-logo="{movie["poster_url"]}"' if movie["poster_url"] else ""
                info_line = f'#EXTINF:-1 {logo_tag},{movie["title"]}\n'
                url_line = f'{movie["stream_url"]}\n'
                f.write(info_line)
                f.write(url_line)
        print(f"\n✅ Το αρχείο {OUTPUT_FILE} δημιουργήθηκε με επιτυχία με {len(final_playlist)} ταινίες!")
    except IOError as e:
        print(f"\n❌ Σφάλμα εγγραφής στο αρχείο: {e}")


if __name__ == "__main__":
    main()
