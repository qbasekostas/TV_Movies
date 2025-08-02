import requests
import os
import json

# =================================================================================
# ΟΡΙΣΤΙΚΗ ΛΥΣΗ: Ακολουθούμε τη διαδικασία 3 βημάτων που χρησιμοποιεί το ίδιο το ERTFlix.
# =================================================================================
# ΒΗΜΑ 1: Παίρνουμε τη δομή της σελίδας για να βρούμε το ID της λίστας ταινιών.
API_PAGE_URL = "https://api.app.ertflix.gr/v2/page/movies"
# ΒΗΜΑ 2: Χρησιμοποιούμε το ID της λίστας για να πάρουμε τα IDs των ταινιών.
API_LIST_TEMPLATE = "https://api.app.ertflix.gr/v2/list/{list_id}?page=0&tileCount=300"
# ΒΗΜΑ 3: Στέλνουμε τα IDs των ταινιών για να πάρουμε τις πλήρεις λεπτομέρειες.
API_DETAILS_URL = "https://api.app.ertflix.gr/v2/Tile/GetTiles"

OUTPUT_FILE = "ertflix_playlist.m3u8"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_movies_list_id():
    """Βρίσκει το δυναμικό ID της λίστας 'Όλες οι Ταινίες'."""
    print("Step 1: Fetching page structure to find the correct list ID...")
    try:
        response = requests.get(API_PAGE_URL, headers=HEADERS, timeout=20)
        response.raise_for_status()
        data = response.json()
        for component in data.get('data', {}).get('components', []):
            if component.get('title') in ['Όλες οι ταινίες', 'Όλες οι Ταινίες']:
                list_id = component.get('listId')
                if list_id:
                    print(f"  -> SUCCESS: Found List ID: {list_id}")
                    return list_id
        print("  -> FAILURE: Could not find 'Όλες οι ταινίες' component.")
        return None
    except requests.RequestException as e:
        print(f"  -> ERROR: {e}")
        return None

def get_movie_ids_from_list(list_id):
    """Παίρνει τα IDs των ταινιών από τη λίστα που βρήκαμε."""
    list_url = API_LIST_TEMPLATE.format(list_id=list_id)
    print(f"Step 2: Fetching movie IDs from list {list_id}...")
    try:
        response = requests.get(list_url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        data = response.json()
        movie_ids = [item['id'] for item in data.get('data', []) if 'id' in item]
        if movie_ids:
            print(f"  -> SUCCESS: Found {len(movie_ids)} movie IDs.")
            return movie_ids
        print("  -> FAILURE: No movie IDs found in the list response.")
        return []
    except requests.RequestException as e:
        print(f"  -> ERROR: {e}")
        return []

def get_movies_details(movie_ids):
    """Παίρνει τις πλήρεις λεπτομέρειες για μια λίστα από IDs."""
    print(f"Step 3: Fetching full details for {len(movie_ids)} movies...")
    payload = {"platformCodename": "www", "requestedTiles": [{"id": mid} for mid in movie_ids]}
    try:
        response = requests.post(API_DETAILS_URL, headers=HEADERS, json=payload, timeout=45)
        response.raise_for_status()
        data = response.json()
        if 'tiles' in data:
            print(f"  -> SUCCESS: Received details for {len(data['tiles'])} movies.")
            return data['tiles']
        print("  -> FAILURE: 'tiles' key not found in the response.")
        return []
    except requests.RequestException as e:
        print(f"  -> ERROR: {e}")
        return []

def main():
    """Κύρια συνάρτηση του script."""
    playlist_entries = []
    
    list_id = get_movies_list_id()
    if list_id:
        movie_ids = get_movie_ids_from_list(list_id)
        if movie_ids:
            movies_data = get_movies_details(movie_ids)
            
            for movie in movies_data:
                try:
                    title = movie['title']
                    image_url = ""
                    # Βρίσκουμε μια κατάλληλη εικόνα (poster ή photo)
                    for img in movie.get('images', []):
                        if img.get('role') == 'poster' or img.get('role') == 'photo':
                            image_url = img.get('url')
                            break
                    
                    m3u8_url = None
                    # Βρίσκουμε το m3u8 link μέσα στα mediaFiles και τα formats
                    if movie.get('mediaFiles'):
                        for media_file in movie['mediaFiles']:
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
