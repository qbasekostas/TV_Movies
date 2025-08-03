import requests
import time

# Ενότητες API
TILES_URL = "https://api.app.ertflix.gr/v2/Tile/GetTiles"
PLAYER_API_URL = "https://api.app.ertflix.gr/v1/Player/AcquireContent"

# Σταθερές
DEVICE_KEY = "12b9a6425e59ec1fcee9acb0e7fba4f3"
OUTPUT_FILE = "ertflix_playlist.m3u8"

HEADERS = {
    "Content-Type": "application/json;charset=utf-8",
    "X-Api-Date-Format": "iso",
    "X-Api-Camel-Case": "true",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

def fetch_all_tiles():
    all_tiles = []
    offset = 0
    batch_size = 100

    print("📡 Λήψη όλων των tiles...")
    while True:
        payload = {
            "PlatformCodename": "www",
            "SectionCodename": "oles-oi-tainies-1",
            "From": offset,
            "Size": batch_size
        }
        try:
            response = requests.post(TILES_URL, headers=HEADERS, json=payload, timeout=30)
            if response.status_code == 404:
                print("❌ 404 Not Found - πιθανό λάθος στα headers ή στο body.")
                break

            response.raise_for_status()
            data = response.json()
            tiles = data.get("Tiles", [])
            if not tiles:
                break

            all_tiles.extend(tiles)
            print(f"✅ Σετ από {len(tiles)} tiles (offset: {offset})")
            offset += batch_size
            time.sleep(0.2)
        except Exception as e:
            print(f"❌ Σφάλμα στο fetch: {e}")
            break

    print(f"\n🎉 Βρέθηκαν συνολικά {len(all_tiles)} ταινίες.\n")
    return all_tiles

def get_stream_url(codename):
    try:
        params = {
            "platformCodename": "www",
            "deviceKey": DEVICE_KEY,
            "codename": codename,
            "t": int(time.time() * 1000)
        }
        r = requests.get(PLAYER_API_URL, params=params, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
        for media_file in data.get("MediaFiles", []):
            for fmt in media_file.get("Formats", []):
                url = fmt.get("Url", "")
                if url.endswith(".m3u8"):
                    return url
    except:
        pass
    return None

def main():
    tiles = fetch_all_tiles()
    if not tiles:
        print("🚫 Δεν βρέθηκαν ταινίες.")
        return

    movies = []

    for i, tile in enumerate(tiles, 1):
        codename = tile.get("Codename")
        title = tile.get("Title") or codename
        print(f"[{i}/{len(tiles)}] Επεξεργασία: {title}...", end=" ")

        stream_url = get_stream_url(codename)
        if stream_url:
            print("✅")
            movies.append((title, stream_url))
        else:
            print("❌")

        time.sleep(0.05)

    if not movies:
        print("⚠ Δεν βρέθηκαν έγκυρα streams.")
        return

    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for title, url in movies:
                f.write(f"#EXTINF:-1,{title}\n{url}\n")
        print(f"\n💾 Το αρχείο '{OUTPUT_FILE}' δημιουργήθηκε με {len(movies)} ταινίες!")
    except IOError as e:
        print(f"❌ Σφάλμα αποθήκευσης: {e}")

if __name__ == "__main__":
    main()
