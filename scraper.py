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

    movies = []
    for link in soup.find_all("a", class_="VideoTile__auditionLink___xcDYk", href=True):
        # Βρες το <img> που είναι μέσα στο <a>
        img = link.find("img", alt=True)
        if img and img["alt"].strip():
            title = img["alt"].strip()
            href = link["href"].strip()
            # Φτιάξε το πλήρες link αν χρειάζεται
            if href.startswith("/"):
                href = "https://www.ertflix.gr" + href
            movies.append((title, href))

    print("Βρέθηκαν τίτλοι:")
    for title, url in movies:
        print("-", title, url)

    # Δημιουργία ertflix_playlist.m3u8
    with open("ertflix_playlist.m3u8", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for title, url in movies:
            f.write(f'#EXTINF:-1,{title}\n{url}\n')

if __name__ == "__main__":
    main()
