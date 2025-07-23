import requests
from bs4 import BeautifulSoup
import re
import os

BASE_URL = "https://www.skai.gr"
CINEMA_URL = f"{BASE_URL}/tv/cinema"
OUTPUT_FILE = "skai_playlist.m3u8"

def get_movie_list():
    """Παίρνει τη λίστα των ταινιών από την κεντρική σελίδα."""
    print("Fetching movie list...")
    try:
        response = requests.get(CINEMA_URL, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        movies = []
        # ΑΛΛΑΓΗ: Πιο στοχευμένος επιλογέας με βάση το HTML που δόθηκε.
        movie_cards = soup.find_all('div', class_='col-lg-4 listimg')
        
        for card in movie_cards:
            link_tag = card.find('a')
            if link_tag and link_tag.has_attr('href'):
                # ΑΛΛΑΓΗ: Πιο στοχευμένοι επιλογείς για τίτλο και εικόνα.
                title_tag = link_tag.find('h3', class_='title_r')
                img_tag = link_tag.find('img')
                
                if title_tag and img_tag and img_tag.has_attr('src'):
                    title = title_tag.get_text(strip=True)
                    relative_url = link_tag['href']
                    image_url = img_tag['src']
                    
                    movies.append({
                        'title': title,
                        'url': relative_url,
                        'image': image_url
                    })
        
        print(f"Found {len(movies)} movies.")
        return movies
    except requests.RequestException as e:
        print(f"Error fetching movie list: {e}")
        return []

def get_episode_url(movie_page_url):
    """Βρίσκει το URL του επεισοδίου/player από τη σελίδα της ταινίας."""
    full_url = f"{BASE_URL}{movie_page_url}"
    try:
        response = requests.get(full_url, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Ο σύνδεσμος για το επεισόδιο είναι συνήθως στο κεντρικό media player.
        # Βρίσκουμε το div του main-media και μετά τον σύνδεσμο μέσα σε αυτό.
        main_media = soup.find('div', class_='main-media')
        if main_media:
            play_link = main_media.find('a')
            if play_link and play_link.has_attr('href'):
                return play_link['href']

    except requests.RequestException as e:
        print(f"Error fetching episode URL from {full_url}: {e}")
    return None

def get_m3u8_url(episode_page_url):
    """Εξάγει το m3u8 URL από τη σελίδα του player, όπως επιβεβαιώθηκε."""
    if not episode_page_url.startswith('http'):
        full_url = f"{BASE_URL}{episode_page_url}"
    else:
        full_url = episode_page_url

    try:
        response = requests.get(full_url, timeout=20)
        response.raise_for_status()
        
        # Αυτή η μέθοδος με Regular Expression είναι η πιο αξιόπιστη και επιβεβαιώθηκε
        # από το URL που δώσατε.
        match = re.search(r'file\s*:\s*"([^"]+\.m3u8)"', response.text)
        if match:
            return match.group(1)
            
    except requests.RequestException as e:
        print(f"Error fetching m3u8 URL from {full_url}: {e}")
    return None

def main():
    """Κύρια συνάρτηση του script."""
    all_movies = get_movie_list()
    if not all_movies:
        print("No movies found. Exiting.")
        # Δημιουργεί ένα κενό αρχείο για να μην αποτύχει το commit step
        open(OUTPUT_FILE, 'w').close()
        return

    playlist_entries = []
    for movie in all_movies:
        print(f"Processing: {movie['title']}")
        
        episode_url = get_episode_url(movie['url'])
        if not episode_url:
            print(f"  -> Could not find episode link for {movie['title']}.")
            continue
            
        m3u8_url = get_m3u8_url(episode_url)
        if not m3u8_url:
            print(f"  -> Could not find m3u8 stream for {movie['title']}.")
            continue
        
        # ΝΕΟ: Προσθήκη του tvg-logo με το URL της εικόνας για καλύτερη εμφάνιση στους players
        print(f"  -> Found M3U8: {m3u8_url}")
        print(f"  -> Found Image: {movie['image']}")
        entry = f'#EXTINF:-1 tvg-logo="{movie["image"]}",{movie["title"]}\n{m3u8_url}'
        playlist_entries.append(entry)

    if not playlist_entries:
        print("No valid streams found. Playlist will not be updated.")
        # Διασφαλίζει ότι το αρχείο υπάρχει ακόμα και αν είναι κενό
        open(OUTPUT_FILE, 'w').close()
        return

    # Δημιουργία του τελικού περιεχομένου του αρχείου
    playlist_content = "#EXTM3U\n\n" + "\n\n".join(playlist_entries)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(playlist_content)
        
    print(f"\nSuccessfully created playlist '{OUTPUT_FILE}' with {len(playlist_entries)} entries.")

if __name__ == "__main__":
    main()
