import requests

# === Ρυθμίσεις ===
API_URL = "https://api.app.ertflix.gr/v2/Tile/GetTiles"
HEADERS = {
    "Content-Type": "application/json;charset=utf-8",
    "X-Api-Date-Format": "iso",
    "X-Api-Camel-Case": "true"
}
PAYLOAD = {
    "pageCodename": "movies",
    "sectionCodename": "oles-oi-tainies-1",
    "tileCount": 300
}
OUTPUT_FILE = "ertflix_playlist.m3u8"

# === Κύρια Συνάρτηση ===
def fetch_movies():
    print("🔄 Fetching data from ERTFLIX API...")
    try:
        response = requests.post(API_URL, headers=HEADERS, json=PAYLOAD, timeout=30)
        response.raise_for_status()
        movies = response.json().get("tiles", [])
        print(f"✅ Found {len(movies)} items.")
        return movies
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def build_playlist(movies):
    entries = []
    for movie in movies:
        try:
            # Φιλτράρουμε μόνο ταινίες (όχι επεισόδια)
            if movie.get("isEpisode") or movie.get("type") != "vod":
                continue

            title = movie.get("title", "Unknown Title")
            m3u8_url = ""
            logo_url = ""

            # Βρίσκουμε το m3u8
            for media in movie.get("mediaFiles", []):
                for fmt in media.get("formats", []):
                    if fmt.get("url", "").endswith(".m3u8"):
                        m3u8_url = fmt["url"]
                        break
                if m3u8_url:
                    break

            # Poster εικόνα
            for img in movie.get("images", []):
                if img.get("role") == "poster":
                    logo_url = img.get("url")
                    break

            # Δημιουργία γραμμής playlist
            if all([title, m3u8_url, logo_url]):
                entry = f'#EXTINF:-1 tvg-logo="{logo_url}",{title}\n{m3u8_url}'
                entries.append(entry)
                print(f"🎬 Added: {title}")

        except Exception:
            continue

    return entries

def save_playlist(entries):
    print(f"\n💾 Writing playlist to '{OUTPUT_FILE}'...")
    content = "#EXTM3U\n\n" + "\n\n".join(entries)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"🏁 Finished: {len(entries)} movies saved.")

# === Εκτέλεση ===
if __name__ == "__main__":
    movies = fetch_movies()
    playlist = build_playlist(movies)
    save_playlist(playlist)
