import requests
from bs4 import BeautifulSoup

URL = "https://www.ertflix.gr/list?pageCodename=movies&sectionCodename=oles-oi-tainies-1&tileCount=300"
HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def get_movie_titles(soup):
    """
    Επιστρέφει ένα σετ με τίτλους ταινιών από το soup.
    """
    movies = set()
    # Αναζήτηση τίτλων σε h3, span, div, strong
    for tag in soup.find_all(["h3", "span", "div", "strong"]):
        text = tag.get_text(strip=True)
        if len(text) > 4 and (any(x in text.lower() for x in ["ταινία", "movie"]) or len(text) > 8):
            movies.add(text)
    return movies

def save_as_m3u8(titles, filename="ertflix_playlist.m3u8"):
    """
    Αποθηκεύει τους τίτλους ως m3u8 playlist (χωρίς stream links, μόνο τίτλους με dummy url).
    """
    with open(filename, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for i, title in enumerate(sorted(titles), 1):
            # Dummy URL - αν βρεις τα πραγματικά links, βάλε τα εδώ!
            stream_url = f"https://example.com/movie_stream_{i}.mp4"
            f.write(f'#EXTINF:-1,{title}\n{stream_url}\n')

def main():
    response = requests.get(URL, headers=HEADERS)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    titles = get_movie_titles(soup)

    print(f"Βρέθηκαν τίτλοι: {len(titles)}")
    for title in sorted(titles):
        print("-", title)

    save_as_m3u8(titles)
    print("\nΑποθηκεύτηκε το ertflix_playlist.m3u8")

if __name__ == "__main__":
    main()
