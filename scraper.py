import requests
import os
import json
import re

MOVIE_LIST_URL = "https://www.ertflix.gr/list?pageCodename=movies&backUrl=/show/movies&sectionCodename=oles-oi-tainies-1&tileCount=300"
OUTPUT_FILE = "ertflix_playlist.m3u8"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_all_movies_data():
    """
    Κατεβάζει την κεντρική σελίδα και εξάγει το ενσωματωμένο JSON
    που περιέχει ΟΛΕΣ τις πληροφορίες για τις ταινίες, από το ___INITIAL_STATE___.
    """
    print(f"Fetching page to extract embedded data from: {MOVIE_LIST_URL}")
    try:
        response = requests.get(MOVIE_LIST_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        match = re.search(r'<script>var ___INITIAL_STATE__ = (\{.*?\});<\/script>', response.text)
        if not match:
            print("FATAL: Could not find the ___INITIAL_STATE___ data block in the page source.")
            return []
            
        initial_data = json.loads(match.group(1))
        
        # --- Η ΟΡΙΣΤΙΚΗ ΔΙΟΡΘΩΣΗ ΕΙΝΑΙ ΕΔΩ ---
        # Πλοηγούμαστε στο σημείο που περιέχει τις λίστες περιεχομένου της σελίδας
        components = initial_data.get('bootstrap', {}).get('page', {}).get('data', {}).get('components', [])
        
        # Ψάχνουμε σε όλες τις λίστες για αυτήν με τον τίτλο "Όλες οι ταινίες"
        for component in components:
            if component.get('title') == 'Όλες οι Ταινίες':
                tiles = component.get('tiles', [])
                if tiles:
                    print(f"SUCCESS: Found the 'Όλες οι Ταινίες' list with {len(tiles)} movies.")
                    return tiles
        
        print("FAILURE: Could not find a component with the title 'Όλες οι Ταινίες' that contains movies.")
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
