import requests
import time
import json
from tqdm import tqdm  # Αν δεν έχεις, κάνε pip install tqdm

# API Endpoints
LIST_API_URL = "https://api.app.ertflix.gr/v1/InsysGoPage/GetSectionContent"
PLAYER_API_URL = "https://api.app.ertflix.gr/v1/Player/AcquireContent"

# Σταθερές
DEVICE_KEY = "12b9a6425e59ec1fcee9acb0e7fba4f3"
OUTPUT_FILE = "ertflix_playlist.m3u8"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def get_all_tiles():
    page = 1
    limit = 40
    all_tiles = []

    print("📥 Λήψη όλων των ταινιών από το ERTFLIX...")
    while True:
        try:
            params = {
                "platformCodename": "www",
                "sectionCodename": "oles-oi-tainies-1",
                "page": page,
                "limit": limit,
                "ignoreLimit": "false"
            }
            r = requests.get(LIST_API_URL, params=params, headers=HEADERS, timeout=30)
            r.raise_for_status()
            data = r.json()
            tiles = data.get("SectionContent", {}).get("TilesIds", [])
            if not tiles:
                break
            all_tiles.extend(tiles)
            print(f"🔹 Σελίδα {page} → {len(tiles)} αποτελέσματα.")
            page += 1
            time.sleep(0.2)
        except Exception as e:
            print(f"❌ Σφάλμα στη σελίδα {page}: {e}")
            break

    print(f"✅ Σύνολο ταινιών: {len(all_tiles)}\n")
    return all_tiles

def get_stream_url(codename):
    try:
        player_params = {
            "platformCodename": "www",
            "deviceKey": DEVICE_KEY,
            "codename": codename,
            "t": int(time.time() * 1000)
        }
        r = requests.get(PLAYER_API_URL, params=player_params, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()

        if data.get("MediaFiles"):
            for media_file in data["MediaFiles"]:
                for fmt in media_file.get("Formats", []):
                    url = fmt.get("Url", "")
                    if url.endswith(".m3u8"):
                        return url
        return None
    except requests.exceptions.HTTPError as e:
        if e.response and e.response.status_code == 404:
            return None
        else:
            raise
    except Exception as e:
        print(f"⚠ Σφάλμα με codename {codename}: {e}")
        return None

def main():
    tiles = get_all_tiles()
    if not tiles:
        print("🚫 Δεν βρέθηκαν ταινίες.")
        return

    movies = []

    for tile in tqdm(tiles, desc="🎬 Επεξεργασία"):
        codename = tile.get('codename') or tile.get('Codename')
        if not codename:
            continue
        stream_url = get_stream_url(codename)
        if stream_url:
            movies.append((codename, stream_url))
        time.sleep(0.05)

    if not movies:
        print("❌ Δεν βρέθηκε stream για καμία ταινία.")
        return

    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for title, url in movies:
                f.write(f"#EXTINF:-1,{title}\n{url}\n")
        print(f"\n💾 Το αρχείο '{OUTPUT_FILE}' δημιουργήθηκε με {len(movies)} ταινίες!")
    except IOError as e:
        print(f"❌ Σφάλμα εγγραφής: {e}")

if __name__ == "__main__":
    main()
