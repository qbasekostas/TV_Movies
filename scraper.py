import requests
import os
import json
import re

MOVIE_LIST_URL = "https://www.ertflix.gr/list?pageCodename=movies&backUrl=/show/movies&sectionCodename=oles-oi-tainies-1&tileCount=300"
OUTPUT_FILE = "ertflix_playlist.m3u8"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def find_movie_list_recursively(data_node):
    """
    Μια 'έξυπνη' αναδρομική συνάρτηση που ψάχνει σε ολόκληρο το JSON
    για να βρει μια λίστα που μοιάζει με τη λίστα ταινιών.
    """
    # Αν ο κόμβος είναι λίστα...
    if isinstance(data_node, list) and data_node:
        # ...ελέγχουμε αν το πρώτο της στοιχείο μοιάζει με ταινία.
        # Μια ταινία πρέπει να έχει 'title', 'mediafiles', και 'images'.
        first_item = data_node[0]
        if isinstance(first_item, dict) and all(k in first_item for k in ['title', 'mediafiles', 'images']):
            return data_node # Βρήκαμε τη λίστα!

    # Αν ο κόμβος είναι dictionary, ψάχνουμε σε όλες τις τιμές του.
    if isinstance(data_node, dict):
        for key, value in data_node.items():
            result = find_movie_list_recursively(value)
            if result:
                return result

    # Αν ο κόμβος είναι λίστα, ψάχνουμε σε όλα τα στοιχεία του.
    if isinstance(data_node, list):
        for item in data_node:
            result = find_movie_list_recursively(item)
            if result:
                return result
    
    # Αν δεν βρεθεί τίποτα, επιστρέφουμε None.
    return None

def get_all_movies_data():
    """
    Κατεβάζει τη σελίδα και χρησιμοποιεί την αναδρομική συνάρτηση
    για να βρει τη λίστα των ταινιών μέσα στο ___INITIAL_STATE___.
    """
    print(f"Fetching page to extract embedded data from: {MOVIE_LIST_URL}")
    try:
        response = requests.get(MOVIE_LIST_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        match = re.search(r'<script>var ___INITIAL_STATE__ = (\{.*?\});<\/script>', response.text)
        if not match:
            print("FATAL: Could not find the ___INITIAL_STATE___ data block.")
            return []
            
        initial_data = json.loads(match.group(1))
        
        print("Searching for movie list within the data block...")
        movie_list = find_movie_list_recursively(initial_data)
        
        if movie_list:
            print(f"SUCCESS: Found the movie list with {len(movie_list)} items.")
            return movie_list
        else:
            print("FAILURE: Could not find a valid movie list anywhere in the data block.")
            return []

    except requests.RequestException as e:
        print(f"Error fetching the main page: {e}")
        return []
    except (json.JSONDecodeError, AttributeError, IndexError) as e:
        print(f"Error parsing the page's embedded data: {e}")
        return []

def main():
    """Κύρια συνάρτηση του script."""
    movies_data = get_all_movies_data()
    playlist_entries = []
    
    if movies_data:
        for movie in movies_data:
            try:
                title = movie['title']
                m3u8_url = movie['mediafiles'][0]['url']
                image_url = movie['images']['cover']['url']
                
                if m3u8_url.endswith('.m3u8'):
                    print(f"  -> Found: {title}")
                    entry = f'#EXTINF:-1 tvg-logo="{image_url}",{title}\n{m3u8_url}'
                    playlist_entries.append(entry)
                else:
                    print(f"  -> Skipped: {title} (Stream is not m3u8)")
            except (KeyError, IndexError):
                print(f"  -> Skipped an item due to missing/incomplete data.")
                continue

    print(f"\nCreating playlist file '{OUTPUT_FILE}'...")
    playlist_content = "#EXTM3U\n\n" + "\n\n".join(playlist_entries)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(playlist_content)
        
    print(f"\n>>>>>>>>> Finished. Created playlist with {len(playlist_entries)} movies. <<<<<<<<<")

if __name__ == "__main__":
    main()
