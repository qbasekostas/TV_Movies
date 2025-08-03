import requests
import json

# Τα στοιχεία παραμένουν τα ίδια
LIST_API_URL = "https://api.app.ertflix.gr/v1/InsysGoPage/GetSectionContent"
LIST_API_PARAMS = {
    'platformCodename': 'www',
    'sectionCodename': 'oles-oi-tainies-1'
}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def debug_api_response():
    print("--- ΕΝΑΡΞΗ ΔΙΕΡΕΥΝΗΣΗΣ API ---")
    print(f"URL Κλήσης: {LIST_API_URL}")
    print(f"Παράμετροι: {LIST_API_PARAMS}")
    
    try:
        response = requests.get(LIST_API_URL, params=LIST_API_PARAMS, headers=HEADERS, timeout=20)
        response.raise_for_status()
        
        print("\n--- ΑΠΑΝΤΗΣΗ ΕΠΙΤΥΧΗΣ (STATUS CODE 200) ---")
        
        # Προσπαθούμε να τυπώσουμε το JSON με όμορφο τρόπο
        try:
            api_data = response.json()
            print("\n--- ΠΕΡΙΕΧΟΜΕΝΟ JSON ---")
            # Η εντολή json.dumps με indent=2 το κάνει ευανάγνωστο
            print(json.dumps(api_data, indent=2, ensure_ascii=False))
            
        except json.JSONDecodeError:
            print("\n--- ΣΦΑΛΜΑ: Η απάντηση δεν είναι έγκυρο JSON. ---")
            print("--- ΑΚΑΤΕΡΓΑΣΤΟ ΚΕΙΜΕΝΟ ΑΠΑΝΤΗΣΗΣ ---")
            print(response.text)

    except requests.exceptions.RequestException as e:
        print(f"\n--- ΣΦΑΛΜΑ ΚΛΗΣΗΣ API ---")
        print(f"Σφάλμα: {e}")
        if e.response:
            print(f"Status Code: {e.response.status_code}")
            print(f"Response Body: {e.response.text}")

    print("\n--- ΛΗΞΗ ΔΙΕΡΕΥΝΗΣΗΣ API ---")

if __name__ == "__main__":
    debug_api_response()
