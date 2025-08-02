import requests
import os
import json
import re

# ΒΗΜΑ 1: Από εδώ παίρνουμε τα IDs
INITIAL_PAGE_URL = "https://www.ertflix.gr/list?pageCodename=movies&backUrl=/show/movies&sectionCodename=oles-oi-tainies-1&tileCount=300"
# ΒΗΜΑ 2: Εδώ στέλνουμε τα IDs για να πάρουμε τα πάντα
API_DETAILS_URL = "https://api.app.ertflix.gr/v2/Tile/GetTiles"

OUTPUT_FILE = "ertflix_playlist.m3u8"

# Γενικά Headers για την πρώτη κλήση
GENERAL_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Ειδικά Headers για την κλήση του API, όπως τα δώσατε
API_HEADERS = {
    "Content-Type": "application/json;charset=utf-8",
    "X-Api-Date-Format": "iso",
    "X-Api-Camel-Case": "true"
}

def get_movie_ids_from_page():
    print(f"Step 1: Fetching page to get movie IDs from: {INITIAL_PAGE_URL}")
    try:
        response = requests.get(INITIAL_PAGE_URL, headers=GENERAL_HEADERS, timeout=30)
        response.raise_for_status()
        
        match = re.search(r'<script>var ___INITIAL_STATE__ = (\{.*?\});<\/script>', response.text)
        if not match:
            print("  -> FATAL: Could not find the ___INITIAL_STATE___ data block.")
            return []
            
        initial_data = json.loads(match.group(1))
        # Εκτύπωσε όλο το JSON για να δεις τη δομή
        with open("ertflix_initial_data.json", "w", encoding="utf-8") as f:
    json.dump(initial_data, f, indent=2, ensure_ascii=False)
print("Αποθηκεύτηκε το αρχικό JSON στο ertflix_initial_data.json")

        components = initial_data.get('bootstrap', {}).get('page', {}).get('data', {}).get('components', [])
        movie_ids = []
        for comp in components:
            if 'tiles' in comp:
                movie_ids += [tile.get('id') for tile in comp.get('tiles', []) if tile.get('id')]
        if movie_ids:
            print(f"  -> SUCCESS: Found {len(movie_ids)} movie IDs.")
            return movie_ids
        
        print("  -> FAILURE: Could not find the movie list inside the initial data.")
        return []

    except Exception as e:
        print(f"  -> ERROR during Step 1: {e}")
        return []

def get_movies_details(movie_ids):
    """Παίρνει τις πλήρεις λεπτομέρειες (και τα m3u8) στέλνοντας τα IDs με τα σωστά headers."""
    print(f"Step 2: Fetching full details for {len(movie_ids)} movies...")
    
    payload = {
        "platformCodename": "www",
        "requestedTiles": [{"id": mid} for mid in movie_ids]
    }
    
    try:
        response = requests.post(API_DETAILS_URL, headers=API_HEADERS, json=payload, timeout=45)
        response.raise_for_status()
        data = response.json()
        
        if 'tiles' in data:
            print(f"  -> SUCCESS: Received details for {len(data['tiles'])} movies.")
            return data['tiles']
        else:
            print("  -> FAILURE: Response did not contain 'tiles' key.")
            return []
            
    except requests.RequestException as e:
        print(f"  -> ERROR during Step 2: {e}")
        return []

def main():
    """Κύρια συνάρτηση του script."""
    playlist_entries = []
    
    movie_ids = get_movie_ids_from_page()
    
    if movie_ids:
        movies_data = get_movies_details(movie_ids)
        
        for movie in movies_data:
            try:
                title = movie.get('title')
                image_url = ""
                m3u8_url = None

                for img in movie.get('images', []):
                    if img.get('role') == 'poster':
                        image_url = img.get('url')
                        break
                
                if movie.get('mediaFiles'):
                    for media_file in movie.get('mediaFiles', []):
                        for fmt in media_file.get('formats', []):
                            if fmt.get('url', '').endswith('.m3u8'):
                                m3u8_url = fmt['url']
                                break
                        if m3u8_url:
                            break
                
                if all([title, image_url, m3u8_url]):
                    print(f"  -> Found: {title}")
                    entry = f'#EXTINF:-1 tvg-logo="{image_url}",{title}\n{m3u8_url}'
                    playlist_entries.append(entry)
                else:
                    print(f"  -> Skipped '{title}' (missing essential data).")

            except (KeyError, IndexError, TypeError):
                print(f"  -> Skipped an item due to unexpected data structure.")
                continue

    print(f"\nCreating playlist file '{OUTPUT_FILE}'...")
    playlist_content = "#EXTM3U\n\n" + "\n\n".join(playlist_entries)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(playlist_content)
        
    print(f"\n>>>>>>>>> Finished. Created playlist with {len(playlist_entries)} movies. <<<<<<<<<")

if __name__ == "__main__":
    main()
