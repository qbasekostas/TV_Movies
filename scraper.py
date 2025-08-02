import requests
import os

# Το σωστό URL που δώσατε
URL = "https://www.ertflix.gr/list?pageCodename=movies&backUrl=/show/movies&sectionCodename=oles-oi-tainies-1"
OUTPUT_FILE = "debug_output.html" # Το αρχείο εξόδου για διάγνωση

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def main():
    """
    Αυτή η συνάρτηση απλά κατεβάζει το περιεχόμενο της σελίδας
    και το αποθηκεύει σε ένα αρχείο HTML για να το εξετάσουμε.
    """
    print(f"Attempting to download page source from: {URL}")
    try:
        response = requests.get(URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        print(f"Successfully downloaded page. Saving content to {OUTPUT_FILE}...")
        
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(response.text)
            
        print("File saved successfully.")

    except requests.RequestException as e:
        error_message = f"Failed to download the page. Error: {e}"
        print(error_message)
        # Γράφουμε το σφάλμα στο αρχείο για να το δούμε
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(error_message)

if __name__ == "__main__":
    main()
