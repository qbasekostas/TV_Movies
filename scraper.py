import requests
import os
import json
import re

# Το μοναδικό, σωστό URL.
PAGE_URL = "https://www.ertflix.gr/show/movies"
OUTPUT_FILE = "ertflix_playlist.m3u8"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def extract_movies_from_page():
    """
    Κατεβάζει την κεντρική σελίδα ταινιών και εξάγει ΟΛΕΣ τις ταινίες
    από το ενσωματωμένο JSON του ___INITIAL_STATE___.
    """
    print(f"Fetching page to extract embedded data from: {PAGE_URL}")
    try:
        response = requests.get(PAGE_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        match = re.search(r'<script>var ___INITIAL_STATE__ = (\{.*?\});<\/script>', response.text)
        if not match:
            print("FATAL: Could not find the ___INITIAL_STATE___ data block in the page source.")
            return []
            
        initial_data = json.loads(match.group(1))
        
        all_movies = []
        # Σαρώνουμε όλα τα 'components' (λίστες) της σελίδας
        components = initial_data.get('bootstrap', {}).get('page', {}).get('data', {}).get('components', [])
        
        print(f"Found {len(components)} content lists on the page. Searching for movies in each...")
        
        for component in components:
            # Παίρνουμε τα 'tiles' (ταινίες/σειρές) από κάθε component
            tiles = component.get('tiles', [])
            if tiles:
                print(f" -> Found {len(tiles)} items in list titled '{component.get('title', 'Untitled')}'")
                all_movies.extend(tiles)
        
        if all_movies:
            # Αφαιρούμε τυχόν διπλότυπα
            unique_movies = {movie['id']: movie for movie in all_movies}.values()
            print(f"\nSUCCESS: Extracted data for {len(unique_movies)} unique movies from the page.")
            return list(unique_movies)
        else:
            print("FAILURE: Could not extract any movie items from the page components.")
            return []

    except Exception as e:
        print(f"An error occurred: {e}")
        return []

def main():
    """Κύρια συνάρτηση του script."""
    movies_data = extract_movies_from_page()
    playlist_entries = []
    
    if movies_data:
        for movie in movies_data:
            try:
                # Ελέγχουμε αν είναι όντως ταινία (και όχι σειρά, κλπ)
                if movie.get('type') != 'vod' or movie.get('isEpisode'):
                    continue
                    
                title = movie['title']
                m3u8_url = None
                image_url = ""

                # Βρίσκουμε το m3u8 link
                if movie.get('mediaFiles'):
                    for media_file in movie.get('mediaFiles', []):
                        for fmt in media_file.get('formats', []):
                            if fmt.get('url', '').endswith('.m3u8'):
                                m3u8_url = fmt['url']
                                break
                        if m3u8_url:
                            break
                
                # Αν δεν βρέθηκε m3u8, το προσπερνάμε
                if not m3u8_url:
                    print(f"  -> Skipped '{title}' (No m3u8 stream available).")
                    continue

                # Βρίσκουμε μια κατάλληλη εικόνα
                for img in movie.get('images', []):
                    if img.get('role') == 'poster':
                        image_url = img.get('url')
                        break
                
                print(f"  -> Found: {title}")
                entry = f'#EXTINF:-1 tvg-logo="{image_url}",{title}\n{m3u8_url}'
                playlist_entries.append(entry)

            except (KeyError, IndexError, TypeError):
                continue

    print(f"\nCreating playlist file '{OUTPUT_FILE}'...")
    playlist_content = "#EXTM3U\n\n" + "\n\n".join(playlist_entries)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(playlist_content)
        
    print(f"\n>>>>>>>>> Finished. Created playlist with {len(playlist_entries)} movies. <<<<<<<<<")

if __name__ == "__main__":
    main()
