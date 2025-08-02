import requests

API_URL = "https://api.app.ertflix.gr/v2/Tile/GetTiles"
OUTPUT_FILE = "ertflix_playlist.m3u8"

HEADERS = {
    "Content-Type": "application/json;charset=utf-8",
    "X-Api-Date-Format": "iso",
    "X-Api-Camel-Case": "true"
}

PAYLOAD = {
    "pageCodename": "movies",
    "sectionCodename": "oles-oi-tainies-1",
    "tileCount": 300,
    "platformCodename": "www"
}

def fetch_movies():
    print("📡 Connecting to ERTFLIX API...")
    try:
        response = requests.post(API_URL, headers=HEADERS, json=PAYLOAD, timeout=20)
        response.raise_for_status()
        return response.json().get("tiles", [])
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def extract_entries(tiles):
    playlist = []
    for movie in tiles:
        try:
            if movie.get("isEpisode") or movie.get("type") != "vod":
                continue

            title = movie.get("title", "Untitled")
            stream = ""
            logo = ""

            # βρες stream .m3u8
            for media in movie.get("mediaFiles", []):
                for fmt in media.get("formats", []):
                    if fmt.get("url", "").endswith(".m3u8"):
                        stream = fmt["url"]
                        break
                if stream:
                    break

            # βρες poster εικόνα
            for img in movie.get("images", []):
                if img.get("role") == "poster":
                    logo = img.get("url")
                    break

            if stream and logo:
                entry = f'#EXTINF:-1 tvg-logo="{logo}",{title}\n{stream}'
                playlist.append(entry)
                print(f"🎬 Added: {title}")

        except Exception:
            continue

    return playlist

def save_playlist(entries):
    print(f"\n💾 Saving playlist to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n\n" + "\n\n".join(entries))
    print(f"✅ Done: {len(entries)} entries written.")

if __name__ == "__main__":
    movies = fetch_movies()
    playlist = extract_entries(movies)
    save_playlist(playlist)
