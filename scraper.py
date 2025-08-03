import requests
from bs4 import BeautifulSoup
import time

LIST_URL = "https://www.ertflix.gr/list?pageCodename=movies&sectionCodename=oles-oi-tainies-1&tileCount=300"
DEVICE_KEY = "12b9a6425e59ec1fcee9acb0e7fba4f3"
API_URL = "https://api.app.ertflix.gr/v1/Player/AcquireContent"

headers = {
    "User-Agent": "Mozilla/5.0"
}

def get_codename_from_href(href):
    # href: /vod/vod.635976-oups-o-noe-ephuge
    # codename: oups-o-noe-ephuge
    if "vod." in href and "-" in href:
        return href.split('-')[-4:]
        # This will return a list of last 4 parts, so join:
        # e.g. ['oups', 'o', 'noe', 'ephuge']
    return href.split('/')[-1]

def extract_codename(href):
    # Improved extraction: get everything after the first '-' after 'vod.'
    if "vod." in href:
        return href.split("vod.")[1].split("-")[1:]
    return href.split("/")[-1]

def main():
    response = requests.get(LIST_URL, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    movies = []
    for link in soup.find_all("a", href=True, class_="VideoTile__auditionLink___xcDYk"):
        img = link.find("img", alt=True)
        if img and img["alt"].strip():
            title = img["alt"].strip()
            href = link["href"]
            # Extract codename
            if "vod." in href:
                codename = href.split("vod.")[1].split("-")[1:]
                codename = "-".join(codename)
            else:
                codename = href.split("/")[-1]
            t = int(time.time() * 1000)
            params = {
                "platformCodename": "www",
                "deviceKey": DEVICE_KEY,
                "codename": codename,
                "t": t
            }
            try:
                api_resp = requests.get(API_URL, params=params, headers=headers, timeout=8)
                api_resp.raise_for_status()
                data = api_resp.json()
                # Συνήθως το .m3u8 είναι κάπου στο response, π.χ.:
                # data['sources'][0]['src']
                stream_url = None
                if "MediaFiles" in data and data.get("MediaFiles"):
                    for media_file in data["MediaFiles"]:
                        if "Formats" in media_file and media_file.get("Formats"):
                            for file_format in media_file["Formats"]:
                                # Συνήθως το Type 2 είναι HLS (m3u8)
                                if "Url" in file_format and file_format["Url"].endswith(".m3u8"):
                                    stream_url = file_format["Url"]
                                    break  # Βρέθηκε, έξοδος από τον εσωτερικό βρόχο
                        if stream_url:
                            break  # Βρέθηκε, έξοδος από τον εξωτερικό βρόχο
                if stream_url:
                    movies.append((title, stream_url))
                    print(f"OK: {title} | {stream_url}")
                else:
                    print(f"NO STREAM: {title}")
            except Exception as e:
                print(f"ERROR for {title}: {e}")

    # Φτιάξε το ertflix_playlist.m3u8
    with open("ertflix_playlist.m3u8", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for title, url in movies:
            f.write(f'#EXTINF:-1,{title}\n{url}\n')

if __name__ == "__main__":
    main()
