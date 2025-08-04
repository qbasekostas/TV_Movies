import requests
import time
import json
import html

# --- API Endpoints (Από το δικό σου script, είναι τα σωστά) ---
LIST_API_URL = "https://api.app.ertflix.gr/v1/InsysGoPage/GetSectionContent"
TILE_DETAIL_API_URL = "https://api.app.ertflix.gr/v1/tile/GetTile"
PLAYER_API_URL = "https://api.app.ertflix.gr/v1/Player/AcquireContent"

# --- Σταθερές ---
DEVICE_KEY = "12b9a6425e59ec1fcee9acb0e7fba4f3"
OUTPUT_FILE = "ertflix_playlist.m3u8" # Όπως το έχεις στο .yml
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://www.ertflix.gr/"
}

# --- ΟΛΕΣ οι πιθανές κατηγορίες ταινιών ---
CATEGORIES = {
    "Όλες οι Ταινίες": "oles-oi-tainies-1",
    "Κωμωδίες": "komodies-1", "Ρομαντικές": "romantikes",
    "Περιπέτειες": "peripeteies-1", "Δραματικές": "dramatikes",
    "Θρίλερ": "copy-of-thriler", "Βιογραφίες": "biographies-1",
    "Σινεφίλ": "sinephil", "Ελληνικός Κινηματογράφος": "ellenikos-kinematographos",
    "Μικρές Ιστορίες": "mikres-istories", "Παιδικές Ταινίες": "paidikes-tainies-1"
}

def main():
    final_playlist = []
    seen_codenames = set() # Για να αποφεύγουμε τις διπλές εγγραφές

    print("--- Έναρξη σάρωσης όλων των κατηγοριών από το API ---")
    
    for category_name, section_codename in CATEGORIES.items():
        print(f"\n>>> Επεξεργασία κατηγορίας: {category_name}")
        try:
            params = {'platformCodename': 'www', 'sectionCodename': section_codename}
            response = requests.get(LIST_API_URL, params=params, headers=HEADERS, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            movies_in_category = data.get('SectionContent', {}).get('TilesIds', [])
            
            if not movies_in_category:
                print("  -> Δεν βρέθηκαν ταινίες σε αυτή την κατηγορία.")
                continue

            print(f"  -> Βρέθηκαν {len(movies_in_category)} ταινίες. Έναρξη επεξεργασίας...")
            
            for index, tile in enumerate(movies_in_category):
                codename = tile.get('Codename')
                if not codename or codename in seen_codenames:
                    continue 
                
                seen_codenames.add(codename)
                title, poster_url = codename, "" # Προεπιλογές
                
                try:
                    # Παίρνουμε τον ελληνικό τίτλο και την εικόνα
                    detail_params = {'platformCodename': 'www', 'codename': codename}
                    detail_resp = requests.get(TILE_DETAIL_API_URL, params=detail_params, headers=HEADERS, timeout=10)
                    if detail_resp.status_code == 200:
                        detail_data = detail_resp.json()
                        title = detail_data.get('Title', codename).strip()
                        title = html.unescape(title)
                        poster_url = detail_data.get('Poster', '')
                    
                    print(f"    Επεξεργασία {index + 1}/{len(movies_in_category)}: {title}")

                    # Παίρνουμε το stream URL
                    player_params = {"platformCodename": "www", "deviceKey": DEVICE_KEY, "codename": codename, "t": int(time.time() * 1000)}
                    player_resp = requests.get(PLAYER_API_URL, params=player_params, headers=HEADERS, timeout=15)
                    
                    if player_resp.status_code == 404: continue
                    player_resp.raise_for_status()
                    player_data = player_resp.json()
                    
                    final_url = None
                    if player_data.get("MediaFiles"):
                        for media_file in player_data["MediaFiles"]:
                            if media_file.get("Formats"):
                                for file_format in media_file["Formats"]:
                                    url = file_format.get("Url", "")
                                    if url.endswith(".m3u8") and "/output1/" not in url:
                                        final_url = url
                                        break
                                    elif url.endswith(".mpd") and not final_url:
                                        final_url = url
                            if final_url and ".m3u8" in final_url: break
                    
                    if final_url and final_url.endswith(".mpd"):
                        final_url = final_url.replace("/index.mpd", "/playlist.m3u8")

                    if final_url:
                        final_playlist.append({'title': title, 'stream_url': final_url, 'poster_url': poster_url, 'group_title': category_name})

                except Exception:
                    pass
                
                time.sleep(0.05)

        except requests.exceptions.RequestException:
            pass

    if not final_playlist:
        print("\nΔεν βρέθηκαν ταινίες με έγκυρο stream.")
        return
        
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for movie in final_playlist:
                logo_tag = f'tvg-logo="{movie["poster_url"]}"' if movie["poster_url"] else ""
                info_line = f'#EXTINF:-1 group-title="{movie["group_title"]}" {logo_tag},{movie["title"]}\n'
                user_agent_line = f'#EXTVLCOPT:user-agent={HEADERS["User-Agent"]}\n'
                f.write(info_line)
                f.write(user_agent_line)
                f.write(f'{movie["stream_url"]}\n')
        print(f"\nΤο αρχείο {OUTPUT_FILE} δημιουργήθηκε με {len(final_playlist)} μοναδικές ταινίες!")
    except IOError as e:
        print(f"\nΣφάλμα εγγραφής στο αρχείο: {e}")

if __name__ == "__main__":
    main()
