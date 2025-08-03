import requests
from bs4 import BeautifulSoup

URL = "https://www.ertflix.gr/list?pageCodename=movies&sectionCodename=oles-oi-tainies-1&tileCount=300"

headers = {
    "User-Agent": "Mozilla/5.0"
}

def main():
    response = requests.get(URL, headers=headers)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Αναζήτηση όλων των τίτλων ταινιών (δοκίμασε και άλλα selectors αν δεν βρίσκει)
    movies = set()

    # Πολλές φορές οι τίτλοι υπάρχουν σε στοιχεία όπως <h3>, <span>, <div> με συγκεκριμένες κλάσεις
    for tag in soup.find_all(["h3", "span", "div"]):
        text = tag.get_text(strip=True)
        if len(text) > 3 and ("ταινία" in text.lower() or "movie" in text.lower() or len(text) > 8):
            movies.add(text)

    print("Βρέθηκαν τίτλοι:")
    for title in movies:
        print("-", title)

    # Δημιουργία ertflix_playlist.m3u8 με dummy URLs
    with open("ertflix_playlist.m3u8", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for i, title in enumerate(sorted(movies), 1):
            f.write(f'#EXTINF:-1,{title}\nhttps://example.com/movie_{i}.mp4\n')

if __name__ == "__main__":
    main()
