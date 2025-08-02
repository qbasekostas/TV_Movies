import requests
import os
import json

# API endpoints του ERTFlix
API_LIST_URL = "https://api.ertflix.gr/v2/list/section/oles-oi-tainies-1?page=0&tileCount=200"
API_VOD_URL_TEMPLATE = "https://api.ertflix.gr/v2/vod/tile/{movie_id}"

OUTPUT_FILE = "ertflix_playlist.m3u8" # Αλλάζουμε το όνομα του αρχείου εξόδου

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_movie_list():
    """Παίρνει τη λίστα των ταινιών απευθείας από το API του ERTFlix."""
    print("Fetching movie list from ERTFlix API...")
    try:
        response = requests.get(API_LIST_URL, headers=HEADERS, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        # Τα δεδομένα των ταινιών βρίσκονται μέσα στο 'data' key
        if 'data' in data and data['data']:
            print(f"Found {len(data['data'])} movies in the list.")
            return data['data']
        else:
            print("Could not find movie data in the API response.")
            return []
            
    except requests.RequestException as e:
        print(f"Error fetching movie list from API: {e}")
        return []
    except json.JSONDecodeError:
        print("Failed to parse JSON from API response.")
        return []

def get_movie_stream_details(movie_id):
    """Παίρνει το .m3u8 link για μια συγκεκριμένη ταινία μέσω του API."""
    vod_url = API_VOD_URL_TEMPLATE.format(movie_id=movie_id)
    print(f"  -> Fetching stream details from: {vod_url}")
    try:
        response = requests.get(vod_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        # Το m3u8 link συνήθως είναι το πρώτο στη λίστα mediafiles
        if 'data' in data and 'mediafiles' in data['data'] and data['data']['mediafiles']:
            stream_url = data['data']['mediafiles'][0].get('url')
            if stream_url and stream_url.endswith('.m3u8'):
                print(f"  -> SUCCESS: Found m3u8 stream: {stream_url}")
                return stream_url
            else:
                print(f"  -> INFO: Found a stream but it's not a .m3u8 link.")
        
        return None
        
    except requests.RequestException as e:
        print(f"  -> ERROR fetching stream details: {e}")
        return None
    except json.JSONDecodeError:
        print("  -> FAILED to parse stream details JSON.")
        return None

def main():
    """Κύρια συνάρτηση του script."""
    movies = get_movie_list()
    if not movies:
        print("No movies found. Exiting.")
        return

    playlist_entries = []
    found_count = 0
    total_movies = len(movies)

    for movie in movies:
        title = movie.get('title')
        movie_id = movie.get('id')
        
        # Η εικόνα είναι μέσα σε ένα nested dictionary
        try:
            image_url = movie['images']['cover']['url']
        except (KeyError, TypeError):
            image_url = "" # Βάζουμε κενό string αν δεν υπάρχει εικόνα

        if not all([title, movie_id]):
            print("Skipping an item due to missing title or id.")
            continue
        
        print(f"\nProcessing: {title} (ID: {movie_id})")
        
        m3u8_url = get_movie_stream_details(movie_id)
        
        if m3u8_url:
            found_count += 1
            entry = f'#EXTINF:-1 tvg-logo="{image_url}",{title}\n{m3u8_url}'
            playlist_entries.append(entry)
        else:
            print(f"  -> FINAL RESULT: No playable stream found for '{title}'.")

    # Δημιουργία του περιεχομένου του αρχείου
    playlist_content = "#EXTM3U\n\n" + "\n\n".join(playlist_entries)
    
    # Εγγραφή στο αρχείο
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(playlist_content)
        
    print(f"\n>>>>>>>>> Successfully created playlist '{OUTPUT_FILE}' with {found_count} out of {total_movies} movies. <<<<<<<<<")


if __name__ == "__main__":
    main()
