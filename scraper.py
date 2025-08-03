import requests
import json

# Το API που φορτώνει την πρώτη σελίδα
INITIAL_LOAD_URL = "https://api.app.ertflix.gr/v1/InsysGoPage/GetSectionContent"
PARAMS = {
    'platformCodename': 'www',
    'sectionCodename': 'oles-oi-tainies-1'
}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def debug_initial_load():
    print("--- ΔΙΕΡΕΥΝΗΣΗ ΑΡΧΙΚΗΣ ΚΛΗΣΗΣ API ---")
    print(f"URL: {INITIAL_LOAD_URL}")
    print(f"Params: {PARAMS}")

    try:
        response = requests.get(INITIAL_LOAD_URL, params=PARAMS, headers=HEADERS, timeout=20)
        response.raise_for_status()

        print("\n--- ΑΠΑΝΤΗΣΗ ΕΠΙΤΥΧΗΣ (STATUS CODE 200) ---")

        try:
            api_data = response.json()
            print("\n--- ΠΕΡΙΕΧΟΜΕΝΟ JSON (ΜΕ ΜΟΡΦΟΠΟΙΗΣΗ) ---")
            # Η εντολή json.dumps με indent=2 το κάνει ευανάγνωστο
            print(json.dumps(api_data, indent=2, ensure_ascii=False))

        except json.JSONDecodeError:
            print("\n--- ΣΦΑΛΜΑ: Η απάντηση δεν είναι έγκυρο JSON. ---")
            print("--- ΑΚΑΤΕΡΓΑΣΤΟ ΚΕΙΜΕΝΟ ΑΠΑΝΤΗΣΗΣ ---")
            print(response.text)

    except requests.exceptions.RequestException as e:
        print(f"\n--- ΣΦΑΛΜΑ ΚΛΗΣΗΣ API ---")
        print(f"Σφάλμα: {e}")

    print("\n--- ΤΕΛΟΣ ΔΙΕΡΕΥΝΗΣΗΣ ---")

if __name__ == "__main__":
    debug_initial_load()
