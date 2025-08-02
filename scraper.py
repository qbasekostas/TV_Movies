import requests

# === Ρυθμίσεις ===
API_URL = "https://api.app.ertflix.gr/v2/Tile/GetTiles"
HEADERS = {
    "Content-Type": "application/json;charset=utf-8",
    "X-Api-Date-Format": "iso",
    "X-Api-Camel-Case": "true"
}
PAYLOAD = {
    "platformCodename": "www",
    "requestedTiles": [
        {"id": "chn.150403"},
        {"id": "chn.427302"},
        {"id": "chn.21"},
        {"id": "chn.22"},
        {"id": "chn.131978"},
        {"id": "chn.164800"},
        {"id": "chn.164802"},
        {"id": "chn.451846"},
        {"id": "chn.332984"},
        {"id": "chn.131980"},
        {"id": "chn.335937"},
        {"id": "chn.363284"},
        {"id": "chn.307498"},
        {"id": "chn.308550"},
        {"id": "chn.417558"},
        {"id": "chn.229023"},
        {"id": "chn.229024"},
        {"id": "chn.229026"},
        {"id": "chn.262163"},
        {"id": "chn.229025"},
        {"id": "chn.233893"},
        {"id": "chn.229022"},
        {"id": "chn.229027"},
        {"id": "chn.229028"},
        {"id": "chn.229029"},
    ]
}
OUTPUT_FILE = "ertflix_playlist.m3u8"

def fetch_tiles():
    print("📡 Requesting data from ERTFLIX API...")
    try:
        response = requests.post(API_URL, headers=HEADERS, json=PAYLOAD, timeout=30)
        response.raise_for_status()
        return response.json().get("tiles", [])
    except Exception as e:
        print(f"❌ API error: {e}")
        return []

def build_playlist(tiles):
    playlist_entries = []
    for tile in tiles:
        try:
            title = tile.get("title", "Unknown Title")
            m3u8_url = ""
            poster_url = ""

            # Βρες stream
            for media_file in tile.get("mediaFiles", []):
                for fmt in media_file.get("formats", []):
                    if fmt.get("url", "").endswith(".m3u8"):
                        m3u8_url = fmt["url"]
                        break
                if m3u8_url:
                    break

            # Βρες εικόνα
            for img in tile.get("images", []):
                if img.get("role") == "poster":
                    poster_url = img.get("url")
                    break

            if m3u8_url and poster_url:
                entry = f'#EXTINF:-1 tvg-logo="{poster_url}",{title}\n{m3u8_url}'
                playlist_entries.append(entry)
                print(f"🎞️ Added: {title}")
        except Exception:
            continue
    return playlist_entries

def save_playlist(entries):
    print(f"\n💾 Saving to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n\n" + "\n\n".join(entries))
    print(f"🏁 Done! {len(entries)} entries written.")

# === Εκτέλεση ===
if __name__ == "__main__":
    tiles = fetch_tiles()
    playlist = build_playlist(tiles)
    save_playlist(playlist)
