import requests
from bs4 import BeautifulSoup
import re
import os
import json

BASE_URL = "https://www.skai.gr"
TV_BASE_URL = f"{BASE_URL}/tv" # <--- ΝΕΑ ΜΕΤΑΒΛΗΤΗ ΓΙΑ ΝΑ ΜΗ ΓΙΝΕΙ ΞΑΝΑ ΛΑΘΟΣ
CINEMA_URL = f"{TV_BASE_URL}/cinema"
OUTPUT_FILE = "skai_playlist.m3u8"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def make_request(url):
    """Κάνει μια HTTP GET αίτηση χρησιμοποιώντας τα απαραίτητα headers."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        print(f"  -> ERROR during request for {url}: {e}")
        return None

def get_movie_list():
    """Παίρνει τη λίστα των ταινιών από την κεντρική σελίδα."""
    print("Fetching movie list...")
    response = make_request(CINEMA_URL)
    if not response:
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    movies = []
    movie_cards = soup.find_all('div', class_='col-lg-4 listimg')
    
    for card in movie_cards:
        link_tag = card.find('a')
        if link_tag and link_tag.has_attr('href'):
            title_tag = link_tag.find('h3', class_='title_r')
            img_tag = link_tag.find('img')
            
            if title_tag and img_tag and img_tag.has_attr('src'):
                movies.append({
                    'title': title_tag.get_text(strip=True),
                    'url': link_tag['href'],
                    'image': img_tag['src']
                })
    
    print(f"Found {len(movies)} movies.")
    return movies

def get_episode_url(movie_page_url):
    """Εξάγει το JSON από το <script> tag της σελίδας της ταινίας."""
    full_url = f"{TV_BASE_URL}{movie_page_url}" # <--- Διορθώθηκε για να χρησιμοποιεί το TV_BASE_URL
    print(f"  -> Searching for episode data on page: {full_url}")
    
    response = make_request(full_url)
    if not response:
        return None

    match = re.search(r'var data = (\{.*?\});', response.text, re.DOTALL)
    
    if match:
        json_text = match.group(1)
        try:
            data_dict = json.loads(json_text)
            if 'episodes' in data_dict and len(data_dict['episodes']) > 0:
                episode_link = data_dict['episodes'][0].get('link')
                if episode_link:
                    print(f"  -> SUCCESS: Found episode link via JSON: {episode_link}")
                    return episode_link
        except json.JSONDecodeError:
            print("  -> FAILED: Could not decode JSON data.")
            return None

    print("  -> FAILED: Could not find 'var data = {...};' script block.")
    return None

def get_m3u8_url(episode_page_url):
    """
    Εξάγει το m3u8 URL από το JSON data της σελίδας του player.
    """
    # ΔΙΟΡΘΩΣΗ: Προσθέτουμε το /tv/ που έλειπε
    full_url = f"{TV_BASE_URL}{episode_page_url}"
    print(f"  -> Searching for m3u8 data on page: {full_url}")

    response = make_request(full_url)
    if not response:
        return None

    # Χρησιμοποιούμε την ίδια μέθοδο για να βρούμε τα δεδομένα του player
    match = re.search(r'var data = (\{.*?\});', response.text, re.DOTALL)
    
    if match:
        json_text = match.group(1)
        try:
            data_dict = json.loads(json_text)
            # Το m3u8 link βρίσκεται στο πεδίο 'drm' του πρώτου επεισοδίου
            if 'episode' in data_dict and len(data_dict['episode']) > 0:
                m3u8_link = data_dict['episode'][0].get('drm')
                if m3u8_link:
                    # Το link μπορεί να έχει DRM, αλλά το βασικό stream συνήθως παίζει.
                    print(f"  -> SUCCESS: Found m3u8 link via JSON: {m3u8_link}")
                    return m3u8_link
        except json.JSONDecodeError as e:
            print(f"  -> FAILED: Could not decode player JSON data. Error: {e}")
            return None
            
    print("  -> FAILED: Could not find player's 'var data = {...};' script block.")
    return None

def main():
    """Κύρια συνάρτηση του script."""
    all_movies = get_movie_list()
    if not all_movies:
        print("No movies found or initial page failed to load. Exiting.")
        return

    playlist_entries = []
    for movie in all_movies:
        print(f"Processing: {movie['title']}")
        
        episode_url = get_episode_url(movie['url'])
        if not episode_url:
            continue
            
        m3u8_url = get_m3u8_url(episode_url)
        if not m3u8_url:
            continue
        
        print(f"  -> FINAL SUCCESS: Found M3U8 for {movie['title']}")
        entry = f'#EXTINF:-1 tvg-logo="{movie["image"]}",{movie["title"]}\n{m3u8_url}'
        playlist_entries.append(entry)

    playlist_content = "#EXTM3U\n\n" + "\n\n".join(playlist_entries)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(playlist_content)
        
    print(f"\nSuccessfully created playlist '{OUTPUT_FILE}' with {len(playlist_entries)} entries.")

if __name__ == "__main__":
    main()
