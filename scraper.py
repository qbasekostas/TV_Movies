import requests
import os
import json
import re

# =================================================================================
# ΟΡΙΣΤΙΚΗ ΛΥΣΗ:
# Στοχεύουμε απευθείας στο URL που περιέχει το JSON με ΟΛΑ τα δεδομένα.
# Αυτό το URL επιβεβαιώθηκε από εσάς.
# =================================================================================
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
        
        # ΟΡΙΣΤΙΚΗ ΔΙΟΡΘΩΣΗ:
        # Σε αυτή τη σελίδα, η λίστα ταινιών είναι το πρώτο (και μοναδικό) "component".
        # Παίρνουμε τα 'tiles' απευθείας από εκεί, χωρίς να ψάχνουμε για τίτλο.
        components = initial_data.get('bootstrap', {}).get('page', {}).get('data', {}).get('components', [])
        
        if components and 'tiles' in components[0]:
            tiles = components[0]['tiles']
            print(f"SUCCESS: Extracted data for {len(tiles)} movies from the page.")
            return tiles
        else:
            print("FAILURE: Found the INITIAL_STATE block, but could not find the movie list inside.")
            return []

    except Exception as e:
        print(f"An error occurred: {e}")
        return []

def main():
    """Κύρια συνάρτηση του script."""
    movies_data = get_all_movies_data()
    playlist_entries = []
    
    if movies_data:
        for movie in movies_data:
            try:
                # Ελέγχουμε αν είναι όντως ταινία (και όχι σειρά, κλπ)
                if movie.get('type') != 'vod' or movie.get('isEpisode'):
                    continue
                    
                title = movie.get('title')
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
                
                if not m3u8_url:
                    # Αν δεν υπάρχει m3u8, ίσως υπάρχει στο βασικό αντικείμενο (για παλαιότερες ταινίες)
                    if movie.get('mediafile', '').endswith('.m3u8'):
                         m3u8_url = movie.get('mediafile')

                # Βρίσκουμε μια κατάλληλη εικόνα (poster)
                for img in movie.get('images', []):
                    if img.get('role') == 'poster':
                        image_url = img.get('url')
                        break
                
                if all([title, image_url, m3u8_url]):
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
