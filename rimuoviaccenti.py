import unicodedata
import sys
import time

def remove_accents(input_str):
    """Rimuove i diacritici (accenti) da una stringa."""
    # Normalizza la stringa in NFKD (scompone 'à' in 'a' + '`')
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    # Filtra tenendo solo i caratteri non 'combining' (non-diacritici)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

# --- Configurazione ---
INPUT_FILE = "words.txt"
OUTPUT_FILE = "word_pulito.txt"
# ----------------------

print("Avvio pulizia dizionario...")
start_time = time.time()

all_words = set()
unaccented_to_remove = set()

try:
    # --- Pass 1: Caricamento di tutte le parole uniche ---
    print(f"Pass 1: Caricamento da {INPUT_FILE}...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            # strip() rimuove spazi/newline, lower() standardizza
            word = line.strip().lower()
            if word: # Ignora righe vuote
                all_words.add(word)

    count_read = len(all_words)
    print(f"Lette {count_read} parole uniche.")

    # --- Pass 2: Identificazione duplicati non accentati ---
    print("Pass 2: Identificazione versioni non accentate...")
    
    # Iteriamo sul set appena creato
    for word in all_words:
        unaccented_word = remove_accents(word)
        
        # Caso: "città" -> "citta"
        # 1. word != unaccented_word (vero: "città" != "citta")
        # 2. unaccented_word in all_words (vero: "citta" è nel set)
        if word != unaccented_word and unaccented_word in all_words:
            # Aggiungiamo "citta" (la versione errata) al set da rimuovere
            unaccented_to_remove.add(unaccented_word)
            
        # Caso: "mela" -> "mela"
        # 1. word != unaccented_word (falso: "mela" == "mela")
        # -> Il loop continua, "mela" non viene aggiunto per errore.

    count_removed = len(unaccented_to_remove)
    print(f"Identificate {count_removed} versioni non accentate da rimuovere.")

    # --- Pass 3: Calcolo set finale e scrittura ---
    print(f"Pass 3: Calcolo e scrittura su {OUTPUT_FILE}...")
    
    # Sottrazione tra insiemi: tiene tutto tranne gli elementi in unaccented_to_remove
    final_words = all_words - unaccented_to_remove
    
    count_final = len(final_words)
    
    # Scriviamo il risultato ordinato (opzionale, ma pulito per un dizionario)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        # Convertiamo il set in lista per ordinarlo
        for word in sorted(list(final_words)):
            f.write(f"{word}\n")

    end_time = time.time()
    
    print("\n--- Report Finale ---")
    print(f"Parole uniche lette: {count_read}")
    print(f"Parole errate rimosse: {count_removed}")
    print(f"Parole finali scritte: {count_final}")
    print(f"Tempo di esecuzione: {end_time - start_time:.2f} secondi.")
    print(f"File pulito salvato come: {OUTPUT_FILE}")


except FileNotFoundError:
    print(f"ERRORE: File input '{INPUT_FILE}' non trovato.", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"ERRORE: Si è verificato un errore: {e}", file=sys.stderr)
    sys.exit(1)