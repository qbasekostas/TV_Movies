import requests
import time
import json

# Νέο API endpoint που επιστρέφει τη λίστα ταινιών σε μορφή JSON
# Το limit=500 ζητάει έως 500 ταινίες με μία κλήση
LIST_API_URL = "https://api.app.ertflix.gr/v2/tile/list?platformCodename=www&pageCodename=movies§ionCodename=oles-oi-tainies-1&limit=500&offset=0"

# Αυτά παραμένουν τα ίδια
DEVICE_KEY = "12b9a6425e59ec1fcee9acb0e7fba4f3"
PLAYER_API_URL = "https://api.app.ertflix.gr/v1/Player/AcquireContent"
OUTPUT_FILE = "ertflix_playlist.m3u8"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def main():
    movies = []
    
    print("Λήψη λίστας ταινιών από το API της ERTFLIX...")
    try:
        # Κάνουμε την κλήση στο νέο API για τη λίστα
        list_response = requests.get(LIST_API_URL, headers=headers, timeout=20)
        list_response.raise_for_status()
        list_data = list_response.json()
    except requests.exceptions.RequestException as e:
        print(f"Σφάλμα: Αποτυχία λήψης της λίστας ταινιών από το API. {e}")
        return
    except json.JSONDecodeError:
        print("Σφάλμα: Η απάντηση από το API λίστας ταινιών δεν ήταν έγκυρο JSON.")
        return

    # Ελέγχουμε αν υπάρχουν ταινίες στην απάντηση
    if not list_data or 'tiles' not in list_data or not list_data['tiles']:
        print("Δεν βρέθηκαν ταινίες στην απάντηση του API. Η δομή μπορεί να έχει αλλάξει.")
        return

    movie_tiles = list_data['tiles']
    print(f"Βρέθηκαν {len(movie_tiles)} ταινίες. Έναρξη επεξεργασίας για λήψη stream URL...")

    for tile in movie_tiles:
        # Το 'title' και το 'codename' είναι πλέον απευθείας διαθέσιμα στο JSON
        title = tile.get('title', 'Unknown Title').strip()
        codename = tile.get('codename')

        if not codename:
            print(f"INFO: Παράλειψη '{title}' καθώς δεν έχει codename.")
            continue

        t = int(time.time() * 1000)
        params = {
            "platformCodename": "www",
            "deviceKey": DEVICE_KEY,
            "codename": codename,
            "t": t
        }
        
        try:
            api_resp = requests.get(PLAYER_API_URL, params=params, headers=headers, timeout=10)
            api_resp.raise_for_status()
            data = api_resp.json()
            
            stream_url = None
            if data.get("MediaFiles"):
                for media_file in data["MediaFiles"]:
                    if media_file.get("Formats"):
                        for file_format in media_file["Formats"]:
                            if file_format.get("Url", "").endswith(".m3u8"):
                                stream_url = file_format["Url"]
                                break
                    if stream_url:
                        break

            if stream_url:
                movies.append((title, stream_url))
                print(f"OK: {title}")
            else:
                print(f"NO STREAM: {title}")
        except requests.exceptions.HTTPError as http_err:
            if http_err.response.status_code == 404:
                print(f"INFO: Το περιεχόμενο για '{title}' δεν είναι πλέον διαθέσιμο (404).")
            else:
                print(f"HTTP ERROR for {title}: {http_err}")
        except requests.exceptions.RequestException as req_err:
            print(f"REQUEST ERROR for {title}: {req_err}")
        except Exception as e:
            print(f"GENERIC ERROR for {title}: {e}")
        
        # Μικρή καθυστέρηση για να είμαστε καλοί με τον server
        time.sleep(0.2)

    if not movies:
        print("\nΔεν βρέθηκαν ταινίες με έγκυρο stream για δημιουργία λίστας.")
        return

    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for title, url in movies:
                f.write(f'#EXTINF:-1,{title}\n{url}\n')
        print(f"\nΤο αρχείο {OUTPUT_FILE} δημιουργήθηκε με επιτυχία με {len(movies)} ταινίες!")
    except IOError as e:
        print(f"\nΣφάλμα: Αποτυχία εγγραφής στο αρχείο: {e}")

if __name__ == "__main__":
    main()
