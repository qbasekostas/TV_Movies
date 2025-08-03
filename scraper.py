import requests
import time

URL = "https://api.app.ertflix.gr/v1/Tile/GetTiles"
PLAYER_API_URL = "https://api.app.ertflix.gr/v1/Player/AcquireContent"
DEVICE_KEY = "12b9a6425e59ec1fcee9acb0e7fba4f3"
OUTPUT_FILE = "ertflix_playlist.m3u8"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "application/json",
    "Content-Type": "application/json;charset=utf-8",
    "X-Api-Date-Format": "iso",
    "X-Api-Camel-Case": "true"
}


def fetch_tiles():
    all_tiles = []
    offset = 0
    size = 100

    while True:
        payload = {
            "PlatformCodename": "www",
            "SectionCodename": "oles-oi-tainies-1",
            "From": offset,
            "Size": size
        }
        r = requests.post(URL, headers=HEADERS, json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        tiles = data.get("Tiles", [])
        if not tiles:
            break
        all_tiles.extend(tiles)
        print(f"✅ Fetched {len(tiles)} tiles (offset {offset})")
        offset += size
        time.sleep(0.2)

    print(f"\n🎉 Σύνολο ταινιών: {len(all_tiles)}\n")
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
    tiles = fetch_tiles()
    movies = []

    for tile in tiles:
        codename = tile.get("Codename")
        title = tile.get("Title") or codename
        stream_url = get_stream_url(codename)
        if stream_url:
            movies.append((title, stream_url))
        time.sleep(0.05)

    if not movies:
        print("❌ Δεν βρέθηκε καμία διαθέσιμη ταινία.")
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for title, url in movies:
            f.write(f"#EXTINF:-1,{title}\n{url}\n")

    print(f"\n💾 Το αρχείο '{OUTPUT_FILE}' δημιουργήθηκε με {len(movies)} ταινίες!")

if __name__ == "__main__":
    main()
