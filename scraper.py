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
        movie_cards = soup.find_all('div', class_='col-lg-4 listimg')
        
        for card in movie_cards:
            link_tag = card.find('a')
            if link_tag and link_tag.has_attr('href'):
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
    """
    ΑΛΛΑΓΗ: Βρίσκει το URL του player στοχεύοντας στο div 'list-item'
    που επιβεβαιώθηκε από το παράδειγμα του χρήστη.
    """
    full_url = f"{BASE_URL}{movie_page_url}"
    print(f"  -> Searching for episode link on page: {full_url}")
    try:
        response = requests.get(full_url, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Στοχεύουμε στο div που περιέχει τη λέξη 'list-item' στην κλάση του.
        # Αυτό είναι το κλειδί από το HTML που στείλατε.
        list_item_div = soup.find('div', class_=re.compile(r'\blist-item\b'))
        
        if list_item_div:
            # Μέσα σε αυτό το div, βρίσκουμε τον σύνδεσμο που οδηγεί στο player.
            episode_link = list_item_div.find('a', href=re.compile(r'/tv/episode/'))
            if episode_link and episode_link.has_attr('href'):
                print(f"  -> SUCCESS: Found episode link: {episode_link['href']}")
                return episode_link['href']

        print("  -> FAILED: Episode link not found inside a 'list-item' div.")
        return None

    except requests.RequestException as e:
        print(f"  -> ERROR fetching episode URL from {full_url}: {e}")
        return None

def get_m3u8_url(episode_page_url):
    """Εξάγει το m3u8 URL από τη σελίδα του player."""
    if not episode_page_url.startswith('http'):
        full_url = f"{BASE_URL}{episode_page_url}"
    else:
        full_url = episode_page_url

    try:
        response = requests.get(full_url, timeout=20)
        response.raise_for_status()
        
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
        # Δημιουργεί ένα κενό αρχείο για να μη σκάσει το commit step
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n")
        return

    playlist_entries = []
    for movie in all_movies:
        print(f"Processing: {movie['title']}")
        
        episode_url = get_episode_url(movie['url'])
        if not episode_url:
            continue # Προχωράμε στην επόμενη ταινία
            
        m3u8_url = get_m3u8_url(episode_url)
        if not m3u8_url:
            print(f"  -> FAILED to find m3u8 stream for {movie['title']}.")
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
