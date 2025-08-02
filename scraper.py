import requests
import os
import json

# =================================================================================
# ΟΡΙΣΤΙΚΗ ΛΥΣΗ:
# Βήμα 1: Παίρνουμε τα IDs των ταινιών από αυτό το API.
# Βήμα 2: Ζητάμε τις πλήρεις πληροφορίες (μαζί με τα m3u8) από το δεύτερο API.
# =================================================================================
API_GET_IDS_URL = "https://api.app.ertflix.gr/v2/list/section/oles-oi-tainies-1?page=0&tileCount=300"
API_GET_DETAILS_URL = "https://api.app.ertflix.gr/v2/tile/list"

OUTPUT_FILE = "ertflix_playlist.m3u8"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_movie_ids():
    """Βήμα 1: Παίρνει τη λίστα με τα IDs όλων των ταινιών."""
    print(f"Fetching movie IDs from: {API_GET_IDS_URL}")
    try:
        response = requests.get(API_GET_IDS_URL, headers=HEADERS, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        movie_ids = [item['id'] for item in data.get('data', []) if 'id' in item]
        
        if movie_ids:
            print(f"SUCCESS: Found {len(movie_ids)} movie IDs.")
            return movie_ids
        else:
            print("FAILURE: No movie IDs found in the response.")
            return []
            
    except requests.RequestException as e:
        print(f"Error fetching movie IDs: {e}")
        return []

def get_movies_details(movie_ids):
    """Βήμα 2: Παίρνει τις πλήρεις λεπτομέρειες για μια λίστα από IDs."""
    print(f"Fetching details for {len(movie_ids)} movies from: {API_GET_DETAILS_URL}")
    
    # Το payload που στέλνουμε στο API, όπως το είδαμε στα δεδομένα σας
    payload = {
        "platformCodename": "www",
        "requestedTiles": [{"id": movie_id} for movie_id in movie_ids]
    }
    
    try:
        # Χρησιμοποιούμε POST request για να στείλουμε τα IDs
        response = requests.post(API_GET_DETAILS_URL, headers=HEADERS, json=payload, timeout=45)
        response.raise_for_status()
        data = response.json()
        
        if 'tiles' in data:
            print(f"SUCCESS: Received details for {len(data['tiles'])} movies.")
            return data['tiles']
        else:
            print("FAILURE: 'tiles' key not found in the details response.")
            return []
            
    except requests.RequestException as e:
        print(f"Error fetching movie details: {e}")
        return []

def main():
    """Κύρια συνάρτηση του script."""
    movie_ids = get_movie_ids()
    
    if not movie_ids:
        print("No movie IDs found. Aborting.")
        # Δημιουργούμε κενό αρχείο για να μη σκάσει το Action
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n")
        return

    movies_data = get_movies_details(movie_ids)
    playlist_entries = []
    
    if movies_data:
        for movie in movies_data:
            try:
                title = movie['title']
                m3u8_url = movie['mediaFiles'][0]['formats'][2]['url'] # Βασισμένο στη δομή που στείλατε
                image_url = movie['images'][2]['url'] # Το ίδιο και εδώ
                
                if m3u8_url.endswith('.m3u8'):
                    print(f"  -> Found: {title}")
                    entry = f'#EXTINF:-1 tvg-logo="{image_url}",{title}\n{m3u8_url}'
                    playlist_entries.append(entry)
                else:
                    print(f"  -> Skipped: {title} (Stream is not m3u8)")

            except (KeyError, IndexError):
                # Αγνοούμε ταινίες που δεν έχουν την αναμενόμενη δομή
                print(f"  -> Skipped '{movie.get('title', 'Unknown')}' due to unexpected data structure.")
                continue

    print(f"\nCreating playlist file '{OUTPUT_FILE}'...")
    playlist_content = "#EXTM3U\n\n" + "\n\n".join(playlist_entries)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(playlist_content)
        
    print(f"\n>>>>>>>>> Finished. Created playlist with {len(playlist_entries)} movies. <<<<<<<<<")

if __name__ == "__main__":
    main()
