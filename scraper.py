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

    movies = set()
    # Πάρε τους τίτλους από το alt των <img>
    for img in soup.find_all("img", alt=True):
        title = img["alt"].strip()
        if title:
            movies.add(title)

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
