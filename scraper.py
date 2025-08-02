import requests
import os
import json

# Βασικοί API endpoints
API_PAGE_URL = "https://api.ertflix.gr/v2/page/movies" # Γενική σελίδα ταινιών
API_LIST_TEMPLATE = "https://api.ertflix.gr/v2/list/{list_id}?page=0&tileCount=250"
API_VOD_TEMPLATE = "https://api.ertflix.gr/v2/vod/tile/{movie_id}"

OUTPUT_FILE = "ertflix_playlist.m3u8"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_movies_list_id():
    """Βρίσκει το δυναμικό ID της λίστας 'Όλες οι ταινίες'."""
    print("Fetching the main movies page to find the list ID...")
    try:
        response = requests.get(API_PAGE_URL, headers=HEADERS, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        # Ψάχνουμε στα components της σελίδας για τη σωστή λίστα
        for component in data.get('data', {}).get('components', []):
            if component.get('title') == 'Όλες οι ταινίες':
                list_id = component.get('listId')
                if list_id:
                    print(f"SUCCESS: Found list ID: {list_id}")
                    return list_id
        
        print("FAILURE: Could not find the 'Όλες οι ταινίες' component on the page.")
        return None
        
    except requests.RequestException as e:
        print(f"Error fetching page data: {e}")
        return None

def get_all_movies_from_list(list_id):
    """Παίρνει όλες τις ταινίες από ένα συγκεκριμένο list ID."""
    list_url = API_LIST_TEMPLATE.format(list_id=list_id)
    print(f"Fetching all movies from list URL: {list_url}")
    try:
        response = requests.get(list_url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        if 'data' in data and data['data']:
            print(f"Found {len(data['data'])} movies in the list.")
            return data['data']
        
        return []
    except requests.RequestException as e:
        print(f"Error fetching movie list from API: {e}")
        return []

def get_movie_stream_details(movie_id):
    """Παίρνει το .m3u8 link για μια συγκεκριμένη ταινία."""
    vod_url = API_VOD_TEMPLATE.format(movie_id=movie_id)
    print(f"  -> Fetching stream details for movie ID: {movie_id}")
    try:
        response = requests.get(vod_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        if 'data' in data and 'mediafiles' in data['data'] and data['data']['mediafiles']:
            stream_url = data['data']['mediafiles'][0].get('url')
            if stream_url and stream_url.endswith('.m3u8'):
                return stream_url
        return None
    except requests.RequestException:
        # Αγνοούμε σφάλματα εδώ, π.χ. αν μια ταινία έχει λήξει (404)
        return None

def main():
    """Κύρια συνάρτηση του script."""
    playlist_entries = []
    
    list_id = get_movies_list_id()
    if list_id:
        movies = get_all_movies_from_list(list_id)
        
        if movies:
            for movie in movies:
                title = movie.get('title')
                movie_id = movie.get('id')
                try:
                    image_url = movie['images']['cover']['url']
                except (KeyError, TypeError):
                    image_url = ""

                if not all([title, movie_id]):
                    continue
                
                print(f"\nProcessing: {title}")
                m3u8_url = get_movie_stream_details(movie_id)
                
                if m3u8_url:
                    print(f"  -> SUCCESS: Found playable stream for '{title}'.")
                    entry = f'#EXTINF:-1 tvg-logo="{image_url}",{title}\n{m3u8_url}'
                    playlist_entries.append(entry)
                else:
                    print(f"  -> SKIPPED: No playable stream found for '{title}'.")

    # ΑΣΦΑΛΕΙΑ: Δημιουργούμε το αρχείο ακόμα και αν είναι κενό
    # για να μην αποτύχει το GitHub Action.
    print(f"\nCreating playlist file '{OUTPUT_FILE}'...")
    playlist_content = "#EXTM3U\n\n" + "\n\n".join(playlist_entries)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(playlist_content)
        
    print(f"\n>>>>>>>>> Finished. Created playlist with {len(playlist_entries)} movies. <<<<<<<<<")

if __name__ == "__main__":
    main()
