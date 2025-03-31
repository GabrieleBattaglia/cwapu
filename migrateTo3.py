import pickle
import json
import os
import datetime as dt

# Nomi dei vecchi file pickle
OLD_OVERALL_FILE = "CWapu_Overall.pkl"
OLD_RXING_FILE = "CWapu_Rxing.pkl"
OLD_INDEX_FILE = "CWapu_Index.pkl"

# Nome del nuovo file JSON (deve corrispondere a quello nel main script)
NEW_SETTINGS_FILE = "cwapu_settings.json"

# Struttura dati di default (copiata/adattata dal main script)
DEFAULT_DATA = {
    "app_info": {
        "launch_count": 0 # La migrazione non imposta il lancio, verrà fatto dal main
    },
    "overall_settings": {
        "app_language": "en", "speed": 18, "pitch": 550, "dashes": 30,
        "spaces": 50, "dots": 50, "volume": 0.5, "ms": 1,
        "fs_index": 5, "wave_index": 1
    },
    "rxing_stats": {
        "total_calls": 0, "sessions": 1, "total_correct": 0,
        "total_wrong_items": 0, "total_time_seconds": 0.0
    },
    "counting_stats": {
        "exercise_number": 1
    }
}

def migrate():
    print("Avvio migrazione impostazioni da .pkl a .json...")
    # Parti sempre dalla struttura di default per assicurarti che tutte le chiavi esistano
    migrated_data = DEFAULT_DATA.copy()
    # Usa deep copy se hai dizionari annidati complessi, ma qui copy() è sufficiente
    # import copy
    # migrated_data = copy.deepcopy(DEFAULT_DATA)

    # 1. Migrazione CWapu_Overall.pkl
    try:
        if os.path.exists(OLD_OVERALL_FILE):
            with open(OLD_OVERALL_FILE, "rb") as f:
                (app_language, overall_speed, overall_pitch, overall_dashes,
                 overall_spaces, overall_dots, overall_volume, overall_ms,
                 overall_fs, overall_wave) = pickle.load(f)

            # Sovrascrivi la sezione di default con i dati caricati
            migrated_data['overall_settings'] = {
                "app_language": app_language,
                "speed": overall_speed,
                "pitch": overall_pitch,
                "dashes": overall_dashes,
                "spaces": overall_spaces,
                "dots": overall_dots,
                "volume": overall_volume,
                "ms": overall_ms,
                "fs_index": overall_fs,
                "wave_index": overall_wave
            }
            print(f"- Dati da {OLD_OVERALL_FILE} caricati.")
        else:
            print(f"- File {OLD_OVERALL_FILE} non trovato, uso i default per overall_settings.")
    except (IOError, pickle.UnpicklingError, EOFError, ValueError, TypeError) as e:
        print(f"- ERRORE nel caricare {OLD_OVERALL_FILE}: {e}. Uso i default per overall_settings.")

    # 2. Migrazione CWapu_Rxing.pkl
    try:
        if os.path.exists(OLD_RXING_FILE):
            with open(OLD_RXING_FILE, "rb") as f:
                # Assumi che l'ordine nel pkl fosse: [totalcalls, sessions, totalget, totalwrong, totaltime]
                rx_data = pickle.load(f)
                totalcalls, sessions, totalget, totalwrong, totaltime = rx_data

            total_time_seconds = 0.0
            if isinstance(totaltime, dt.timedelta):
                total_time_seconds = totaltime.total_seconds()
            elif isinstance(totaltime, (int, float)): # Gestisce se per caso era già un numero
                 total_time_seconds = float(totaltime)

            # Sovrascrivi la sezione di default con i dati caricati
            migrated_data['rxing_stats'] = {
                "total_calls": totalcalls,
                "sessions": sessions,
                "total_correct": totalget,
                "total_wrong_items": totalwrong,
                "total_time_seconds": total_time_seconds
            }
            print(f"- Dati da {OLD_RXING_FILE} caricati.")
        else:
             print(f"- File {OLD_RXING_FILE} non trovato, uso i default per rxing_stats.")
    except (IOError, pickle.UnpicklingError, EOFError, ValueError, TypeError, IndexError) as e: # Aggiunto IndexError
        print(f"- ERRORE nel caricare o processare {OLD_RXING_FILE}: {e}. Uso i default per rxing_stats.")


    # 3. Migrazione CWapu_Index.pkl
    try:
        if os.path.exists(OLD_INDEX_FILE):
             with open(OLD_INDEX_FILE, "rb") as f:
                 esnum = pickle.load(f)
             # Aggiorna solo il valore specifico nella sezione di default
             migrated_data['counting_stats']['exercise_number'] = esnum
             print(f"- Dati da {OLD_INDEX_FILE} caricati.")
        else:
            print(f"- File {OLD_INDEX_FILE} non trovato, uso i default per counting_stats.")
    except (IOError, pickle.UnpicklingError, EOFError, ValueError, TypeError) as e:
        print(f"- ERRORE nel caricare {OLD_INDEX_FILE}: {e}. Uso i default per counting_stats.")

    # 4. Salvataggio nel nuovo file JSON
    try:
        with open(NEW_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(migrated_data, f, indent=4, ensure_ascii=False)
        print(f"\nMigrazione completata con successo! I dati sono stati salvati in {NEW_SETTINGS_FILE}")
        print("ATTENZIONE: Puoi ora cancellare i vecchi file .pkl (dopo aver verificato!):")
        print(f"- {OLD_OVERALL_FILE}")
        print(f"- {OLD_RXING_FILE}")
        print(f"- {OLD_INDEX_FILE}")
    except IOError as e:
        print(f"\nERRORE CRITICO nel salvare il file JSON {NEW_SETTINGS_FILE}: {e}")
    except TypeError as e:
        print(f"\nERRORE CRITICO di tipo durante la scrittura JSON: {e}")

if __name__ == "__main__":
    # Verifica se il file JSON esiste già per evitare sovrascritture accidentali
    if os.path.exists(NEW_SETTINGS_FILE):
        confirm = input(f"ATTENZIONE: Il file {NEW_SETTINGS_FILE} esiste già.\nContinuando lo sovrascriverai con i dati migrati dai file .pkl (se trovati).\nSei sicuro di voler continuare? (s/N): ")
        if confirm.lower() != 's':
            print("Migrazione annullata.")
            exit()
    migrate()