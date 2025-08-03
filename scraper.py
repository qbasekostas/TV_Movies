import requests
import time
import json

# API URLs
LIST_API_URL = "https://api.app.ertflix.gr/v1/InsysGoPage/GetSectionContent"
PLAYER_API_URL = "https://api.app.ertflix.gr/v1/Player/AcquireContent"

DEVICE_KEY = "12b9a6425e59ec1fcee9acb0e7fba4f3"
OUTPUT_FILE = "ertflix_playlist.m3u8"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json",
    "X-Api-Date-Format": "iso",
    "X-Api-Camel-Case": "true"
}

def fetch_tiles():
    params = {
        "platformCodename": "www",
        "sectionCodename": "oles-oi-tainies-1"
    }
    try:
        r = requests.get(LIST_API_URL, params=params, headers=HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json()
        tiles = data.get("SectionContent", {}).get("TilesIds", [])
        print(f"🎯 Βρέθηκαν {len(tiles)} codename entries από το API.\n")
        return tiles
    except Exception as e:
        print(f"❌ Σφάλμα στο fetch: {e}")
        return []

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
    if not tiles:
        print("🚫 Δεν βρέθηκαν ταινίες.")
        return

    movies = []
    for i, tile in enumerate(tiles, 1):
        codename = tile.get("Codename") or tile.get("codename")
        if not codename:
            continue

        print(f"[{i}/{len(tiles)}] Αναζήτηση για: {codename}...", end=" ")
        stream = get_stream_url(codename)
        if stream:
            movies.append((codename, stream))
            print("✅")
        else:
            print("❌")

        time.sleep(0.05)

    if not movies:
        print("⚠ Δεν βρέθηκαν διαθέσιμα streams.")
        return

    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for title, url in movies:
                f.write(f"#EXTINF:-1,{title}\n{url}\n")
        print(f"\n💾 Το αρχείο '{OUTPUT_FILE}' δημιουργήθηκε με {len(movies)} ταινίες.")
    except IOError as e:
        print(f"❌ Σφάλμα εγγραφής: {e}")

if __name__ == "__main__":
    main()
