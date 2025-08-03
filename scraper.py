import requests
import json

API_URL = "https://api.app.ertflix.gr/v2/Tile/GetTiles"
OUTPUT_FILE = "ertflix_playlist.m3u8"

HEADERS = {
    "Content-Type": "application/json;charset=utf-8",
    "X-Api-Date-Format": "iso",
    "X-Api-Camel-Case": "true",
    "User-Agent": "Mozilla/5.0"
}

# Αντικατέστησε αν θέλεις με άλλον κωδικό κατηγορίας
MOVIES_SECTION_CODENAME = "oles-oi-tainies-1"

def fetch_movies():
    """ Fetch all movies from ERTFLIX API """
    payload = {
        "spaceCodename": "ext",
        "platformCodename": "www",
        "sectionCodename": MOVIES_SECTION_CODENAME,
        "tileCount": 300  # Μέγιστο που επιτρέπει το API
    }
    resp = requests.post(API_URL, headers=HEADERS, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("tiles", [])

def extract_movie_info(tile):
    """ Extract title, poster image, and m3u8 url for a movie """
    title = tile.get("title")
    poster = ""
    m3u8_url = ""
    for img in tile.get("images", []):
        if img.get("role", "").lower() == "poster":
            poster = img.get("url")
            break
    for mf in tile.get("mediaFiles", []):
        for fmt in mf.get("formats", []):
            url = fmt.get("url", "")
            if url.endswith(".m3u8"):
                m3u8_url = url
                break
        if m3u8_url:
            break
    return title, poster, m3u8_url

def main():
    print("Fetching movies from ERTFLIX...")
    try:
        tiles = fetch_movies()
    except Exception as e:
        print(f"ERROR: {e}")
        return

    playlist_entries = []
    for tile in tiles:
        title, poster, m3u8_url = extract_movie_info(tile)
        if title and poster and m3u8_url:
            print(f"Found: {title}")
            entry = f'#EXTINF:-1 tvg-logo="{poster}",{title}\n{m3u8_url}'
            playlist_entries.append(entry)
        else:
            print(f"Skipped: {title} (missing data)")

    print(f"\nWriting playlist file ({OUTPUT_FILE}) ...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n\n" + "\n\n".join(playlist_entries))

    print(f"Done. Created playlist with {len(playlist_entries)} movies.")

if __name__ == "__main__":
    main()
