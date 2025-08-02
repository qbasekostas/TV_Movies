import requests
import os
import json
import re

# Το μοναδικό URL που χρειαζόμαστε, αυτό που δώσατε εσείς.
# Αυξάνουμε το tileCount για να πιάσουμε όσο το δυνατόν περισσότερες ταινίες.
MOVIE_LIST_URL = "https://www.ertflix.gr/list?pageCodename=movies&backUrl=/show/movies&sectionCodename=oles-oi-tainies-1"

OUTPUT_FILE = "ertflix_playlist.m3u8"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_all_movies_data():
    """
    Κατεβάζει την κεντρική σελίδα και εξάγει το ενσωματωμένο JSON
    που περιέχει ΟΛΕΣ τις πληροφορίες για τις ταινίες.
    """
    print(f"Fetching main page to extract embedded data from: {MOVIE_LIST_URL}")
    try:
        response = requests.get(MOVIE_LIST_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        # Ψάχνουμε για το <script> που περιέχει τα δεδομένα της σελίδας (Nuxt.js pattern)
        match = re.search(r'<script>window\.__NUXT__=(\{.*?\});<\/script>', response.text)
        if not match:
            print("FATAL: Could not find the __NUXT__ data block in the page source.")
            return []
            
        # Μετατρέπουμε το κείμενο JSON σε ένα διαχειρίσιμο Python dictionary
        nuxt_data = json.loads(match.group(1))
        
        # Πλοηγούμαστε στο περίπλοκο JSON για να βρούμε τη λίστα με τα "tiles" (τις ταινίες)
        # Η διαδρομή μπορεί να αλλάξει, αλλά αυτή είναι η τρέχουσα.
        tiles = nuxt_data.get('data', [{}])[0].get('page', {}).get('components', [{}])[0].get('tiles', [])
        
        if tiles:
            print(f"SUCCESS: Extracted data for {len(tiles)} movies from the page.")
            return tiles
        else:
            print("FAILURE: Found the NUXT block, but the path to movie tiles was incorrect or empty.")
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
                image_url = movie['images']['cover']['url']
                # Το m3u8 link βρίσκεται απευθείας εδώ!
                m3u8_url = movie['mediafiles'][0]['url']
                
                if m3u8_url.endswith('.m3u8'):
                    print(f"  -> Found: {title}")
                    entry = f'#EXTINF:-1 tvg-logo="{image_url}",{title}\n{m3u8_url}'
                    playlist_entries.append(entry)
                else:
                    print(f"  -> Skipped: {title} (Stream is not m3u8)")

            except (KeyError, IndexError):
                # Αγνοούμε ταινίες που δεν έχουν όλα τα απαραίτητα πεδία
                print(f"  -> Skipped an item due to missing data.")
                continue

    # Δημιουργούμε το αρχείο, ακόμα και αν είναι κενό.
    print(f"\nCreating playlist file '{OUTPUT_FILE}'...")
    playlist_content = "#EXTM3U\n\n" + "\n\n".join(playlist_entries)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(playlist_content)
        
    print(f"\n>>>>>>>>> Finished. Created playlist with {len(playlist_entries)} movies. <<<<<<<<<")

if __name__ == "__main__":
    main()
