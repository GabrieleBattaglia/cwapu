# CWAPUDEV - Utility per il CW, di Gabry, IZ4APU
# Data concepimento 21/12/2022.
# GitHub publishing on july 2nd, 2024.

import datetime as dt
import difflib
import json
import os
import random
import re
import string
import sys
import time
import traceback

import pyperclip
from GBUtils import CWzator, Donazione, dgt, enter_escape, key, menu, polipo
from pynput import keyboard

from grafico import crea_report_grafico
from wilson import wilson_score_lower_bound, wilson_score_upper_bound

# installazione percorsi relativi e i18n
APP_DIR = os.path.dirname(os.path.abspath(__file__))


def get_user_data_path():
    """Restituisce un percorso scrivibile per i dati utente.

    Da eseguibile PyInstaller e' la cartella dell'eseguibile, da sorgente e'
    la cartella dello script. Mai la directory di lavoro: lanciando cwapu da
    un'altra cartella si perderebbero impostazioni, archivio storico e diario.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return APP_DIR


USER_DATA_PATH = get_user_data_path()


def resource_path(relative_path):
    """
    Restituisce il percorso assoluto a una risorsa, funzionante sia in sviluppo
    che per un eseguibile compilato con PyInstaller (anche con la cartella _internal).
    """
    base_path = getattr(sys, "_MEIPASS", None)
    if base_path is None:
        # Fuori da PyInstaller, o in una build onedir, la risorsa sta accanto
        # al programma: mai nella directory di lavoro del momento.
        base_path = USER_DATA_PATH
    return os.path.join(base_path, relative_path)


def user_file_path(nome_file):
    """Percorso di una risorsa che l'utente puo' sostituire con una propria copia.

    Ha la precedenza il file messo accanto al programma; se non c'e', si usa
    quello incluso nel pacchetto.
    """
    percorso_utente = os.path.join(USER_DATA_PATH, nome_file)
    if os.path.exists(percorso_utente):
        return percorso_utente
    return resource_path(nome_file)


app_language, _ = polipo(source_language="it")

# QC Costanti
VERSION = "6.0.0"
RELEASE_DATE = "2026-09-07"
# Tetto unico della velocita' per tutta l'applicazione, uguale a quello che
# CWzator V10 accetta. Prima ce n'erano quattro diversi, e il piu' basso, 85,
# era quello che chi riceve veloce incontrava per primo.
WPM_MIN = 5
WPM_MAX = 120
RX_ITEM_TIMEOUT_SECONDS = 30  # Tempo massimo per item prima di considerarlo una pausa
RX_LSP_VARIATION_PROBABILITY = 0.3
RX_LSP_RANGE_L = (30, 60)
RX_LSP_RANGE_S = (25, 75)
RX_LSP_RANGE_P = (15, 50)
SAMPLE_RATES = [8000, 11025, 16000, 22050, 32000, 44100, 48000, 88200, 96000, 176400, 192000, 384000]
WAVE_TYPES = ["sine", "square", "triangle", "sawtooth"]
SETTINGS_FILE = os.path.join(USER_DATA_PATH, "cwapu_settings.json")
DIARY_NAME = "CWapu_Diary.txt"
DIARY_FILE = os.path.join(USER_DATA_PATH, DIARY_NAME)
MANUALE_NAME = "Manuale_CWapu.html"
# Le voci del menu principale: dati, non logica, quindi stanno fra le costanti
# e si possono leggere anche da fuori, per esempio dalle prove automatiche.
MNMAIN = {
    "c": _("Risultati conteggio"),
    "g": _("Guida in linea, il manuale di CWapu"),
    "k": _("Tastiera ed impostazioni CW"),
    "l": _("Ascolta gli appunti in CW"),
    "m": _("Mostra Menu"),
    "q": _("Per uscire da questa app"),
    "r": _("Esercizio di ricezione"),
    "s": _("Statistiche sull'archivio storico"),
    "t": _("Esercizio di trasmissione simulata"),
    "w": _("Crea dizionario personalizzato"),
}
FINE_RECORD_DIARIO = _("Fine del rapporto.") + "\n"
# I tipi di esercizio si mescolano solo se producono statistiche confrontabili.
# Parole, qrz e contest sono esclusivi, perche' ricevere una parola, un
# nominativo o uno scambio di contest sono mestieri diversi e metterli nella
# stessa media la svuota di senso. Tutto cio' che e' un gruppo di caratteri,
# compreso il gruppo personalizzato dei caratteri problematici, sta invece
# nello stesso gruppo e si puo' accendere insieme.
RX_SWITCHER_ITEMS = [
    # key_state e' la chiave con cui lo stato viene salvato su disco e non si
    # traduce mai; etichetta e' cio' che l'utente legge e si traduce sempre.
    {"id": "1", "key_state": "parole", "etichetta": _("parole"), "is_exclusive": True, "category_group": "WORDS"},
    {"id": "2", "key_state": "lettere", "etichetta": _("lettere"), "is_exclusive": False, "category_group": "CHARS"},
    {"id": "3", "key_state": "numeri", "etichetta": _("numeri"), "is_exclusive": False, "category_group": "CHARS"},
    {"id": "4", "key_state": "lettere e numeri", "etichetta": _("lettere e numeri"), "is_exclusive": False, "category_group": "CHARS"},
    {"id": "5", "key_state": "simboli", "etichetta": _("simboli"), "is_exclusive": False, "category_group": "CHARS"},
    {"id": "6", "key_state": "custom", "etichetta": _("custom"), "is_exclusive": False, "category_group": "CHARS"},
    {"id": "7", "key_state": "qrz", "etichetta": "qrz", "is_exclusive": True, "category_group": "QRZ"},
    {"id": "8", "key_state": "contest", "etichetta": _("contest"), "is_exclusive": True, "category_group": "QRZ"},
]
HISTORICAL_RX_MAX_SESSIONS_DEFAULT = 730
HISTORICAL_RX_REPORT_INTERVAL = 3500

# Caricamento database QRZ reali (MASTER.SCP)
REAL_CALLS_POOL = []
MASTER_SCP_PATH = resource_path("MASTER.SCP")


def load_master_scp():
    """Carica il database dei nominativi reali, avvisando quando non c'e'."""
    global REAL_CALLS_POOL
    if not os.path.exists(MASTER_SCP_PATH):
        print(_("Attenzione: MASTER.SCP non trovato.\n\tNegli esercizi QRZ userò solo nominativi inventati."))
        return
    try:
        with open(MASTER_SCP_PATH, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        calls = [x.strip() for x in lines if not x.startswith("#")]
        REAL_CALLS_POOL = sorted(set(calls))
    except OSError as e:
        print(_("Attenzione: MASTER.SCP non leggibile ({errore}).\n\tNegli esercizi QRZ userò solo nominativi inventati.").format(errore=e))


load_master_scp()

VALID_MORSE_CHARS_FOR_CUSTOM_SET = {k for k in CWzator(get_map=True) if k != " " and k.isprintable()}
LETTERE_MORSE_POOL = {k for k in VALID_MORSE_CHARS_FOR_CUSTOM_SET if k in set(string.ascii_lowercase)}
NUMERI_MORSE_POOL = {k for k in VALID_MORSE_CHARS_FOR_CUSTOM_SET if k in set(string.digits)}
SIMBOLI_MORSE_POOL = VALID_MORSE_CHARS_FOR_CUSTOM_SET - LETTERE_MORSE_POOL - NUMERI_MORSE_POOL
DEFAULT_DATA = {
    "app_info": {"launch_count": 0},
    "overall_settings": {"app_language": "en", "speed": 18, "pitch": 550, "dashes": 30, "spaces": 50, "dots": 50, "volume": 0.5, "ms": 1, "fs_index": 5, "wave_index": 1},
    "rxing_stats_words": {"total_calls": 0, "sessions": 0, "total_correct": 0, "total_wrong_items": 0, "total_time_seconds": 0.0},
    "rxing_stats_chars": {"total_calls": 0, "sessions": 0, "total_correct": 0, "total_wrong_items": 0, "total_time_seconds": 0.0},
    "rxing_stats_qrz": {"total_calls": 0, "sessions": 0, "total_correct": 0, "total_wrong_items": 0, "total_time_seconds": 0.0},
    "counting_stats": {"exercise_number": 1},
    "rx_menu_switcher_states": {
        "parole": True,
        "lettere": False,
        "numeri": False,
        "lettere e numeri": False,
        "simboli": False,
        "qrz": False,
        "custom": False,
        "contest": False,
        "parole_filter_min": 3,
        "parole_filter_max": 7,
        "custom_set_string": "",
    },
    "historical_rx_settings": {
        "max_sessions_to_keep": HISTORICAL_RX_MAX_SESSIONS_DEFAULT,
        "report_interval": HISTORICAL_RX_REPORT_INTERVAL,
    },
    "historical_rx_data_words": {"chars_since_last_report": 0, "sessions_log": [], "historical_reports": []},
    "historical_rx_data_chars": {"chars_since_last_report": 0, "sessions_log": [], "historical_reports": []},
    "historical_rx_data_qrz": {"chars_since_last_report": 0, "sessions_log": [], "historical_reports": []},
}
MDL = {"a0a": 4, "a0aa": 6, "a0aaa": 15, "aa0a": 6, "aa0aa": 18, "aa0aaa": 36, "0a0a": 2, "0a0aa": 2, "0a0aaa": 2, "a00a": 3, "a00aa": 3, "a00aaa": 4}
words = []
app_data = {}


def _clear_screen_ansi():
    """Pulisce lo schermo usando ANSI e posiziona il cursore in alto a sinistra."""
    sys.stdout.write("\x1b[2J")
    sys.stdout.write("\x1b[H")
    sys.stdout.flush()


def limita_wpm(velocita):
    """Riporta una velocita' dentro i limiti che il motore CW accetta."""
    return max(WPM_MIN, min(WPM_MAX, int(velocita)))


def suona(msg, wpm=None, pitch=None, l=None, s=None, p=None, sync=False, to_file=False, avvisa=True):
    """Manda un messaggio al motore CW con le impostazioni correnti dell'utente.

    Raccoglie i dieci parametri che ogni chiamata ripeteva identici e lascia
    al chiamante soltanto cio' che cambia davvero. Restituisce la coppia
    (handle, velocita' effettiva) di CWzator. Quando la libreria rifiuta il
    messaggio restituisce (None, 0.0) e lo dice: prima si proseguiva in
    silenzio e l'utente restava senza suono senza sapere perche'.
    """
    handle, rwpm = CWzator(
        msg=msg,
        wpm=limita_wpm(overall_speed if wpm is None else wpm),
        pitch=overall_pitch if pitch is None else pitch,
        l=overall_dashes if l is None else l,
        s=overall_spaces if s is None else s,
        p=overall_dots if p is None else p,
        vol=overall_volume,
        ms=overall_ms,
        fs=SAMPLE_RATES[overall_fs],
        wv=overall_wave,
        sync=sync,
        to_file=to_file,
    )
    if handle is None:
        if avvisa:
            print(_("Il motore CW non ha trasmesso il messaggio: {errore}").format(errore=getattr(CWzator, "ultimo_errore", None)))
        return None, 0.0
    return handle, rwpm


def genera_singolo_item_esercizio_misto(active_switcher_states, group_length_for_generated, custom_set_active_string, parole_filtrate_list):
    active_and_usable_kinds = []
    if active_switcher_states.get("parole") and parole_filtrate_list:
        active_and_usable_kinds.append("parole")
    if active_switcher_states.get("lettere"):
        active_and_usable_kinds.append("lettere")
    if active_switcher_states.get("numeri"):
        active_and_usable_kinds.append("numeri")
    if active_switcher_states.get("lettere e numeri"):
        active_and_usable_kinds.append("lettere e numeri")
    if active_switcher_states.get("simboli"):
        active_and_usable_kinds.append("simboli")
    if active_switcher_states.get("qrz"):
        active_and_usable_kinds.append("qrz")
    if active_switcher_states.get("custom") and custom_set_active_string and (len(custom_set_active_string) >= 2):
        active_and_usable_kinds.append("custom")
    if not active_and_usable_kinds:
        return "ERROR_NO_VALID_TYPES"
    chosen_kind = random.choice(active_and_usable_kinds)
    item_generato = ""
    if chosen_kind == "parole":
        item_generato = random.choice(parole_filtrate_list)
    elif chosen_kind == "qrz":
        random_mdl_key_list = random.choices(list(MDL.keys()), weights=list(MDL.values()), k=1)
        item_generato = Mkdqrz(random_mdl_key_list)
    elif chosen_kind == "custom":
        item_generato = GeneratingGroup(kind="4", length=group_length_for_generated, wpm=overall_speed, customized_set_param=custom_set_active_string)
    elif chosen_kind == "lettere":
        item_generato = GeneratingGroup(kind="1", length=group_length_for_generated, wpm=overall_speed)
    elif chosen_kind == "numeri":
        item_generato = GeneratingGroup(kind="2", length=group_length_for_generated, wpm=overall_speed)
    elif chosen_kind == "lettere e numeri":
        item_generato = GeneratingGroup(kind="3", length=group_length_for_generated, wpm=overall_speed)
    elif chosen_kind == "simboli":
        item_generato = GeneratingGroup(kind="S", length=group_length_for_generated, wpm=overall_speed)
    return item_generato.lower()


def applica_esclusione_switcher(stati, chiave_accesa):
    """Spegne gli switcher incompatibili con quello appena acceso.

    Restano accesi soltanto quelli del suo stesso gruppo, e nessuno se lo
    switcher acceso e' esclusivo o se lo e' l'altro. Cosi' nella stessa
    sessione, e quindi nella stessa statistica, finiscono solo cose che ha
    senso confrontare fra loro.
    """
    acceso = next((v for v in RX_SWITCHER_ITEMS if v["key_state"] == chiave_accesa), None)
    if acceso is None:
        return stati
    mio_gruppo = acceso.get("category_group")
    sono_esclusivo = acceso.get("is_exclusive", False)
    for altro in RX_SWITCHER_ITEMS:
        if altro["key_state"] == chiave_accesa:
            continue
        if sono_esclusivo or altro.get("is_exclusive") or altro.get("category_group") != mio_gruppo:
            stati[altro["key_state"]] = False
    return stati


def seleziona_modalita_rx():
    switcher_settings_key = "rx_menu_switcher_states"
    if switcher_settings_key not in app_data:
        app_data[switcher_settings_key] = DEFAULT_DATA[switcher_settings_key].copy()
    current_switcher_states = app_data[switcher_settings_key].copy()
    parole_filtrate_sessione = None
    custom_set_string_sessione = current_switcher_states.get("custom_set_string", "")
    if current_switcher_states.get("parole"):
        min_len = current_switcher_states.get("parole_filter_min", 0)
        max_len = current_switcher_states.get("parole_filter_max", 0)
        if min_len > 0 and max_len > 0 and (min_len <= max_len):
            parole_filtrate_sessione = [w for w in words if len(w) >= min_len and len(w) <= max_len]
            if not parole_filtrate_sessione:
                current_switcher_states["parole"] = False
        else:
            current_switcher_states["parole"] = False
    if current_switcher_states.get("custom") and (not custom_set_string_sessione):
        current_switcher_states["custom"] = False
    MENU_BASE_ROW = 3
    user_message_line_row = MENU_BASE_ROW + len(RX_SWITCHER_ITEMS) + 1
    prompt_actual_line_row = MENU_BASE_ROW + len(RX_SWITCHER_ITEMS) + 2

    def _display_single_switcher_line(index, is_on_state):
        item_config = RX_SWITCHER_ITEMS[index]
        riga_da_scrivere = MENU_BASE_ROW + index
        _move_cursor(riga_da_scrivere, 1)
        label_text_trans = item_config["etichetta"]
        status_marker = "<X>" if is_on_state else "< >"
        status_text_trans = _("ATTIVATO") if is_on_state else _("disattivato")
        display_label_cased = label_text_trans.upper() if is_on_state else label_text_trans.lower()
        line_output = "{}. {display_label_cased} {status_marker} {status_text_trans}".format(
            item_config["id"], display_label_cased=display_label_cased, status_marker=status_marker, status_text_trans=status_text_trans
        )
        sys.stdout.write(line_output)
        _clear_line_from_cursor()
        sys.stdout.flush()

    def _redraw_menu_interface_for_key_prompt(current_states_dict, message_for_user=""):
        _move_cursor(MENU_BASE_ROW - 1, 1)
        sys.stdout.write(_("Esercizi Rx - Seleziona Tipi (Invio per iniziare):"))
        _clear_line_from_cursor()
        print()
        for idx_redraw, item_config_redraw in enumerate(RX_SWITCHER_ITEMS):
            _display_single_switcher_line(idx_redraw, current_states_dict[item_config_redraw["key_state"]])
        _move_cursor(user_message_line_row, 1)
        if message_for_user:
            sys.stdout.write(message_for_user)
            _clear_line_from_cursor()
        else:
            _clear_line_from_cursor()
        status_display_parts = []
        for item_cfg_key_prompt in RX_SWITCHER_ITEMS:
            is_on_key_prompt = current_states_dict.get(item_cfg_key_prompt["key_state"], False)
            status_display_parts.append("[{}]".format(item_cfg_key_prompt["id"]) if is_on_key_prompt else "<{}>".format(item_cfg_key_prompt["id"]))
        _move_cursor(prompt_actual_line_row, 1)
        _clear_line_from_cursor()
        sys.stdout.flush()
        return " ".join(status_display_parts) + ": "

    user_message_content = ""
    while True:
        prompt_string = _redraw_menu_interface_for_key_prompt(current_switcher_states, user_message_content)
        user_message_content = ""
        scelta = key(prompt=prompt_string)
        if not scelta or scelta == "\r":
            active_switches_final = [item["key_state"] for item in RX_SWITCHER_ITEMS if current_switcher_states.get(item["key_state"])]
            if not active_switches_final:
                user_message_content = _("Nessuna modalità di esercizio selezionata! Attiva almeno uno switcher.")
                suona("?")
                continue
            if current_switcher_states.get("parole") and (not parole_filtrate_sessione):
                user_message_content = _("Errore: 'Parole' attivo ma il filtro non è impostato o non produce risultati. Usa '.t #-#'.")
                suona("?")
                continue
            if current_switcher_states.get("custom") and (not custom_set_string_sessione or len(custom_set_string_sessione) < 2):
                user_message_content = _("Errore: il set personalizzato non è valido o è vuoto. Controlla le impostazioni.")
                suona("?")
                continue
            group_len_val_final = 0
            ask_for_length = False
            if (
                current_switcher_states.get("lettere")
                or current_switcher_states.get("numeri")
                or current_switcher_states.get("custom")
                or current_switcher_states.get("lettere e numeri")
                or current_switcher_states.get("simboli")
            ):
                ask_for_length = True
            if ask_for_length:
                _move_cursor(prompt_actual_line_row + 1, 1)
                prompt_len_text_final = _("Lunghezza gruppi (1-7 per Lettere/Numeri/Simboli/Custom):")
                sys.stdout.write(prompt_len_text_final)
                _clear_line_from_cursor()
                sys.stdout.flush()
                _move_cursor(prompt_actual_line_row + 1, len(prompt_len_text_final) + 1)
                len_str_final = input()
                if len_str_final.isdigit() and 1 <= int(len_str_final) <= 7:
                    group_len_val_final = int(len_str_final)
                else:
                    user_message_content = _("Lunghezza non valida. Inserire un numero da 1 a 7.")
                    suona("?")
                    continue
            app_data[switcher_settings_key].update(current_switcher_states)
            for i_clean_final in range(len(RX_SWITCHER_ITEMS) + 4):
                _move_cursor(MENU_BASE_ROW - 1 + i_clean_final, 1)
                _clear_line_from_cursor()
            _move_cursor(MENU_BASE_ROW, 1)
            return {
                "active_switcher_states": current_switcher_states,
                "parole_filtrate_list": parole_filtrate_sessione if current_switcher_states.get("parole") else None,
                "custom_set_string_active": custom_set_string_sessione if current_switcher_states.get("custom") else None,
                "group_length_for_generated": group_len_val_final,
            }
        if scelta.isdigit() and "1" <= scelta <= str(len(RX_SWITCHER_ITEMS)):
            chosen_idx = int(scelta) - 1
            item_config_toggled = RX_SWITCHER_ITEMS[chosen_idx]
            item_key_toggle_loop = item_config_toggled["key_state"]

            # Toggle dello stato
            current_switcher_states[item_key_toggle_loop] = not current_switcher_states[item_key_toggle_loop]
            is_now_active = current_switcher_states[item_key_toggle_loop]
            if is_now_active:
                applica_esclusione_switcher(current_switcher_states, item_key_toggle_loop)

            if is_now_active:
                if item_key_toggle_loop == "parole":
                    min_len_saved_loop = current_switcher_states.get("parole_filter_min", 0)
                    max_len_saved_loop = current_switcher_states.get("parole_filter_max", 0)
                    if not (min_len_saved_loop > 0 and max_len_saved_loop > 0 and (min_len_saved_loop <= max_len_saved_loop)):
                        user_message_content = _("Filtro parole non impostato/valido. Usa il comando '.t #-#' nelle Impostazioni (k). Switcher 'Parole' disattivato.")
                        current_switcher_states["parole"] = False
                        parole_filtrate_sessione = None
                    else:
                        parole_filtrate_sessione = [w for w in words if len(w) >= min_len_saved_loop and len(w) <= max_len_saved_loop]
                        if not parole_filtrate_sessione:
                            user_message_content = _("Filtro parole caricato dalle impostazioni non ha prodotto risultati. Switcher 'Parole' disattivato.")
                            current_switcher_states["parole"] = False
                        else:
                            user_message_content = _("Filtro parole applicato dalle impostazioni ({count} parole).").format(count=len(parole_filtrate_sessione))
                elif item_key_toggle_loop == "custom":
                    if not custom_set_string_sessione or len(custom_set_string_sessione) < 2:
                        for i_clean_cs in range(len(RX_SWITCHER_ITEMS) + 4):
                            _move_cursor(MENU_BASE_ROW - 1 + i_clean_cs, 1)
                            _clear_line_from_cursor()
                        _move_cursor(1, 1)
                        sys.stdout.write(_("Avvio configurazione gruppo personalizzato...") + "\n\n")
                        sys.stdout.flush()
                        custom_set_string_nuovo = CustomSet(overall_speed)
                        if len(custom_set_string_nuovo) >= 2:
                            custom_set_string_sessione = custom_set_string_nuovo
                            current_switcher_states["custom_set_string"] = custom_set_string_nuovo
                        else:
                            user_message_content = _("Gruppo Custom non creato o non valido. Switcher 'Custom' disattivato.")
                            current_switcher_states["custom"] = False
                            custom_set_string_sessione = ""
                            current_switcher_states["custom_set_string"] = ""
                    else:
                        user_message_content = _("Gruppo Custom caricato dalle impostazioni: [{set_string}]").format(set_string=custom_set_string_sessione)
        else:
            user_message_content = _("Scelta non valida.")
            suona("?")
    return None


def _move_cursor(riga, colonna):
    """Muove il cursore alla riga e colonna specificata (1-based)."""
    sys.stdout.write(f"\x1b[{riga};{colonna}H")


def _clear_line_from_cursor():
    """Pulisce la linea dalla posizione attuale del cursore fino alla fine."""
    sys.stdout.write("\x1b[K")


def load_settings():
    """Carica le impostazioni dal file JSON o restituisce i default."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, encoding="utf-8") as f:
                loaded_data = json.load(f)

            # --- Logica di Migrazione ---

            # Migrazione delle vecchie statistiche rxing
            if "rxing_stats" in loaded_data:
                if "rxing_stats_words" not in loaded_data:
                    loaded_data["rxing_stats_words"] = loaded_data["rxing_stats"]
                del loaded_data["rxing_stats"]
                print(_("Migrated old 'rxing_stats' to 'rxing_stats_words'."))

            # Migrazione dei vecchi dati storici rxing
            if "historical_rx_data" in loaded_data:
                old_historical_data = loaded_data["historical_rx_data"]

                # Migra le impostazioni condivise se non esistono ancora
                if "historical_rx_settings" not in loaded_data:
                    loaded_data["historical_rx_settings"] = {
                        "max_sessions_to_keep": old_historical_data.get("max_sessions_to_keep", HISTORICAL_RX_MAX_SESSIONS_DEFAULT),
                        "report_interval": old_historical_data.get("report_interval", HISTORICAL_RX_REPORT_INTERVAL),
                    }

                # Migra i dati effettivi (log delle sessioni) in _words
                if "historical_rx_data_words" not in loaded_data:
                    loaded_data["historical_rx_data_words"] = {
                        "chars_since_last_report": old_historical_data.get("chars_since_last_report", 0),
                        "sessions_log": old_historical_data.get("sessions_log", []),
                        "historical_reports": old_historical_data.get("historical_reports", []),
                    }
                del loaded_data["historical_rx_data"]
                print(_("Migrated old 'historical_rx_data' to 'historical_rx_data_words' and extracted settings."))

            # Fine Logica di Migrazione

            merged_data = {}
            for main_key, default_values in DEFAULT_DATA.items():
                loaded_section = loaded_data.get(main_key, {})
                # Gestione speciale per historical_rx_settings se c'è un'override nelle default_values
                if main_key == "historical_rx_settings" and "max_sessions_to_keep" in loaded_section and "report_interval" in loaded_section:
                    merged_data[main_key] = loaded_section  # Usa i valori caricati, non i default
                    continue
                if main_key == "historical_rx_settings":  # Se non ci sono override nei loaded_section per questi valori
                    merged_data[main_key] = default_values.copy()  # Usa i default
                    if "max_sessions_to_keep" in loaded_section:
                        merged_data[main_key]["max_sessions_to_keep"] = loaded_section["max_sessions_to_keep"]
                    if "report_interval" in loaded_section:
                        merged_data[main_key]["report_interval"] = loaded_section["report_interval"]
                    continue
                # Il resto della gestione è per le altre sezioni che non hanno logica di merge speciale
                if isinstance(default_values, dict):
                    merged_section = default_values.copy()
                else:  # Per valori non dizionari, come liste o semplici tipi
                    merged_section = default_values

                if isinstance(merged_section, dict) and isinstance(loaded_section, dict):
                    merged_section.update(loaded_section)  # Applica i valori caricati sui default
                merged_data[main_key] = merged_section

            # Assicurati che le nuove chiavi siano inizializzate se non presenti dopo la migrazione
            for key_suffix in ["words", "chars", "qrz"]:
                rx_stats_key = f"rxing_stats_{key_suffix}"
                if rx_stats_key not in merged_data:
                    merged_data[rx_stats_key] = DEFAULT_DATA[rx_stats_key].copy()
                hist_data_key = f"historical_rx_data_{key_suffix}"
                if hist_data_key not in merged_data:
                    merged_data[hist_data_key] = DEFAULT_DATA[hist_data_key].copy()

            # Ripulitura delle sessioni vuote lasciate dalle versioni fino alla
            # 5.1.12: uscendo dal contest prima del primo QSO si registrava una
            # sessione senza dati, con velocita' minima 100 e massima 0, che
            # falsava le medie dell'archivio. Ora non se ne creano piu'.
            sessioni_vuote = 0
            for key_suffix in ["words", "chars", "qrz"]:
                hist_data_key = f"historical_rx_data_{key_suffix}"
                log = merged_data[hist_data_key].get("sessions_log", [])
                log_pulito = [s for s in log if s.get("items_sent_session", 0) > 0]
                if len(log_pulito) != len(log):
                    sessioni_vuote += len(log) - len(log_pulito)
                    merged_data[hist_data_key]["sessions_log"] = log_pulito
            if sessioni_vuote:
                print(_("Archivio ripulito: tolte {quante} sessioni senza dati.").format(quante=sessioni_vuote))
            print(_("Impostazioni generali caricate"))
            return merged_data
        except (OSError, json.JSONDecodeError, TypeError):
            print(_("Errore durante il caricamento del file di impostazioni."))
            return {k: v.copy() if isinstance(v, dict) else v for k, v in DEFAULT_DATA.items()}
    else:
        print(_("Impostazioni generali di default"))
        return {k: v.copy() if isinstance(v, dict) else v for k, v in DEFAULT_DATA.items()}


def save_settings(data):
    """Salva le impostazioni correnti nel file JSON."""
    try:
        data_to_save = data.copy()
        if "rxing_stats" in data_to_save and isinstance(data_to_save["rxing_stats"].get("total_time"), dt.timedelta):
            data_to_save["rxing_stats"]["total_time_seconds"] = data_to_save["rxing_stats"]["total_time"].total_seconds()
            data_to_save["rxing_stats"].pop("total_time", None)
        elif "rxing_stats" in data_to_save and "total_time" in data_to_save["rxing_stats"]:
            data_to_save["rxing_stats"].pop("total_time", None)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, indent=4, ensure_ascii=False)
        print(_("Impostazioni generali salvate sul disco."))
    except OSError as e:
        print(_("Errore nel salvare {SETTINGS_FILE}: {e}").format(SETTINGS_FILE=SETTINGS_FILE, e=e))
    except TypeError as e:
        print(_("Errore di tipo durante la preparazione dei dati per JSON: {e} - Dati: {data_to_save}").format(e=e, data_to_save=data_to_save))


def ItemChooser(items):
    """Sceglie una voce da un elenco numerato, restituendone l'indice."""
    for i, item in enumerate(items, start=1):
        print(f"{i}. {item}")
    predefinito = min(6, len(items))
    while True:
        choice = dgt(prompt=_("Numero da 1 a {massimo}, Invio per {predefinito}> ").format(massimo=len(items), predefinito=predefinito), kind="i", imin=1, imax=len(items), default=predefinito)
        if 1 <= choice <= len(items):
            return choice - 1
        print(_("Scelta non valida: serve un numero da 1 a {massimo}.").format(massimo=len(items)))


def KeyboardCW():
    """Settings for CW and tx with keyboard"""
    global overall_speed, overall_pitch, overall_dashes, overall_spaces, overall_dots, overall_volume, overall_ms, overall_fs, overall_wave
    # Le righe si concatenano invece di continuare con la barra rovesciata:
    # cosi' non finiscono ventotto spazi in fondo a ognuna, che a schermo
    # erano rumore e nel catalogo delle traduzioni erano peggio.
    MNKeyboard_settings = _(
        "Benvenuto nella sezione dove potrai ascoltare il CW e configurare tutti i suoi parametri.\n"
        "Questi parametri saranno validi e attivi in tutto CWAPU e verranno salvati automaticamente quando esci dall'app.\n"
        "Ora, leggi attentamente quanto segue:\n"
        "\tPremi Invio senza digitare nulla per uscire e tornare al menu principale;\n"
        "\tdigita .w seguito da un valore numerico per impostare il WPM, da 5 a 120;\n"
        "\tdigita .h seguito da un valore per il pitch della nota CW, da 200 a 2700;\n"
        "\tdigita .l seguito da un valore per impostare la linea, il default è 30;\n"
        "\tdigita .s seguito da un valore per impostare lo spazio, il default è 50;\n"
        "\tdigita .p proprio come .s ma per i punti;\n"
        "\tdigita .v seguito da un valore tra 0 e 100 per impostare il volume;\n"
        "\tdigita .f1 .f2 .f3 o .f4 per cambiare la forma d'onda;\n"
        "\tdigita .m seguito da millisecondi per impostare il fade in e out per la nota CW;\n"
        "\tdigita .g seguito da un valore per impostare la quantità di esercizi per le statistiche globali;\n"
        "\tdigita .x seguito da un valore per impostare ogni quanti caratteri aggiornare le stats globali;\n"
        "\tdigita .t #-# dove i # sono i valori minimo-massimo del filtro per la scelta delle parole;\n"
        "\tdigita .y per impostare un gruppo personalizzato di caratteri su cui allenarti;\n"
        "\tdigita .sr per impostare il sample rate da inviare alla scheda audio;\n"
        "\tdigita ? per vedere questo messaggio di aiuto;\n"
        "\tdigita ?? per visualizzare i parametri impostati;\n"
        "\tdigita .rs per reimpostare il CW al peso standard di 1/3;\n"
        "\tdigita .sv seguito dal testo per salvare il CW in un file .wav;\n"
        "\tqualunque altra cosa scrivi viene trasmessa in CW.\n"
    )
    tosave = False
    rwpm = overall_speed
    print("\n" + MNKeyboard_settings)
    while True:
        if rwpm is not None and overall_speed != rwpm:
            current_prompt = _("RWPM: {rwpm:.2f}").format(rwpm=rwpm)
        else:
            current_prompt = _("WPM: {overall_speed:.2f}").format(overall_speed=overall_speed)
        print(current_prompt + "> ", end="", flush=True)
        msg_input = sys.stdin.readline()
        if not msg_input:
            break
        msg = msg_input.rstrip("\r\n") + " "
        msg_for_cw = msg
        if msg == " ":
            plo, rwpm_temp = suona("73")
            if rwpm_temp is not None:
                rwpm = rwpm_temp
            break
        if msg == "? ":
            print("\n" + MNKeyboard_settings)
            msg_for_cw = "bk the commands are bk"
        elif msg == "?? ":
            impostazioni_storiche = app_data.get("historical_rx_settings", {})
            current_max_sessions_g_val = impostazioni_storiche.get("max_sessions_to_keep", HISTORICAL_RX_MAX_SESSIONS_DEFAULT)
            current_report_interval_x_val = impostazioni_storiche.get("report_interval", HISTORICAL_RX_REPORT_INTERVAL)
            switcher_states_config = app_data.get("rx_menu_switcher_states", {})
            parole_min = switcher_states_config.get("parole_filter_min", 0)
            parole_max = switcher_states_config.get("parole_filter_max", 0)
            custom_set_str = switcher_states_config.get("custom_set_string", "")
            t_filter_display = f"{parole_min}-{parole_max}" if parole_min > 0 and parole_max > 0 else _("Filtro non impostato")
            y_custom_set_display = f'"{custom_set_str}"' if custom_set_str else _("Gruppo vuoto")
            base_settings_line1 = _("\n\tWPM: {overall_speed}, Hz: {overall_pitch}, Volume: {}").format(int(overall_volume * 100), overall_speed=overall_speed, overall_pitch=overall_pitch)
            base_settings_line2 = _("\tL/S/P: {overall_dashes}/{overall_spaces}/{overall_dots}, Wave: {}, MS: {overall_ms}, FS: {}.").format(
                WAVE_TYPES[overall_wave - 1], SAMPLE_RATES[overall_fs], overall_dashes=overall_dashes, overall_spaces=overall_spaces, overall_dots=overall_dots, overall_ms=overall_ms
            )
            history_settings_line = _("\tMax Exercises History (g): {current_max_sessions_g_val}, Report size (x): {current_report_interval_x_val}.").format(
                current_max_sessions_g_val=current_max_sessions_g_val, current_report_interval_x_val=current_report_interval_x_val
            )
            new_filter_settings_line = _("\tWord Filter (T): {t_filter_display}, Custom Set (Y): {y_custom_set_display}").format(
                t_filter_display=t_filter_display, y_custom_set_display=y_custom_set_display
            )
            print(base_settings_line1)
            print(base_settings_line2)
            print(history_settings_line)
            print(new_filter_settings_line)
            msg_for_cw = "bk r parameters are bk"
        elif msg == ".sr ":
            new_fs_index = ItemChooser(SAMPLE_RATES)
            if new_fs_index != overall_fs:
                overall_fs = new_fs_index
            plo, rwpm_temp = suona(_("bk fs is {} bk").format(SAMPLE_RATES[overall_fs]))
            if rwpm_temp is not None:
                rwpm = rwpm_temp
            msg_for_cw = ""
        elif msg == ".rs ":
            if not (overall_dashes == 30 and overall_spaces == 50 and (overall_dots == 50)):
                overall_dashes, overall_spaces, overall_dots = (30, 50, 50)
            plo, rwpm_temp = suona("bk reset ok bk")
            if rwpm_temp is not None:
                rwpm = rwpm_temp
            msg_for_cw = ""
        elif msg.startswith(".sv "):
            msg_for_cw = msg[4:]
            tosave = True
        elif msg.startswith("."):
            command_candidate_str = msg[1:].strip()
            cmd_letter_parsed = ""
            value_int_parsed = None
            is_value_numeric_type = False
            is_value_special_format = False
            command_processed_internally = False
            feedback_cw = ""
            match_val_num = re.match("([a-zA-Z])(\\d+)", command_candidate_str)
            if match_val_num and command_candidate_str == match_val_num.group(0):
                cmd_letter_parsed = match_val_num.group(1).lower()
                value_int_parsed = int(match_val_num.group(2))
                is_value_numeric_type = True
            else:
                parts = command_candidate_str.split(maxsplit=1)
                if parts:
                    cmd_letter_parsed = parts[0].lower()
                    if len(parts) > 1:
                        value_str_parsed = parts[1]
                        is_value_special_format = True
                else:
                    feedback_cw = "?"
                    command_processed_internally = True
            if cmd_letter_parsed == "y":
                if command_candidate_str == "y":
                    print(_("Avvio editor gruppo Custom..."))
                    custom_string_result = CustomSet(overall_speed)
                    current_saved_set = app_data["rx_menu_switcher_states"].get("custom_set_string", "")
                    if current_saved_set != custom_string_result:
                        app_data["rx_menu_switcher_states"]["custom_set_string"] = custom_string_result
                    if custom_string_result:
                        feedback_cw = _("Set custom: {num_chars} car.").format(num_chars=len(custom_string_result))
                    else:
                        feedback_cw = "bk r custom set empty bk"
                    command_processed_internally = True
                    print("\n" + MNKeyboard_settings)
                else:
                    feedback_cw = "?"
                    command_processed_internally = True
            elif cmd_letter_parsed == "t":
                if is_value_special_format and "-" in value_str_parsed:
                    min_max_parts = value_str_parsed.split("-")
                    if len(min_max_parts) == 2 and min_max_parts[0].isdigit() and min_max_parts[1].isdigit():
                        p_min = int(min_max_parts[0])
                        p_max = int(min_max_parts[1])
                        p_min_validated = max(1, min(10, p_min))
                        p_max_validated = max(3, min(35, p_max))
                        p_min_validated = min(p_min_validated, p_max_validated)
                        if app_data["rx_menu_switcher_states"].get("parole_filter_min") != p_min_validated or app_data["rx_menu_switcher_states"].get("parole_filter_max") != p_max_validated:
                            app_data["rx_menu_switcher_states"]["parole_filter_min"] = p_min_validated
                            app_data["rx_menu_switcher_states"]["parole_filter_max"] = p_max_validated
                        feedback_cw = _("bk r word filter is {p_min_validated} {p_max_validated} bk").format(p_min_validated=p_min_validated, p_max_validated=p_max_validated)
                        command_processed_internally = True
                    else:
                        feedback_cw = "?"
                        command_processed_internally = True
                else:
                    feedback_cw = "?"
                    command_processed_internally = True
            elif is_value_numeric_type and value_int_parsed is not None:
                if cmd_letter_parsed == "g":
                    min_val_g, max_val_g = (20, 5000)
                    impostazioni_storiche = app_data.setdefault("historical_rx_settings", DEFAULT_DATA["historical_rx_settings"].copy())
                    actual_val_g = impostazioni_storiche.get("max_sessions_to_keep", HISTORICAL_RX_MAX_SESSIONS_DEFAULT)
                    new_val_g = max(min_val_g, min(max_val_g, value_int_parsed))
                    if actual_val_g != new_val_g:
                        impostazioni_storiche["max_sessions_to_keep"] = new_val_g
                        # Il registro e' diviso in tre categorie: la potatura va
                        # ripetuta su tutte e tre, non su una chiave sola.
                        for suffisso_categoria in ("words", "chars", "qrz"):
                            dati_categoria = app_data.get(f"historical_rx_data_{suffisso_categoria}", {})
                            log_categoria = dati_categoria.get("sessions_log", [])
                            if len(log_categoria) > new_val_g:
                                dati_categoria["sessions_log"] = log_categoria[-new_val_g:]
                    feedback_cw = _("bk r max exercises is {new_val_g} bk").format(new_val_g=new_val_g)
                    command_processed_internally = True
                elif cmd_letter_parsed == "x":
                    min_val_x, max_val_x = (500, 15000)
                    impostazioni_storiche = app_data.setdefault("historical_rx_settings", DEFAULT_DATA["historical_rx_settings"].copy())
                    actual_val_x = impostazioni_storiche.get("report_interval", HISTORICAL_RX_REPORT_INTERVAL)
                    new_val_x = max(min_val_x, min(max_val_x, value_int_parsed))
                    if actual_val_x != new_val_x:
                        impostazioni_storiche["report_interval"] = new_val_x
                    feedback_cw = _("bk r report size is {new_val_x} bk").format(new_val_x=new_val_x)
                    command_processed_internally = True
                elif cmd_letter_parsed == "w":
                    if overall_speed != value_int_parsed:
                        new_speed = limita_wpm(value_int_parsed)
                        if overall_speed != new_speed:
                            overall_speed = new_speed
                    feedback_cw = _("bk r w is {overall_speed} bk").format(overall_speed=overall_speed)
                    command_processed_internally = True
                elif cmd_letter_parsed == "m":
                    if overall_ms != value_int_parsed:
                        new_ms = max(1, min(30, value_int_parsed))
                        if overall_ms != new_ms:
                            overall_ms = new_ms
                    feedback_cw = _("bk r ms is {overall_ms} bk").format(overall_ms=overall_ms)
                    command_processed_internally = True
                elif cmd_letter_parsed == "f":
                    new_wave_idx_user = max(1, min(len(WAVE_TYPES), value_int_parsed))
                    if overall_wave != new_wave_idx_user:
                        overall_wave = new_wave_idx_user
                    feedback_cw = _("bk r wave is {} bk").format(WAVE_TYPES[overall_wave - 1])
                    command_processed_internally = True
                elif cmd_letter_parsed == "h":
                    if overall_pitch != value_int_parsed:
                        new_pitch = max(200, min(2700, value_int_parsed))
                        if overall_pitch != new_pitch:
                            overall_pitch = new_pitch
                    feedback_cw = _("bk r h is {overall_pitch} bk").format(overall_pitch=overall_pitch)
                    command_processed_internally = True
                elif cmd_letter_parsed == "l":
                    if overall_dashes != value_int_parsed:
                        new_dashes = max(1, min(99, value_int_parsed))
                        if overall_dashes != new_dashes:
                            overall_dashes = new_dashes
                    feedback_cw = _("bk r l is {overall_dashes} bk").format(overall_dashes=overall_dashes)
                    command_processed_internally = True
                elif cmd_letter_parsed == "s":
                    if overall_spaces != value_int_parsed:
                        new_spaces = max(3, min(99, value_int_parsed))
                        if overall_spaces != new_spaces:
                            overall_spaces = new_spaces
                    feedback_cw = _("bk r s is {overall_spaces} bk").format(overall_spaces=overall_spaces)
                    command_processed_internally = True
                elif cmd_letter_parsed == "p":
                    if overall_dots != value_int_parsed:
                        new_dots = max(1, min(99, value_int_parsed))
                        if overall_dots != new_dots:
                            overall_dots = new_dots
                    feedback_cw = _("bk r p is {overall_dots} bk").format(overall_dots=overall_dots)
                    command_processed_internally = True
                elif cmd_letter_parsed == "v":
                    new_volume_percent = max(0, min(100, value_int_parsed))
                    if abs(overall_volume * 100 - new_volume_percent) > 0.01:
                        overall_volume = new_volume_percent / 100.0
                    feedback_cw = _("bk r v is {new_volume_percent} bk").format(new_volume_percent=new_volume_percent)
                    command_processed_internally = True
            if command_processed_internally:
                if feedback_cw:
                    plo, rwpm_temp = suona(feedback_cw)
                    if rwpm_temp is not None:
                        rwpm = rwpm_temp
                msg_for_cw = ""
        if msg_for_cw.strip():
            plo, rwpm_temp = suona(msg_for_cw, to_file=tosave)
            if rwpm_temp is not None:
                rwpm = rwpm_temp
            else:
                rwpm = overall_speed
            if tosave:
                # Prima l'indicazione SV nel prompt si accendeva e si spegneva
                # nello stesso giro di ciclo, quindi non compariva mai, e chi
                # salvava non sapeva dove fosse finito il file.
                percorso_wav = getattr(plo, "file_salvato", None) if plo is not None else None
                if percorso_wav:
                    print(_("CW salvato in: {percorso}").format(percorso=percorso_wav))
                else:
                    print(_("Il file WAV non e' stato scritto."))
                tosave = False
    print(_("Ciao per ora. Torniamo al menu principale.") + "\n")


def StringCleaning(stringa):
    stringa = stringa.strip()
    stringa = stringa.lower()
    cleaned = re.sub("[^a-z0-9\\sàèéìòù@.,;:!?\\'\\\"()=-]", "", stringa)
    return re.sub("\\s+", " ", cleaned)


def CreateDictionary():
    print(
        _(
            "Attenzione! Si prega di leggere attentamente.\nPer gli esercizi di ricezione, (r) dal menu principale, CWAPU utilizza il file words.txt, che deve stare nella stessa cartella di cwapu.py o di cwapu.exe. Se questo file non esiste, creane uno con un editor di testo e scrivi alcune parole al suo interno, una parola per linea, quindi salva.\nLa procedura WordsCreator ti permette di scansionare tutti i file txt contenuti nelle cartelle che indichi e aggiungere tutte le parole da questi file a words.txt. Le parole saranno aggiunte unicamente, cioè saranno tutte diverse tra loro.\nIl file prodotto da questo processo sarà denominato words_updated.txt. Controllalo con un editor di testo e, se sei soddisfatto, rinominalo in words.txt, sostituendo l'esistente words.txt.\nPuoi ripetere questa operazione tutte le volte che vuoi: words_updated.txt conterrà le parole da words.txt più tutte quelle raccolte dai nuovi file .txt elaborati."
        )
    )
    import Words_Creator

    # I percorsi glieli passa cwapu, che sa dove sta il programma: da solo
    # Words_Creator userebbe la cartella da cui si e' lanciato il comando.
    Words_Creator.Start(words_path=user_file_path("words.txt"), output_dir=USER_DATA_PATH)


def CustomSet(overall_speed):
    cs = set()
    # Scelta a lettere, quindi passa da menu() di GBUtils: le due alternative
    # sono dette per esteso invece di essere due iniziali fra parentesi quadre.
    scelta_precompilazione = menu(
        d={_("s"): _("Si, parti dai caratteri su cui sbaglio di piu'"), _("n"): _("No, comincio da un gruppo vuoto")},
        p=_("Vuoi iniziare con un gruppo di caratteri precompilato? "),
        ntf=_("Rispondi s oppure n."),
    )
    if scelta_precompilazione == _("s"):
        prefilled_chars_list = []
        # Il registro e' diviso in parole, caratteri e QRZ: un errore su una
        # lettera resta un errore su quella lettera, quindi si guardano tutte
        # e tre. Prima si leggeva una chiave che non esiste piu' dalla
        # migrazione, e la precompilazione non ha mai avuto dati veri.
        sessions_log = []
        for suffisso_categoria in ("words", "chars", "qrz"):
            sessions_log.extend(app_data.get(f"historical_rx_data_{suffisso_categoria}", {}).get("sessions_log", []))
        if sessions_log:
            # 1. Aggreghiamo sia gli errori che i caratteri inviati
            aggregated_errors = {}
            aggregated_sent = {}
            for session_data in sessions_log:
                # Aggrega errori
                for char, count in session_data.get("errors_detail_session", {}).items():
                    char_lower = char.lower()
                    if char_lower in VALID_MORSE_CHARS_FOR_CUSTOM_SET:
                        aggregated_errors[char_lower] = aggregated_errors.get(char_lower, 0) + count
                # Aggrega invii
                for char, count in session_data.get("sent_chars_detail_session", {}).items():
                    char_lower = char.lower()
                    if char_lower in VALID_MORSE_CHARS_FOR_CUSTOM_SET:
                        aggregated_sent[char_lower] = aggregated_sent.get(char_lower, 0) + count
            # 2. Calcoliamo il punteggio di criticità (Wilson Score) per ogni carattere
            char_scores = []
            all_chars = set(aggregated_errors.keys()) | set(aggregated_sent.keys())
            for char in all_chars:
                errori = aggregated_errors.get(char, 0)
                inviati = aggregated_sent.get(char, 0)
                if inviati > 0:  # Calcoliamo solo per caratteri inviati almeno una volta
                    score = wilson_score_lower_bound(errori, inviati)
                    char_scores.append({"char": char, "score": score})
            # 3. Ordiniamo per punteggio decrescente e prendiamo i primi 10
            if char_scores:
                # Ordina per score (più alto è peggio) e poi alfabeticamente
                sorted_critical_chars = sorted(char_scores, key=lambda x: (-x["score"], x["char"]))
                prefilled_chars_list = [item["char"] for item in sorted_critical_chars[:10]]
        if prefilled_chars_list:
            print(_("Gruppo precompilato con errori frequenti: {chars}").format(chars=", ".join(c.upper() for c in prefilled_chars_list)))
            for char_err in prefilled_chars_list:
                cs.add(char_err)
        else:
            random_chars_pool = list(VALID_MORSE_CHARS_FOR_CUSTOM_SET)
            if random_chars_pool:
                num_to_add = min(10, len(random_chars_pool))
                cs.update(random.sample(random_chars_pool, num_to_add))
                if cs:
                    print(_("Gruppo precompilato con caratteri casuali: {chars}").format(chars=", ".join(sorted(c.upper() for c in cs))))
                else:
                    print(_("Impossibile precompilare: nessun carattere valido disponibile."))
            else:
                print(_("Impossibile precompilare: nessun carattere valido disponibile."))
    print(_("Inserisci/modifica caratteri (toggle). Invio per terminare."))
    while True:
        current_set_display = "".join(sorted(cs))
        user_input_char = key(prompt="\n" + current_set_display)
        if user_input_char == "\r":
            if len(cs) >= 2:
                break
            suona("?")
            continue
        if len(user_input_char) == 1 and user_input_char.isprintable():
            char_typed_lower = user_input_char.lower()
            if char_typed_lower not in VALID_MORSE_CHARS_FOR_CUSTOM_SET:
                suona("?")
                continue
            if char_typed_lower in cs:
                cs.remove(char_typed_lower)
            else:
                cs.add(char_typed_lower)
                suona(char_typed_lower)
        elif user_input_char != "\r":
            suona("?")
    return "".join(sorted(cs))


def GeneratingGroup(kind, length, wpm, customized_set_param=None):
    if kind == "1":
        if not LETTERE_MORSE_POOL:
            return "ERR_LP"
        pool = list(LETTERE_MORSE_POOL)
        return "".join(random.choices(pool, k=length))
    if kind == "2":
        if not NUMERI_MORSE_POOL:
            return "ERR_NP"
        pool = list(NUMERI_MORSE_POOL)
        return "".join(random.choices(pool, k=length))
    if kind == "3":
        if not LETTERE_MORSE_POOL and not NUMERI_MORSE_POOL:
            return "ERR_LNP"  # Errore: pool lettere e numeri vuoto
        pool = list(LETTERE_MORSE_POOL | NUMERI_MORSE_POOL)
        return "".join(random.choices(pool, k=length))
    if kind == "4":
        if not customized_set_param or len(customized_set_param) < 1:
            return "ERR_CS"
        return "".join(random.choices(list(customized_set_param), k=length))
    if kind == "S":
        if not SIMBOLI_MORSE_POOL:
            return "ERR_SP"
        pool = list(SIMBOLI_MORSE_POOL)
        return "".join(random.choices(pool, k=length))
    return "ERR_KD"


def Mkdqrz(c):
    # Se abbiamo un pool di call reali, 75% di probabilità di usarne uno
    if REAL_CALLS_POOL and random.random() < 0.75:
        return random.choice(REAL_CALLS_POOL)

    q = ""
    c = c[0]
    for j in str(c):
        if j.isdigit():
            q += random.choice(string.digits)
        else:
            q += random.choice(string.ascii_uppercase)
    return q


def Txing():
    print(
        _(
            "Esercizio di trasmissione.\nEcco una serie casuale di pseudo-call e numeri progressivi,\n\tprova a trasmetterli con il tuo tasto CW preferito senza errori.\nQualsiasi tasto per passare al successivo, ESC per terminare l'esercizio."
        )
    )
    cont = 1
    while True:
        c = random.choices(list(MDL.keys()), weights=MDL.values(), k=1)
        qrz = Mkdqrz(c)
        pgr = random.randint(1, 9999)
        prompt = _("- {cont} {qrz} 5nn {pgr}").format(cont=cont, qrz=qrz, pgr=pgr)
        wait = key(prompt)
        print()
        # Confronto sul carattere e non su ord: con un ritorno vuoto ord
        # solleverebbe TypeError invece di uscire dall'esercizio.
        if wait in ("\x1b", "esc"):
            break
        cont += 1
    print(_("Ciao per ora. Torniamo al menu principale."))


def Count():
    print(_("Conteggio, SÌ o NO?\nBarra spaziatrice significa: gruppo ricevuto;\nQualsiasi altro tasto significa: gruppo perso;\nPremi ESC per tornare al menu principale."))
    from GBUtils import Acusticator as Ac

    esnum = app_data["counting_stats"].get("exercise_number", 1)
    cont = 0
    corr = 0
    scelta = ""
    Ac([350, 0.2, 0, 0.5], sync=True)
    print(_("Esercizio numero {esnum}:").format(esnum=esnum))
    while True:
        if cont % 100 == 0:
            Ac([1600, 0.2, 0, 0.5], sync=True)
        elif cont % 50 == 0:
            Ac([1150, 0.08, 0, 0.5], sync=True)
        elif cont % 25 == 0:
            Ac([900, 0.06, 0, 0.5], sync=True)
        elif cont % 10 == 0:
            Ac([600, 0.04, 0, 0.5], sync=True)
        if cont > 0:
            percentuale_ok = corr * 100 / cont
            prompt = _("T{cont}, {percentuale}%, C{corr}/N{errati}> ").format(cont=cont + 1, percentuale=f"{percentuale_ok:.1f}", corr=corr, errati=cont - corr)
        else:
            prompt = _("T1, 0%, C0/N0> ")
        scelta = key("\n" + prompt)
        if scelta == " ":
            corr += 1
            Ac([1380, 0.015, 0, 0.5], sync=True)
        elif scelta in ("\x1b", "esc"):
            break
        else:
            Ac([310, 0.025, 0, 0.5], sync=True)
        cont += 1
    if cont > 0:
        pde = 100 - corr * 100 / cont
    else:
        pde = 100
    print(_("\nTotale: {cont}, corrette: {corr}, errori(%): {pde:.2f}%.").format(cont=cont, corr=corr, pde=pde))
    if pde <= 6:
        print(_("Superato!"))
    else:
        print(_("Fallito: {difference:.2f}% oltre la soglia.").format(difference=pde - 6))
    if cont >= 100:
        nota = dgt(prompt=_("\nNota su questo esercizio: "), kind="s", smin=0, smax=512)
        adesso = dt.datetime.now()
        date_str = adesso.strftime("%Y/%m/%d")
        time_str = adesso.strftime("%H:%M")
        try:
            with open(DIARY_FILE, "a", encoding="utf-8") as f:
                f.write(_("Esercizio di conteggio #{esnum} eseguito il {date} alle {time} minuti:\n").format(esnum=esnum, date=date_str, time=time_str))
                f.write(_("Totale: {cont}, corrette: {corr}, errori(%): {pde:.2f}%.\n").format(cont=cont, corr=corr, pde=pde))
                if pde <= 6:
                    f.write(_("Superato!") + "\n")
                else:
                    f.write(_("Fallito: {difference:.2f}% oltre la soglia.").format(difference=pde - 6) + "\n")
                if nota != "":
                    f.write(_("Nota: {nota}").format(nota=nota) + "\n" + FINE_RECORD_DIARIO)
                else:
                    f.write(_("Nota: nessuna") + "\n" + FINE_RECORD_DIARIO)
            print(_("Rapporto salvato su {nome_diario}").format(nome_diario=DIARY_NAME))
        except OSError as e:
            print(_("Diario non scritto: {errore}").format(errore=e))
    else:
        print(_("Gruppi ricevuti {cont} su 100: esercizio non salvato su disco.").format(cont=cont))
    esnum = app_data["counting_stats"].get("exercise_number", 1) + 1
    app_data["counting_stats"]["exercise_number"] = esnum
    print(_("Ciao per ora. Torniamo al menu principale."))


def MistakesCollectorInStrings(right, received):
    differences = []
    s = difflib.SequenceMatcher(None, right, received)
    for tag, i1, i2, j1, j2 in s.get_opcodes():
        if tag == "replace" or tag == "delete":
            differences.extend(right[i1:i2])
        elif tag == "insert":
            differences.extend(received[j1:j2])
    return "".join(differences)


def collect_char_errors(target, user, error_dict):
    """
    Confronta target e user string, aggiorna il dizionario degli errori per carattere
    e restituisce il numero totale di errori trovati.
    """
    mistakes = MistakesCollectorInStrings(target, user)
    count = 0
    for m in mistakes:
        error_dict[m] = error_dict.get(m, 0) + 1
        count += 1
    return count


def AlwaysRight(sent_items, error_counts_dict):
    letters_sent = set("".join(sent_items))
    letters_misspelled = set(error_counts_dict.keys())
    return letters_sent - letters_misspelled


def format_duration(td):
    """
    Format a timedelta object into a localized string.
    Example: 3 giorni, 15 ore, 26 minuti e 3 secondi
    """
    total_seconds = int(td.total_seconds())
    days = total_seconds // 86400
    remainder = total_seconds % 86400
    hours = remainder // 3600
    remainder %= 3600
    minutes = remainder // 60
    seconds = remainder % 60

    parts = []
    if days > 0:
        part = _("{count} giorni") if days > 1 else _("{count} giorno")
        parts.append(part.format(count=days))
    if hours > 0:
        part = _("{count} ore") if hours > 1 else _("{count} ora")
        parts.append(part.format(count=hours))
    if minutes > 0:
        part = _("{count} minuti") if minutes > 1 else _("{count} minuto")
        parts.append(part.format(count=minutes))
    if seconds > 0 or not parts:  # Show seconds if it's the only thing or > 0
        part = _("{count} secondi") if seconds != 1 else _("{count} secondo")
        parts.append(part.format(count=seconds))

    if len(parts) == 1:
        return parts[0]

    return ", ".join(parts[:-1]) + " " + _("e") + " " + parts[-1]


def RxingContest(menu_config_scelta):
    global overall_speed

    print(_("\nModalità contest."))
    print(_("Simulazione scambio rapido: Call + 5NN + Serial"))

    # Setup durata
    scelta_durata = menu(d={"1": _("Numero di QRZ"), "2": _("Tempo (minuti)")}, p=_("Scegli la durata: "))
    if not scelta_durata:
        return
    duration_type = int(scelta_durata)
    limit = 0
    if duration_type == 1:
        limit = dgt(prompt=_("Quanti QRZ? "), kind="i", imin=5, imax=500, default=50)
    else:
        limit = dgt(prompt=_("Quanti minuti? "), kind="i", imin=1, imax=60, default=10)

    print(_("Comandi rapidi: F9/F10 (WPM), F5 (Call), F6 (Serial), F7 (Rpt), F8 (NIL), Alt+W (Wipe), ESC (Exit), Enter (Check)"))
    key(_("Premi un tasto per iniziare..."))
    print(f"\r{' ' * 79}\r", end="", flush=True)  # Clean initial line
    suona("CQ CQ TEST K", sync=True)

    start_time = dt.datetime.now()
    session_calls = 0
    my_progressive = 0  # Counter for my sent serials (only increases on success)
    correct_calls = 0
    total_calls_correct = 0
    total_serials_correct = 0

    # Stats trackers
    item_details = []
    sent_chars_detail_this_session = {}
    char_error_counts = {}
    total_mistakes_calculated = 0
    minwpm = None
    maxwpm = 0
    sum_wpm = 0.0
    callssend = []
    callsget = []
    active_exerctime = dt.timedelta(0)  # Approssimato

    import queue
    import threading
    import time

    input_queue = queue.Queue()
    stop_event = threading.Event()
    current_modifiers = set()

    def on_press(key):
        if stop_event.is_set():
            return False
        try:
            if key in {keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r}:
                current_modifiers.add("alt")
            input_queue.put(("press", key))
        except (AttributeError, ValueError):
            # Tasto che pynput non sa classificare: si scarta e si prosegue,
            # perche' un errore qui fermerebbe l'ascolto della tastiera.
            pass

    def on_release(key):
        try:
            if key in {keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r}:
                current_modifiers.discard("alt")
            input_queue.put(("release", key))
        except (AttributeError, ValueError):
            pass

    listener = keyboard.Listener(on_press=on_press, on_release=on_release, suppress=False)
    listener.start()

    current_audio = None
    last_enter_time = 0
    last_backspace_time = 0
    ultima_rwpm_dx = 0.0

    # Audio Helpers
    def play_async(msg, speed=None, pitch=None, l=None, s=None, p=None):
        # La velocita' effettiva la misura il motore CW sulla durata davvero
        # prodotta: con i pesi sporchi della stazione DX si discosta parecchio
        # da quella nominale, ed e' quella che deve finire nelle statistiche.
        nonlocal current_audio, ultima_rwpm_dx
        if current_audio:
            current_audio.stop()
        if msg:
            current_audio, rwpm_prodotta = suona(msg, wpm=speed, pitch=pitch, l=l, s=s, p=p, sync=False)
            ultima_rwpm_dx = rwpm_prodotta if current_audio is not None else 0.0

    def play_sync_me(msg):
        nonlocal current_audio
        if current_audio:
            current_audio.stop()
        if msg:
            suona(msg, sync=True)

    try:
        while True:
            # Check duration
            elapsed = dt.datetime.now() - start_time
            elapsed_minutes = elapsed.total_seconds() / 60.0

            if duration_type == 1 and session_calls >= limit:
                break
            if duration_type == 2 and elapsed_minutes >= limit:
                break

            # Generate Exchange
            c = random.choices(list(MDL.keys()), weights=MDL.values(), k=1)
            qrz = Mkdqrz(c)

            # Serial
            skill = random.randint(1, 4)
            serial = round(1 + random.random() * max(0.1, elapsed_minutes) * skill)

            # DX Params
            dx_patience = random.randint(0, 5)
            # round e non int: il troncamento e' asimmetrico e regalava mezzo
            # wpm di sconto sistematico su tutto il contest.
            dx_speed = limita_wpm(round(overall_speed * (1 + random.uniform(-0.1, 0.1))))

            # Pitch logic with avoidance (+/- 5Hz) - UPDATED RANGE to +/- 300 with manual clamp 200-2000
            dx_pitch = overall_pitch
            for _tentativo in range(20):
                dx_pitch = max(200, min(2000, overall_pitch + random.randint(-300, 300)))
                if abs(dx_pitch - overall_pitch) > 5:
                    break

            # LSP Logic
            dx_l, dx_s, dx_p = 30, 50, 50
            if random.random() < RX_LSP_VARIATION_PROBABILITY:
                dx_l = random.randint(*RX_LSP_RANGE_L)
                dx_s = random.randint(*RX_LSP_RANGE_S)
                dx_p = random.randint(*RX_LSP_RANGE_P)

            # Messages
            msg_call = qrz
            msg_exchange = f"R 5NN {serial}"
            msg_serial_only = str(serial)
            msg_full_for_stats = f"{qrz} 5NN {serial}"

            callssend.append(msg_full_for_stats)

            # Update sent chars stats
            for ch in msg_full_for_stats:
                if ch.isalnum():
                    sent_chars_detail_this_session[ch.lower()] = sent_chars_detail_this_session.get(ch.lower(), 0) + 1

            # --- STARTQSO ---
            current_stage = "CALL"
            remaining_patience = dx_patience
            qso_done = False
            final_call_ok = False
            final_serial_ok = False
            current_buffer = []

            def redraw_line():
                # Legge di proposito le variabili del QSO in corso: viene
                # chiamata soltanto dentro il giro che le ha appena definite.
                if current_stage == "CALL":  # noqa: B023
                    prompt_label = "CALL:"
                else:
                    prompt_label = f"{msg_call.upper()} 5NN NR:"  # noqa: B023
                line_content = f"RX #{session_calls + 1} {prompt_label} {''.join(current_buffer)}"  # noqa: B023
                print(f"\r{' ' * 79}\r{line_content}", end="", flush=True)

            # 1. DX Calls (Async)
            play_async(msg_call, speed=dx_speed, pitch=dx_pitch, l=dx_l, s=dx_s, p=dx_p)
            # La velocita' del QSO e' quella davvero prodotta dalla prima
            # chiamata, non quella nominale chiesta al motore.
            rwpm_qso = ultima_rwpm_dx if ultima_rwpm_dx > 0 else dx_speed
            minwpm = rwpm_qso if minwpm is None else min(minwpm, rwpm_qso)
            maxwpm = max(maxwpm, rwpm_qso)
            sum_wpm += rwpm_qso

            redraw_line()
            item_start_time = dt.datetime.now()

            while not qso_done:
                try:
                    event_type, event_key = input_queue.get(timeout=0.1)
                    if event_type != "press":
                        continue

                    if event_key == keyboard.Key.esc:
                        if current_audio:
                            current_audio.stop()
                        stop_event.set()
                        return

                    if event_key == keyboard.Key.enter:
                        now = time.time()
                        if now - last_enter_time < 0.5:
                            continue
                        last_enter_time = now

                        if current_audio:
                            current_audio.stop()
                        typed = "".join(current_buffer).upper().strip()
                        print()
                        my_serial_to_send = my_progressive + 1

                        if current_stage == "CALL":
                            target = msg_call.upper()
                            if typed == target:
                                # CALL OK
                                my_msg = f"{typed} 5NN {my_serial_to_send}"
                                play_sync_me(my_msg)
                                final_call_ok = True
                                current_stage = "SERIAL"
                                current_buffer = []
                                time.sleep(0.2)
                                play_async(msg_exchange, speed=dx_speed, pitch=dx_pitch, l=dx_l, s=dx_s, p=dx_p)
                                redraw_line()
                            elif typed == "":
                                # Empty -> Me: TEST
                                play_sync_me("TEST")
                                if remaining_patience > 0:
                                    remaining_patience -= 1
                                    time.sleep(0.2)
                                    play_async(msg_call, speed=dx_speed, pitch=dx_pitch, l=dx_l, s=dx_s, p=dx_p)
                                    redraw_line()
                                else:
                                    print(f" {msg_full_for_stats.upper()} (NIL)")
                                    qso_done = True
                            else:
                                # Wrong or Partial
                                my_msg = f"{typed} 5NN {my_serial_to_send}"
                                play_sync_me(my_msg)
                                total_mistakes_calculated += collect_char_errors(target.lower(), typed.lower(), char_error_counts)

                                # Partial Match Logic (New v5.1.0)
                                # Requires >= 2 chars AND being a valid substring of target
                                if len(typed) >= 2 and typed in target:
                                    if remaining_patience > 0:
                                        remaining_patience -= 1
                                        reaction = random.randint(1, 3)
                                        time.sleep(0.2)

                                        if reaction == 1:
                                            # Mode A: "R {call}" (Standard retry)
                                            play_async(f"R {msg_call}", speed=dx_speed, pitch=dx_pitch, l=dx_l, s=dx_s, p=dx_p)
                                        elif reaction == 2:
                                            # Mode B: "R {call} {call}" (Double repeat)
                                            play_async(f"R {msg_call} {msg_call}", speed=dx_speed, pitch=dx_pitch, l=dx_l, s=dx_s, p=dx_p)
                                        else:
                                            # Mode C: "R {call}" (Slow retry)
                                            dx_speed = limita_wpm(round(dx_speed * random.uniform(0.7, 0.9)))
                                            play_async(f"R {msg_call}", speed=dx_speed, pitch=dx_pitch, l=dx_l, s=dx_s, p=dx_p)

                                        current_buffer = []
                                        redraw_line()
                                    else:
                                        print(f" {msg_full_for_stats.upper()} (NIL)")
                                        qso_done = True
                                else:
                                    # Totally Wrong
                                    if remaining_patience > 0:
                                        remaining_patience -= 1
                                        time.sleep(0.2)
                                        play_async(msg_call, speed=dx_speed, pitch=dx_pitch, l=dx_l, s=dx_s, p=dx_p)
                                        current_buffer = []
                                        redraw_line()
                                    else:
                                        print(f" {msg_full_for_stats.upper()} (NIL)")
                                        qso_done = True

                        else:  # current_stage == "SERIAL"
                            target = msg_serial_only.upper()
                            if typed == target:
                                # SERIAL OK
                                final_serial_ok = True
                                qso_done = True
                                correct_calls += 1
                                my_progressive += 1
                                callsget.append(msg_full_for_stats)
                                item_details.append({"rwpm": rwpm_qso, "correct": True})
                                final_msg = random.choice(["TU", "73", "GL", "R", ""])
                                if final_msg:
                                    time.sleep(0.2)
                                    play_async(final_msg, speed=dx_speed, pitch=dx_pitch, l=dx_l, s=dx_s, p=dx_p)
                            elif typed == "":
                                play_sync_me("TEST")
                                if remaining_patience > 0:
                                    remaining_patience -= 1
                                    time.sleep(0.2)
                                    play_async(msg_serial_only, speed=dx_speed, pitch=dx_pitch, l=dx_l, s=dx_s, p=dx_p)
                                    redraw_line()
                                else:
                                    print(f" {msg_full_for_stats.upper()} (NIL)")
                                    qso_done = True
                            else:
                                # Wrong
                                total_mistakes_calculated += collect_char_errors(target.lower(), typed.lower(), char_error_counts)
                                if remaining_patience > 0:
                                    remaining_patience -= 1
                                    time.sleep(0.2)
                                    play_async(msg_serial_only, speed=dx_speed, pitch=dx_pitch, l=dx_l, s=dx_s, p=dx_p)
                                    current_buffer = []
                                    redraw_line()
                                else:
                                    print(f" {msg_full_for_stats.upper()} (NIL)")
                                    qso_done = True

                        while not input_queue.empty():
                            try:
                                input_queue.get_nowait()
                            except queue.Empty:
                                break

                    elif event_key == keyboard.Key.backspace:
                        now = time.time()
                        if now - last_backspace_time < 0.15:
                            continue
                        last_backspace_time = now
                        if current_buffer:
                            current_buffer.pop()
                            redraw_line()

                    elif event_key == keyboard.Key.f10:
                        # Senza tetto si superava il massimo che il motore CW
                        # accetta, e da li' in poi non si sentiva piu' niente.
                        overall_speed = min(WPM_MAX, overall_speed + 2)
                        print(f"\n[WPM: {overall_speed}]")
                        redraw_line()

                    elif event_key == keyboard.Key.f9:
                        overall_speed = max(WPM_MIN, overall_speed - 2)
                        print(f"\n[WPM: {overall_speed}]")
                        redraw_line()

                    elif event_key == keyboard.Key.f7:
                        if current_audio:
                            current_audio.stop()
                        play_sync_me("?")
                        if remaining_patience > 0:
                            remaining_patience -= 1
                            msg_to_rpt = msg_call if current_stage == "CALL" else msg_exchange
                            play_async(msg_to_rpt, speed=dx_speed, pitch=dx_pitch, l=dx_l, s=dx_s, p=dx_p)
                        else:
                            print(f" {msg_full_for_stats.upper()} (NIL)")
                            qso_done = True

                    elif event_key == keyboard.Key.f8:
                        if current_audio:
                            current_audio.stop()
                        play_sync_me("NIL")
                        print(f" {msg_full_for_stats.upper()} (NIL)")
                        qso_done = True

                    elif event_key == keyboard.Key.f5:
                        if current_audio:
                            current_audio.stop()
                        play_sync_me("?")
                        if remaining_patience > 0:
                            remaining_patience -= 1
                            play_async(msg_call, speed=dx_speed, pitch=dx_pitch, l=dx_l, s=dx_s, p=dx_p)
                        else:
                            print(f" {msg_full_for_stats.upper()} (NIL)")
                            qso_done = True

                    elif event_key == keyboard.Key.f6:
                        if current_audio:
                            current_audio.stop()
                        play_sync_me("?")
                        if remaining_patience > 0:
                            remaining_patience -= 1
                            play_async(msg_serial_only, speed=dx_speed, pitch=dx_pitch, l=dx_l, s=dx_s, p=dx_p)
                        else:
                            print(f" {msg_full_for_stats.upper()} (NIL)")
                            qso_done = True

                    elif hasattr(event_key, "char") and event_key.char == "w" and "alt" in current_modifiers:
                        if current_audio:
                            current_audio.stop()
                        current_buffer = []
                        print(f"\r{' ' * 79}", end="\r", flush=True)
                        redraw_line()

                    elif hasattr(event_key, "char") and event_key.char:
                        if event_key.char.isalnum() or event_key.char in [" ", "/"]:
                            current_buffer.append(event_key.char)
                            print(event_key.char, end="", flush=True)

                except queue.Empty:
                    pass

            if not final_call_ok or not final_serial_ok:
                item_details.append({"rwpm": rwpm_qso, "correct": False})

            if final_call_ok:
                total_calls_correct += 1
            if final_serial_ok:
                total_serials_correct += 1

            if current_audio:
                current_audio.wait_done()
            time.sleep(1.0)

            active_exerctime += dt.datetime.now() - item_start_time
            session_calls += 1

    finally:
        if current_audio:
            current_audio.stop()
        play_sync_me("_ + QRT TU E E")
        stop_event.set()
        listener.stop()
        if os.name == "nt":
            import msvcrt

            while msvcrt.kbhit():
                msvcrt.getch()
        else:
            import sys
            import termios

            try:  # noqa: SIM105 -- il commento spiega perche' si tace
                termios.tcflush(sys.stdin, termios.TCIOFLUSH)
            except (OSError, termios.error):
                # Svuotare la tastiera e' un di piu': se non riesce, pazienza.
                pass

        # --- STATS SAVING ---
        if session_calls == 0:
            # Uscita prima del primo QSO: non c'e' niente da registrare, e una
            # sessione vuota sporcherebbe le medie dell'archivio storico.
            print(_("Contest chiuso prima del primo QSO: niente da salvare."))
            key(_("Premi un tasto per tornare al menu..."))
        else:
            elapsed_total = (dt.datetime.now() - start_time).total_seconds()
            wrong_calls = session_calls - correct_calls
            stats = app_data["rxing_stats_qrz"]
            stats["sessions"] += 1
            stats["total_calls"] += session_calls
            stats["total_correct"] += correct_calls
            stats["total_wrong_items"] += wrong_calls
            stats["total_time_seconds"] += elapsed_total
            avg_wpm_calc = sum_wpm / session_calls if session_calls > 0 else 0
            send_char = sum(sent_chars_detail_this_session.values())
            session_data_for_history = {
                "timestamp_iso": start_time.isoformat(),
                "duration_seconds": active_exerctime.total_seconds(),
                "rwpm_min": minwpm if minwpm is not None else 0,
                "rwpm_max": maxwpm,
                "rwpm_avg": avg_wpm_calc,
                "items_sent_session": session_calls,
                "items_correct_session": correct_calls,
                "item_details": item_details,
                "chars_sent_session": send_char,
                "errors_detail_session": char_error_counts,
                "total_errors_chars_session": total_mistakes_calculated,
                "sent_chars_detail_session": sent_chars_detail_this_session,
            }
            historical_data = app_data["historical_rx_data_qrz"]
            historical_rx_log = historical_data.get("sessions_log", [])
            historical_rx_log.append(session_data_for_history)
            historical_settings = app_data["historical_rx_settings"]
            g = historical_settings.get("max_sessions_to_keep", HISTORICAL_RX_MAX_SESSIONS_DEFAULT)
            while len(historical_rx_log) > g:
                historical_rx_log.pop(0)
            historical_data["sessions_log"] = historical_rx_log

            # --- REPORT A VIDEO ---
            print(_("\nÈ finita! Ora vediamo cosa abbiamo ottenuto."))
            percentage_correct = correct_calls * 100 / session_calls if session_calls > 0 else 0
            call_acc = total_calls_correct * 100 / session_calls if session_calls > 0 else 0
            serial_acc = total_serials_correct * 100 / session_calls if session_calls > 0 else 0
            print(
                _("In questa sessione #{sessions}, ti ho inviato {calls} QRZ e ne hai ricevuti {callsget_len}: {percentage:.1f}%").format(
                    sessions=stats["sessions"], calls=session_calls, callsget_len=correct_calls, percentage=percentage_correct
                )
            )
            print(_("\tCorrettezza Nominativi: {total_calls_correct}/{calls} ({call_acc:.1f}%)").format(total_calls_correct=total_calls_correct, calls=session_calls, call_acc=call_acc))
            print(_("\tCorrettezza Progressivi: {total_serials_correct}/{calls} ({serial_acc:.1f}%)").format(total_serials_correct=total_serials_correct, calls=session_calls, serial_acc=serial_acc))
            print(
                _(
                    "Durante la sessione, la tua velocità minima è stata {minwpm:.2f}, la massima di {maxwpm:.2f}: pari ad una variazione di {range_wpm:.2f} WPM.\n\tLa velocità media di ricezione è di: {average_wpm:.2f} WPM."
                ).format(minwpm=minwpm, maxwpm=maxwpm, range_wpm=maxwpm - minwpm, average_wpm=avg_wpm_calc)
            )
            if total_mistakes_calculated > 0:
                print(_("Carattere: errori = Intervallo di Confidenza Errore (Wilson)"))
                sorted_errors = sorted(char_error_counts.items(), key=lambda item: (-item[1], item[0]))
                for char, errori in sorted_errors:
                    inviati = sent_chars_detail_this_session.get(char, 0)
                    inf = wilson_score_lower_bound(errori, inviati) * 100
                    sup = wilson_score_upper_bound(errori, inviati) * 100
                    print(
                        _("    '{char_display}': {errori} errori su {inviati} invii. Tasso errore stimato: [{inf:.1f}% - {sup:.1f}%]").format(
                            char_display=char.upper(), errori=errori, inviati=inviati, inf=inf, sup=sup
                        )
                    )
                mistake_percentage = total_mistakes_calculated * 100 / send_char if send_char > 0 else 0
                print(
                    _("\nErrori totali: {global_mistakes} su {send_char} = {mistake_percentage:.2f}%").format(
                        global_mistakes=total_mistakes_calculated, send_char=send_char, mistake_percentage=mistake_percentage
                    )
                )

            # --- DIARY SAVING ---
            duration_str = str(active_exerctime).split(".")[0]
            adesso = dt.datetime.now()
            date_str = adesso.strftime("%Y/%m/%d")
            time_str = adesso.strftime("%H:%M")
            diario_scritto = False
            try:
                with open(DIARY_FILE, "a", encoding="utf-8") as f:
                    f.write(_("\nEsercizio di ricezione CONTEST #{sessions} eseguito il {date} alle {time} minuti:\n").format(sessions=stats["sessions"], date=date_str, time=time_str))
                    f.write(_("Durata: {duration}\n").format(duration=duration_str))
                    f.write(
                        _("In questa sessione, ti ho inviato {calls} QRZ e ne hai ricevuti {callsget_len}: {percentage:.1f}%").format(
                            calls=session_calls, callsget_len=correct_calls, percentage=percentage_correct
                        )
                        + "\n"
                    )
                    f.write(
                        _("\tCorrettezza Nominativi: {total_calls_correct}/{calls} ({call_acc:.1f}%)").format(total_calls_correct=total_calls_correct, calls=session_calls, call_acc=call_acc) + "\n"
                    )
                    f.write(
                        _("\tCorrettezza Progressivi: {total_serials_correct}/{calls} ({serial_acc:.1f}%)").format(
                            total_serials_correct=total_serials_correct, calls=session_calls, serial_acc=serial_acc
                        )
                        + "\n"
                    )
                    f.write(_("Velocità: Min {minwpm:.2f}, Max {maxwpm:.2f}, Avg {average_wpm:.2f} WPM.").format(minwpm=minwpm, maxwpm=maxwpm, average_wpm=avg_wpm_calc) + "\n")
                    if total_mistakes_calculated > 0:
                        f.write(_("Carattere: errori = Wilson Interval") + "\n")
                        for char, errori in sorted(char_error_counts.items(), key=lambda item: (-item[1], item[0])):
                            inviati = sent_chars_detail_this_session.get(char, 0)
                            inf = wilson_score_lower_bound(errori, inviati) * 100
                            sup = wilson_score_upper_bound(errori, inviati) * 100
                            f.write(f"    '{char.upper()}': {errori}/{inviati} [{inf:.1f}% - {sup:.1f}%]\n")
                    f.write(FINE_RECORD_DIARIO)
                diario_scritto = True
            except OSError as e:
                print(_("Diario non scritto: {errore}").format(errore=e))
            if diario_scritto:
                print(_("Rapporto salvato su {nome_diario}").format(nome_diario=DIARY_NAME))
                print(_("\nSessione {session_number}, durata attiva: {duration} è stata salvata su disco.").format(session_number=stats["sessions"], duration=duration_str))
            key(_("Premi un tasto per tornare al menu..."))


def Rxing():
    global overall_speed, words
    print(
        _("\nE' il momento giusto per un bell'esercizio di ricezione? Ottimo, allora sei nel posto giusto.\nIniziamo!\n\tCarico lo stato dei tuoi progressi e controllo il database del dizionario...")
    )

    # Ha la precedenza il words.txt messo dall'utente accanto al programma,
    # altrimenti si usa quello incluso nel pacchetto.
    words_file_path = user_file_path("words.txt")
    try:
        with open(words_file_path, encoding="utf-8") as file:
            words = [line.strip() for line in file]
        print(_("Dizionario delle parole caricato con {word_count} parole.").format(word_count=len(words)))
    except OSError as e:
        words = []
        print(_("Dizionario delle parole non caricato: {errore}.\n\tGli esercizi sulle parole non sono disponibili.").format(errore=e))

    # Sposta la selezione della modalità qui, prima della visualizzazione delle statistiche
    menu_config_scelta = seleziona_modalita_rx()
    if not menu_config_scelta:
        return

    # Estrai i parametri della sessione dalla scelta dell'utente
    active_states = menu_config_scelta["active_switcher_states"]

    if active_states.get("contest"):
        RxingContest(menu_config_scelta)
        return

    parole_filtrate_per_sessione = menu_config_scelta["parole_filtrate_list"]
    custom_set_attivo_per_sessione = menu_config_scelta["custom_set_string_active"]
    lunghezza_gruppo_per_generati = menu_config_scelta["group_length_for_generated"]

    # Determina la categoria (words, chars, qrz)
    category_key = ""
    # La logica è che se le "parole" sono attive, è un esercizio di parole.
    # Altrimenti, se "qrz" è attivo, è un esercizio di qrz.
    # Altrimenti, è un esercizio di caratteri/misto.
    if active_states.get("parole"):
        category_key = "words"
    elif active_states.get("qrz"):
        category_key = "qrz"
    else:  # Qualsiasi altra combinazione (lettere, numeri, simboli, custom, misto)
        category_key = "chars"

    # Seleziona i dizionari di statistiche e dati storici corretti per la sessione corrente
    current_rx_stats = app_data[f"rxing_stats_{category_key}"]
    current_historical_data = app_data[f"historical_rx_data_{category_key}"]
    historical_settings = app_data["historical_rx_settings"]  # Le impostazioni sono condivise per tutte le categorie

    # Ora usa current_rx_stats e current_historical_data per il resto della funzione

    totalcalls = current_rx_stats.get("total_calls", 0)
    sessions = current_rx_stats.get("sessions", 0)  # Inizializzato a 0 in DEFAULT_DATA
    numero_sessione = sessions + 1  # La sessione che sta per cominciare: unico numero usato ovunque
    totalget = current_rx_stats.get("total_correct", 0)
    totalwrong = current_rx_stats.get("total_wrong_items", 0)
    totaltime_seconds = current_rx_stats.get("total_time_seconds", 0.0)
    totaltime = dt.timedelta(seconds=totaltime_seconds)
    formatted_time = format_duration(totaltime)

    # Messaggio di benvenuto aggiornato
    print(
        _(
            "Ho recuperato i tuoi dati dal disco per gli esercizi di {category_name}, quindi:\nLa tua attuale velocità WPM è {wpm} e hai svolto {sessions} sessioni.\nTi ho inviato {totalcalls} pseudo-call o gruppi e ne hai ricevuti correttamente {totalget}, mentre {totalwrong} li hai copiati male.\nIl tempo totale speso su questo esercizio è stato di {totaltime}."
        ).format(
            category_name=_("parole") if category_key == "words" else _("caratteri/misto") if category_key == "chars" else "QRZ",
            wpm=overall_speed,
            sessions=sessions,  # Non più sessions - 1, perché sessions conterà le sessioni completate
            totalcalls=totalcalls,
            totalget=totalget,
            totalwrong=totalwrong,
            totaltime=formatted_time,
        )
    )

    callssend = []
    average_rwpm = 0.0
    dz_mistakes = {}
    calls = 1
    callsget = []
    callswrong = []
    item_details = []
    callsrepeated = 0
    minwpm = 100
    maxwpm = 0
    repeatedflag = False

    # Usa le impostazioni storiche condivise
    report_interval = historical_settings.get("report_interval", HISTORICAL_RX_REPORT_INTERVAL)

    overall_speed = dgt(
        prompt=_("Vuoi cambiare la velocità in WPM, da {minimo} a {massimo}? Invio per accettare {wpm}> ").format(minimo=WPM_MIN, massimo=WPM_MAX, wpm=overall_speed),
        kind="i",
        imin=WPM_MIN,
        imax=WPM_MAX,
        default=overall_speed,
    )
    rwpm = overall_speed
    _clear_screen_ansi()
    active_labels_for_display = []
    for item_cfg_ks in RX_SWITCHER_ITEMS:
        if active_states.get(item_cfg_ks["key_state"]):
            active_labels_for_display.append(item_cfg_ks["etichetta"].capitalize())
    if not active_labels_for_display:
        kindstring = "N/A"
    elif len(active_labels_for_display) == 1:
        kindstring = active_labels_for_display[0]
    else:
        kindstring = _("Misto ({types})").format(types=", ".join(active_labels_for_display))
    how_many_calls = dgt(prompt=_("\nQuanti ne vuoi ricevere? (INVIO per infinito)> "), kind="i", imin=10, imax=1000, default=0)
    prompt_vel = _("Invio per velocità variabile, Esc per velocità fissa: ")
    vel_variabile = enter_escape(prompt=prompt_vel)
    fix_speed = not vel_variabile
    print(
        _(
            "Fai molta attenzione adesso.\n\tDigita il {kindstring} che ascolti.\nBattendo invio a vuoto (o aggiungendo un ?) avrai l'opportunità di un secondo tentativo\n\tPer terminare: digita semplicemente un '.' (punto) seguito da dal tasto invio.\n\t\tBUON DIVERTIMENTO!\n\tPremi un tasto quando sei pronto per iniziare."
        ).format(kindstring=kindstring)
    )
    key()
    print(_("Iniziamo la sessione {sessions}!").format(sessions=numero_sessione))
    starttime = dt.datetime.now()
    active_exerctime = dt.timedelta(0)
    total_pause_time = dt.timedelta(0)
    while True:
        total_wait_duration_for_item = dt.timedelta(0)
        if how_many_calls > 0 and len(callssend) >= how_many_calls:
            break
        qrz_to_send = genera_singolo_item_esercizio_misto(active_states, lunghezza_gruppo_per_generati, custom_set_attivo_per_sessione, parole_filtrate_per_sessione)
        if qrz_to_send is None or qrz_to_send == "ERROR_NO_VALID_TYPES":
            print(_("Errore: Impossibile generare item per l'esercizio con le selezioni attuali. Controlla le impostazioni del menu Rx."))
            break
        pitch = random.randint(250, 1050)
        avg_wpm_display = average_rwpm / len(callsget) if len(callsget) else rwpm
        prompt = _("S{sessions}-#{calls} - WPM{rwpm:.2f}/{avg_wpm_display:.2f} - +{correct_count}/-{wrong_count}> ").format(
            avg_wpm_display=avg_wpm_display, correct_count=len(callsget), wrong_count=len(callswrong), sessions=numero_sessione, calls=calls, rwpm=rwpm
        )
        _plo, rwpm = suona(qrz_to_send, pitch=pitch)
        wait_start_1 = dt.datetime.now()
        guess = dgt(prompt=prompt, kind="s", smin=0, smax=64)
        wait_end_1 = dt.datetime.now()
        total_wait_duration_for_item += wait_end_1 - wait_start_1
        if guess == ".":
            break
        needs_processing = True
        if guess == "" or guess.endswith("?"):
            repeatedflag = True
            partial_input = ""
            prompt_indicator = "% "
            if guess.endswith("?"):
                partial_input = guess[:-1]
                prompt_indicator = f"% {partial_input}"
            prompt = _("S{sessions}-#{calls} - WPM{rwpm:.2f}/{:.2f} - +{}/-{} - {prompt_indicator}").format(
                average_rwpm / len(callsget) if len(callsget) else rwpm, len(callsget), len(callswrong), sessions=numero_sessione, calls=calls, rwpm=rwpm, prompt_indicator=prompt_indicator
            )
            _plo, rwpm = suona(qrz_to_send, pitch=pitch)
            wait_start_2 = dt.datetime.now()
            new_guess = dgt(prompt=prompt, kind="s", smin=0, smax=64)
            wait_end_2 = dt.datetime.now()
            total_wait_duration_for_item += wait_end_2 - wait_start_2
            if new_guess == ".":
                needs_processing = False
                break
            guess = partial_input + new_guess
        timeout_delta = dt.timedelta(seconds=RX_ITEM_TIMEOUT_SECONDS)
        if total_wait_duration_for_item > timeout_delta:
            active_time_for_item = timeout_delta
            pause_for_item = total_wait_duration_for_item - timeout_delta
            total_pause_time += pause_for_item
        else:
            active_time_for_item = total_wait_duration_for_item
        active_exerctime += active_time_for_item
        if needs_processing:
            original_qrz = qrz_to_send
            callssend.append(original_qrz)
            guess = guess.lower()
            if original_qrz == guess:
                suona("r _ _ ", pitch=pitch, sync=True)
                callsget.append(original_qrz)
                average_rwpm += rwpm
                item_details.append({"wpm": rwpm, "correct": True})
                if repeatedflag:
                    callsrepeated += 1
                if not fix_speed and overall_speed < WPM_MAX:
                    overall_speed += 1
            else:
                callswrong.append(original_qrz)
                item_details.append({"wpm": rwpm, "correct": False})
                suona("? _ _ ", pitch=pitch, sync=True)
                diff = MistakesCollectorInStrings(original_qrz, guess)
                diff_ratio = (1 - difflib.SequenceMatcher(None, original_qrz, guess).ratio()) * 100
                print(_("TX: {} RX: {} <>: {} RT: {}").format(original_qrz.upper(), guess.upper(), diff.upper(), int(diff_ratio)))
                dz_mistakes[len(callssend)] = (original_qrz, guess)
                if not fix_speed and overall_speed > WPM_MIN:
                    overall_speed -= 1
            calls += 1
            maxwpm = max(maxwpm, rwpm)
            minwpm = min(minwpm, rwpm)
            repeatedflag = False
    print(_("È finita! Ora vediamo cosa abbiamo ottenuto."))
    send_char = sum(len(j) for j in callssend)
    sent_chars_detail_this_session = {}
    for item_str in callssend:
        for char_sent in item_str:
            sent_chars_detail_this_session[char_sent] = sent_chars_detail_this_session.get(char_sent, 0) + 1
    char_error_counts = {}
    total_mistakes_calculated = 0
    for right_str, received_str in dz_mistakes.values():
        total_mistakes_calculated += collect_char_errors(right_str, received_str, char_error_counts)
    avg_wpm_calc = average_rwpm / len(callsget) if len(callsget) > 0 else float(overall_speed)
    if minwpm > maxwpm:
        minwpm = float(overall_speed)
        maxwpm = float(overall_speed)

    if len(callssend) >= 10:
        total_sent_processed = len(callssend)
        percentage_correct = len(callsget) * 100 / total_sent_processed if total_sent_processed > 0 else 0
        print(
            _("In questa sessione #{sessions}, ti ho inviato {calls} {kindstring} e ne hai ricevuti {callsget_len}: {percentage:.1f}%").format(
                sessions=numero_sessione, calls=total_sent_processed, kindstring=kindstring, callsget_len=len(callsget), percentage=percentage_correct
            )
        )
        first_shot_correct = len(callsget) - callsrepeated
        first_shot_percentage = first_shot_correct * 100 / len(callsget) if len(callsget) > 0 else 0
        repetitions_percentage = callsrepeated * 100 / len(callsget) if len(callsget) > 0 else 0
        print(_("\t{first_shot} di questi sono stati ricevuti al primo ascolto: {first_shot_percentage:.1f}%").format(first_shot=first_shot_correct, first_shot_percentage=first_shot_percentage))
        print(
            _("\tmentre {repetitions} {kindstring} al secondo tentativo: {repetitions_percentage:.1f}%.").format(
                repetitions=callsrepeated, kindstring=kindstring, repetitions_percentage=repetitions_percentage
            )
        )
        print(
            _(
                "Durante la sessione, la tua velocità minima è stata {minwpm:.2f}, la massima di {maxwpm:.2f}: pari ad una variazione di {range_wpm:.2f} WPM.\n\tLa velocità media di ricezione è di: {average_wpm:.2f} WPM."
            ).format(minwpm=minwpm, maxwpm=maxwpm, range_wpm=maxwpm - minwpm, average_wpm=avg_wpm_calc)
        )
        print(_("Carattere: errori = Intervallo di Confidenza Errore (Wilson)"))
        if total_mistakes_calculated > 0:
            sorted_errors = sorted(char_error_counts.items(), key=lambda item: (-item[1], item[0]))
            for char, errori in sorted_errors:
                inviati = sent_chars_detail_this_session.get(char, 0)
                limite_inferiore = wilson_score_lower_bound(errori, inviati) * 100
                limite_superiore = wilson_score_upper_bound(errori, inviati) * 100
                print(
                    _("    '{char_display}': {errori} errori su {inviati} invii. Tasso errore stimato: [{inf:.1f}% - {sup:.1f}%]").format(
                        char_display=char.upper(), errori=errori, inviati=inviati, inf=limite_inferiore, sup=limite_superiore
                    )
                )
            mistake_percentage = total_mistakes_calculated * 100 / send_char if send_char > 0 else 0
            print(
                _("\nErrori totali: {global_mistakes} su {send_char} = {mistake_percentage:.2f}%").format(
                    global_mistakes=total_mistakes_calculated, send_char=send_char, mistake_percentage=mistake_percentage
                )
            )
            good_letters = AlwaysRight(callssend, char_error_counts)
            print(_("\nCaratteri mai sbagliati: {good_letters}").format(good_letters=" ".join(sorted(good_letters)).upper()))
        else:
            print(_("Nessun errore sui caratteri registrato in questa sessione."))
        historical_rx_settings = app_data.get("historical_rx_settings", {})
        report_interval = historical_rx_settings.get("report_interval", HISTORICAL_RX_REPORT_INTERVAL)
        if report_interval > 0:
            chars_done = app_data[f"historical_rx_data_{category_key}"].get("chars_since_last_report", 0) + send_char
            chars_target = report_interval
            percentage_done = chars_done / chars_target * 100 if chars_target > 0 else 0.0
            chars_missing = max(0, chars_target - chars_done)
            print(
                _("Completamento sezione corrente:\n+{s} -> ({x} / {y}) = {z}%, ne mancano {w} alla prossima generazione.").format(
                    s=send_char, x=chars_done, y=chars_target, z=f"{percentage_done:.2f}", w=chars_missing
                )
            )
        else:
            print(_("La generazione automatica dei report è disabilitata."))
        nota = dgt(prompt=_("\nNota su questo esercizio: "), kind="s", smin=0, smax=512)
        adesso = dt.datetime.now()
        date_str = adesso.strftime("%Y/%m/%d")
        time_str = adesso.strftime("%H:%M")
        try:
            with open(DIARY_FILE, "a", encoding="utf-8") as f:
                f.write(_("\nEsercizio di ricezione #{sessions} eseguito il {date} alle {time} minuti:\n").format(sessions=numero_sessione, date=date_str, time=time_str))
                f.write(
                    _("In questa sessione #{sessions}, ti ho inviato {calls} {kindstring} e ne hai ricevuti {callsget_len}: {percentage:.1f}%").format(
                        sessions=numero_sessione, calls=total_sent_processed, kindstring=kindstring, callsget_len=len(callsget), percentage=percentage_correct
                    )
                    + "\n"
                )
                f.write(
                    _("\t{first_shot} di questi sono stati ricevuti al primo ascolto: {first_shot_percentage:.1f}%").format(first_shot=first_shot_correct, first_shot_percentage=first_shot_percentage)
                    + "\n"
                )
                f.write(
                    _("\tmentre {repetitions} {kindstring} al secondo tentativo: {repetitions_percentage:.1f}%.").format(
                        repetitions=callsrepeated, kindstring=kindstring, repetitions_percentage=repetitions_percentage
                    )
                    + "\n"
                )
                f.write(
                    _(
                        "Durante la sessione, la tua velocità minima è stata {minwpm:.2f}, la massima di {maxwpm:.2f}: pari ad una variazione di {range_wpm:.2f} WPM.\n\tLa velocità media di ricezione è di: {average_wpm:.2f} WPM."
                    ).format(minwpm=minwpm, maxwpm=maxwpm, range_wpm=maxwpm - minwpm, average_wpm=avg_wpm_calc)
                    + "\n"
                )
                f.write(_("Carattere: errori = Intervallo di Confidenza Errore (Wilson)"))
                if total_mistakes_calculated > 0:
                    sorted_errors = sorted(char_error_counts.items(), key=lambda item: (-item[1], item[0]))
                    for char, errori in sorted_errors:
                        inviati = sent_chars_detail_this_session.get(char, 0)
                        limite_inferiore = wilson_score_lower_bound(errori, inviati) * 100
                        limite_superiore = wilson_score_upper_bound(errori, inviati) * 100
                        f.write(
                            _("    '{char_display}': {errori} errori su {inviati} invii. Tasso errore stimato: [{inf:.1f}% - {sup:.1f}%]").format(
                                char_display=char.upper(), errori=errori, inviati=inviati, inf=limite_inferiore, sup=limite_superiore
                            )
                        )
                    f.write("\n")
                    f.write(
                        _("\nErrori totali: {global_mistakes} su {send_char} = {mistake_percentage:.2f}%").format(
                            global_mistakes=total_mistakes_calculated, send_char=send_char, mistake_percentage=mistake_percentage
                        )
                    )
                    f.write(_("\nCaratteri mai sbagliati: {good_letters}").format(good_letters=" ".join(sorted(good_letters)).upper()))
                else:
                    f.write("\n" + _("Nessun errore sui caratteri registrato in questa sessione.") + "\n")
                f.write(_("\nElenco delle parole copiate male:"))
                for k, v in sorted(dz_mistakes.items()):
                    rslt = MistakesCollectorInStrings(v[0], v[1])
                    f.write(_("\n\t({k}) TX: {tx}, RX: {rx}, DIF: {dif};").format(k=k, tx=v[0].upper(), rx=v[1].upper(), dif=rslt.upper()))
                if nota != "":
                    f.write(_("Nota: {nota}").format(nota=nota) + "\n" + FINE_RECORD_DIARIO)
                else:
                    f.write("\n" + _("Nota: nessuna") + "\n" + FINE_RECORD_DIARIO)
            print(_("Rapporto salvato su {nome_diario}").format(nome_diario=DIARY_NAME))
        except OSError as e:
            print(_("Diario non scritto: {errore}").format(errore=e))
    else:
        print(_("Hai ricevuto troppo pochi {kindstring} per generare statistiche consistenti.").format(kindstring=kindstring))
    current_session_items = len(callssend)
    current_session_correct = len(callsget)
    current_session_wrong = len(dz_mistakes)

    new_totalcalls = current_rx_stats["total_calls"] + current_session_items
    new_totalget = current_rx_stats["total_correct"] + current_session_correct
    new_totalwrong = current_rx_stats["total_wrong_items"] + current_session_wrong
    new_totaltime = dt.timedelta(seconds=current_rx_stats["total_time_seconds"]) + active_exerctime

    current_rx_stats.update(
        {
            "total_calls": new_totalcalls,
            "sessions": current_rx_stats["sessions"] + 1,
            "total_correct": new_totalget,
            "total_wrong_items": new_totalwrong,
            "total_time_seconds": new_totaltime.total_seconds(),
        }
    )

    corrected_item_details = [{"rwpm": item["wpm"], "correct": item["correct"]} for item in item_details]
    session_data_for_history = {
        "timestamp_iso": starttime.isoformat(),
        "duration_seconds": active_exerctime.total_seconds(),
        "rwpm_min": minwpm,
        "rwpm_max": maxwpm,
        "rwpm_avg": avg_wpm_calc,
        "items_sent_session": len(callssend),
        "items_correct_session": len(callsget),
        "item_details": corrected_item_details,
        "chars_sent_session": send_char,
        "errors_detail_session": char_error_counts,
        "total_errors_chars_session": total_mistakes_calculated,
        "sent_chars_detail_session": sent_chars_detail_this_session,
    }

    historical_rx_log = current_historical_data.get("sessions_log", [])
    historical_rx_log.append(session_data_for_history)

    g = historical_settings.get("max_sessions_to_keep", HISTORICAL_RX_MAX_SESSIONS_DEFAULT)

    while len(historical_rx_log) > g:
        sessione_eliminata = historical_rx_log.pop(0)
        data_sessione_str = sessione_eliminata.get("timestamp_iso", "N/D")
        data_sessione_dt = dt.datetime.fromisoformat(data_sessione_str).strftime("%Y-%m-%d %H:%M")
        durata_sessione = int(sessione_eliminata.get("duration_seconds", 0))
        contenuto_sessione = sessione_eliminata.get("chars_sent_session", 0)
        print(
            _("Sessione del {data}, durata {durata}s, contenuto {contenuto} caratteri, eliminata dalla coda degli esercizi di {category_name}.").format(
                data=data_sessione_dt,
                durata=durata_sessione,
                contenuto=contenuto_sessione,
                category_name=_("parole") if category_key == "words" else _("caratteri/misto") if category_key == "chars" else "QRZ",
            )
        )

    current_historical_data["chars_since_last_report"] = current_historical_data.get("chars_since_last_report", 0) + send_char
    current_historical_data["sessions_log"] = historical_rx_log

    if report_interval > 0 and current_historical_data["chars_since_last_report"] >= report_interval:
        print(_("Generazione report storico in corso..."))
        sessions_log = current_historical_data.get("sessions_log", [])
        chars_to_account_for = current_historical_data["chars_since_last_report"]
        sessions_for_this_report = []
        accumulated_chars = 0
        for session in reversed(sessions_log):
            sessions_for_this_report.insert(0, session)
            accumulated_chars += session.get("chars_sent_session", 0)
            if accumulated_chars >= chars_to_account_for:
                break
        new_report_aggregates = generate_historical_rx_report(sessions_for_this_report, category_key)
        if new_report_aggregates:
            historical_reports = current_historical_data.get("historical_reports", [])
            historical_reports.append(new_report_aggregates)
            current_historical_data["historical_reports"] = historical_reports
        chars_in_this_report = accumulated_chars
        overshoot = chars_in_this_report - report_interval
        current_historical_data["chars_since_last_report"] = max(0, overshoot)

    duration_str = str(active_exerctime).split(".")[0]
    print(_("\nSessione {session_number}, durata attiva: {duration} è stata salvata su disco.").format(session_number=current_rx_stats["sessions"], duration=duration_str))
    if total_pause_time.total_seconds() > 0:
        pause_str = str(total_pause_time).split(".")[0]
        print(_("\t(Tempo totale in pausa rilevato: {pause_time})").format(pause_time=pause_str))
    # La lunghezza si legge dopo la potatura, altrimenti a limite raggiunto
    # l'applicazione annunciava una sessione di troppo e uno spazio negativo.
    x = len(historical_rx_log)
    print(
        _("L'archivio ora contiene {x} sessioni salvate per gli esercizi di {category_name}, ancora {g_minus_x} al raggiungimento del limite stabilito.").format(
            x=x, g_minus_x=max(0, g - x), category_name=_("parole") if category_key == "words" else _("caratteri/misto") if category_key == "chars" else "QRZ"
        )
    )
    return


def _calculate_aggregates(session_list):
    """
    Calcola statistiche aggregate da una lista di dati di sessione.
    Restituisce un dizionario con le statistiche aggregate.
    """
    if not session_list:
        return {
            "num_sessions_in_block": 0,
            "total_duration_seconds": 0.0,
            "wpm_min_overall": 0,
            "wpm_max_overall": 0,
            "wpm_avg_of_session_avgs": 0.0,
            "total_items_sent": 0,
            "total_items_correct": 0,
            "total_chars_sent_overall": 0,
            "aggregated_errors_detail": {},
            "total_errors_chars_overall": 0,
            "aggregated_sent_chars_detail": {},
        }
    total_duration_seconds = sum(s.get("duration_seconds", 0) for s in session_list)
    total_chars_sent_overall = sum(s.get("chars_sent_session", 0) for s in session_list)
    aggregated_sent_chars_detail = {}
    for s in session_list:
        for char, count in s.get("sent_chars_detail_session", {}).items():
            aggregated_sent_chars_detail[char] = aggregated_sent_chars_detail.get(char, 0) + count
    # Niente eccezione per il 100: era l'aggiramento delle sessioni vuote, che
    # adesso non si registrano piu' e che load_settings toglie dall'archivio.
    valid_min_wpms = [s.get("rwpm_min", 0) for s in session_list if s.get("rwpm_min", 0) > 0]
    valid_max_wpms = [s.get("rwpm_max", 0) for s in session_list if s.get("rwpm_max", 0) > 0]
    wpm_min_overall = min(valid_min_wpms) if valid_min_wpms else 0
    wpm_max_overall = max(valid_max_wpms) if valid_max_wpms else 0
    sum_of_session_avg_wpms = sum(s.get("rwpm_avg", 0.0) for s in session_list)
    wpm_avg_of_session_avgs = sum_of_session_avg_wpms / len(session_list)
    total_items_sent = sum(s.get("items_sent_session", 0) for s in session_list)
    total_items_correct = sum(s.get("items_correct_session", 0) for s in session_list)
    aggregated_errors_detail = {}
    total_errors_chars_overall = 0
    for s in session_list:
        total_errors_chars_overall += s.get("total_errors_chars_session", 0)
        for char, count in s.get("errors_detail_session", {}).items():
            aggregated_errors_detail[char] = aggregated_errors_detail.get(char, 0) + count
    return {
        "num_sessions_in_block": len(session_list),
        "total_duration_seconds": total_duration_seconds,
        "wpm_min_overall": wpm_min_overall,
        "wpm_max_overall": wpm_max_overall,
        "wpm_avg_of_session_avgs": wpm_avg_of_session_avgs,
        "total_items_sent": total_items_sent,
        "total_items_correct": total_items_correct,
        "total_chars_sent_overall": total_chars_sent_overall,
        "aggregated_errors_detail": aggregated_errors_detail,
        "total_errors_chars_overall": total_errors_chars_overall,
        "aggregated_sent_chars_detail": aggregated_sent_chars_detail,
    }


def generate_historical_rx_report(sessions_for_current_report, category_key):
    """
    Genera i report (HTML e grafico) per il blocco di sessioni fornito,
    confrontandoli con l'ultimo report storico salvato.
    Restituisce i dati aggregati del report corrente per poterli salvare.
    """
    if not sessions_for_current_report:
        print(_("Nessuna sessione nel blocco corrente da riportare."))
        return None
    current_aggregates = _calculate_aggregates(sessions_for_current_report)
    num_sessions_in_current_report = current_aggregates["num_sessions_in_block"]

    historical_data = app_data.get(f"historical_rx_data_{category_key}", {})
    historical_settings = app_data.get("historical_rx_settings", {})

    full_sessions_log = historical_data.get("sessions_log", [])
    num_sessions_in_current_block = len(sessions_for_current_report)
    previous_aggregates = None
    if len(full_sessions_log) > num_sessions_in_current_block:
        num_previous_sessions = len(full_sessions_log) - num_sessions_in_current_block
        previous_block_sessions = full_sessions_log[:num_previous_sessions]
        if previous_block_sessions:
            previous_aggregates = _calculate_aggregates(previous_block_sessions)

    g_value = historical_settings.get("max_sessions_to_keep", HISTORICAL_RX_MAX_SESSIONS_DEFAULT)
    x_value = historical_settings.get("report_interval", HISTORICAL_RX_REPORT_INTERVAL)

    cat_name_file = category_key.capitalize()
    report_filename_base = f"CWapu_Historical_Statistics_{cat_name_file}_G_{g_value}_X_{x_value}.html"
    report_filename_full_path = os.path.join(USER_DATA_PATH, report_filename_base)

    cat_display_name = _("parole") if category_key == "words" else _("caratteri/misto") if category_key == "chars" else "QRZ"

    try:
        with open(report_filename_full_path, "w", encoding="utf-8") as f:
            f.write("<!DOCTYPE html>\n")
            f.write(f'<html lang="{app_language[:2]}">\n')
            f.write("<head>\n")
            f.write('    <meta charset="UTF-8">\n')
            f.write(_("    <title>Report Statistiche Storiche Esercizi Rx ({cat}) G{g_value} X{x_value}</title>\n").format(cat=cat_display_name, g_value=g_value, x_value=x_value))
            f.write("    <style>\n")
            f.write("        body { background-color: #282c34; color: #e0e0e0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; }\n")
            f.write("        .container { max-width: 1200px; margin: auto; background-color: #333740; padding: 20px; border-radius: 8px; box-shadow: 0 0 15px rgba(0,0,0,0.5); }\n")
            f.write("        h1, h2, h3 { color: #61afef; border-bottom: 2px solid #61afef; padding-bottom: 5px; margin-top: 30px; }\n")
            f.write("        h1 { text-align: center; font-size: 2em; margin-bottom: 10px; }\n")
            f.write("        .report-subtitle { text-align: center; font-size: 0.9em; color: #abb2bf; margin-bottom: 5px; }\n")
            f.write("        .report-generation-time { text-align: center; font-size: 0.8em; color: #888; margin-bottom: 30px; }\n")
            f.write("        table { border-collapse: collapse; width: 100%; margin-top: 15px; margin-bottom: 30px; box-shadow: 0 0 10px rgba(0,0,0,0.3); }\n")
            f.write("        th, td { border: 1px solid #4b5260; padding: 10px; text-align: left; font-size: 0.9em; }\n")
            f.write("        th { background-color: #3a3f4b; color: #98c379; font-weight: bold; }\n")
            f.write("        tr:nth-child(even) { background-color: #383c44; }\n")
            f.write("        tr:hover { background-color: #484e59; }\n")
            f.write("        .good { color: #98c379; font-weight: bold; } /* Verde per miglioramenti */\n")
            f.write("        .bad { color: #e06c75; font-weight: bold; } /* Rosso per peggioramenti */\n")
            f.write("        .neutral { color: #e5c07b; } /* Giallo/Arancio per neutrali o minimi */\n")
            f.write("        .char-emphasis { font-weight: bold; color: #c678dd; } /* Viola per il carattere in analisi */\n")
            f.write("        .details-label { font-style: italic; color: #abb2bf; font-size: 0.85em; }\n")
            f.write("    </style>\n")
            f.write("</head>\n")
            f.write("<body>\n")
            f.write('    <div class="container">\n')
            f.write(_("<h1>CWAPU - Report Statistiche Storiche Esercizi Rx ({cat})</h1>\n").format(cat=cat_display_name))
            f.write(
                _('<p class="report-subtitle">Statistiche basate su {count} esercizi (G={g_value}, X={x_value})</p>\n').format(count=num_sessions_in_current_report, g_value=g_value, x_value=x_value)
            )
            timestamp_now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(_('<p class="report-generation-time">Report generato il: {timestamp_now}</p>\n').format(timestamp_now=timestamp_now))

            def get_delta_class(delta_value, higher_is_better=True, tolerance=0.01):
                if higher_is_better:
                    if delta_value > tolerance:
                        return "good"
                    if delta_value < -tolerance:
                        return "bad"
                else:
                    if delta_value < -tolerance:
                        return "good"
                    if delta_value > tolerance:
                        return "bad"
                return "neutral"

            f.write(_("<h2>Statistiche Velocità Complessive</h2>\n"))
            f.write("<table>\n")
            f.write(_("  <thead><tr><th>Metrica</th><th>Valore Attuale</th>"))
            if previous_aggregates:
                f.write(_("<th>Valore Precedente</th><th>Variazione</th>"))
            f.write("</tr></thead>\n")
            f.write("  <tbody>\n")
            f.write(_("    <tr><td>WPM Min</td><td>{} WPM</td>").format(current_aggregates["wpm_min_overall"]))
            if previous_aggregates:
                prev_val = previous_aggregates.get("wpm_min_overall", 0)
                delta = current_aggregates["wpm_min_overall"] - prev_val
                delta_class = get_delta_class(delta, higher_is_better=True)
                perc_delta_str = f" ({delta / prev_val * 100}%)" if prev_val != 0 else ""
                f.write(
                    _('<td>{prev_val} WPM</td><td class="{delta_class}">{delta} WPM{perc_delta_str}</td>').format(
                        prev_val=prev_val, delta_class=delta_class, delta=delta, perc_delta_str=perc_delta_str
                    )
                )
            f.write("</tr>\n")
            f.write(_("    <tr><td>WPM Max</td><td>{} WPM</td>").format(current_aggregates["wpm_max_overall"]))
            if previous_aggregates:
                prev_val = previous_aggregates.get("wpm_max_overall", 0)
                delta = current_aggregates["wpm_max_overall"] - prev_val
                delta_class = get_delta_class(delta, higher_is_better=True)
                perc_delta_str = f" ({delta / prev_val * 100}%)" if prev_val != 0 else ""
                f.write(
                    _('<td>{prev_val} WPM</td><td class="{delta_class}">{delta} WPM{perc_delta_str}</td>').format(
                        prev_val=prev_val, delta_class=delta_class, delta=delta, perc_delta_str=perc_delta_str
                    )
                )
            f.write("</tr>\n")
            f.write(_("    <tr><td>WPM Medio (media delle sessioni)</td><td>{} WPM</td>").format(current_aggregates["wpm_avg_of_session_avgs"]))
            if previous_aggregates:
                prev_val = previous_aggregates.get("wpm_avg_of_session_avgs", 0)
                delta = current_aggregates["wpm_avg_of_session_avgs"] - prev_val
                delta_class = get_delta_class(delta, higher_is_better=True)
                perc_delta_str = f" ({delta / prev_val * 100}%)" if prev_val != 0 else ""
                f.write(
                    _('<td>{prev_val} WPM</td><td class="{delta_class}">{delta} WPM{perc_delta_str}</td>').format(
                        prev_val=prev_val, delta_class=delta_class, delta=delta, perc_delta_str=perc_delta_str
                    )
                )
            f.write("</tr>\n")
            f.write("  </tbody>\n</table>\n")
            f.write(_("<h2>Statistiche Errori Complessive</h2>\n"))
            f.write("<table>\n")
            f.write(_("  <thead><tr><th>Metrica</th><th>Valore Attuale</th>"))
            if previous_aggregates:
                f.write(_("<th>Valore Precedente</th><th>Variazione</th>"))
            f.write("</tr></thead>\n")
            f.write("  <tbody>\n")
            f.write(_("    <tr><td>Caratteri totali inviati (nel blocco)</td><td>{}</td>").format(current_aggregates["total_chars_sent_overall"]))
            if previous_aggregates:
                prev_val = previous_aggregates.get("total_chars_sent_overall", 0)
                delta = current_aggregates["total_chars_sent_overall"] - prev_val
                perc_delta_str = f" ({delta / prev_val * 100}%)" if prev_val != 0 else ""
                f.write(_("<td>{prev_val}</td><td>{delta} {perc_delta_str}</td>").format(prev_val=prev_val, delta=delta, perc_delta_str=perc_delta_str))
            f.write("</tr>\n")
            total_chars_curr = current_aggregates["total_chars_sent_overall"]
            total_errs_curr = current_aggregates["total_errors_chars_overall"]
            overall_error_rate_curr = total_errs_curr / total_chars_curr * 100 if total_chars_curr > 0 else 0.0
            f.write(
                _("    <tr><td>Tasso errore generale</td><td>{total_errs_curr} / {total_chars_curr} ({overall_error_rate_curr}%)</td>").format(
                    total_errs_curr=total_errs_curr, total_chars_curr=total_chars_curr, overall_error_rate_curr=overall_error_rate_curr
                )
            )
            if previous_aggregates:
                total_chars_prev = previous_aggregates.get("total_chars_sent_overall", 0)
                total_errs_prev = previous_aggregates.get("total_errors_chars_overall", 0)
                overall_error_rate_prev = total_errs_prev / total_chars_prev * 100 if total_chars_prev > 0 else 0.0
                delta_rate = overall_error_rate_curr - overall_error_rate_prev
                delta_class = get_delta_class(delta_rate, higher_is_better=False)
                f.write(
                    _('<td>{total_errs_prev} / {total_chars_prev} ({overall_error_rate_prev}%)</td><td class="{delta_class}">{delta_rate} punti %</td>').format(
                        total_errs_prev=total_errs_prev, total_chars_prev=total_chars_prev, overall_error_rate_prev=overall_error_rate_prev, delta_class=delta_class, delta_rate=delta_rate
                    )
                )
            f.write("</tr>\n")
            f.write("  </tbody>\n</table>\n")
            if current_aggregates.get("aggregated_errors_detail", {}):
                f.write(_("<h2>Dettaglio errori per carattere</h2>\n"))
                f.write("<table>\n")
                f.write(_('  <thead><tr><th>Carattere</th><th>Errori / Inviati</th><th style="text-align: center;">Intervallo Confidenza Errore (Wilson)</th></tr></thead>\n'))
                f.write("  <tbody>\n")
                sorted_errors = sorted(current_aggregates["aggregated_errors_detail"].items(), key=lambda item: (-item[1], item[0]))
                for char, count in sorted_errors:
                    errori = count
                    inviati = current_aggregates.get("aggregated_sent_chars_detail", {}).get(char, 0)
                    limite_inferiore = wilson_score_lower_bound(errori, inviati) * 100
                    limite_superiore = wilson_score_upper_bound(errori, inviati) * 100
                    f.write(
                        _('     <tr><td class="char-emphasis">\'{}\'</td><td>{} su {} inv.</td><td colspan="2" style="text-align:center;">[{:.1f}% - {:.1f}%]</td></tr>\n').format(
                            char.upper(), errori, inviati, limite_inferiore, limite_superiore
                        )
                    )
                f.write("  </tbody>\n</table>\n")
            if previous_aggregates and previous_aggregates.get("num_sessions_in_block", 0) > 0:
                f.write(_("<h2>Variazioni Dettaglio Errori per Carattere</h2>\n"))
                f.write(_('<p class="report-subtitle">Variazioni rispetto al blocco di {count} esercizi precedente</p>\n').format(count=previous_aggregates["num_sessions_in_block"]))
                f.write("<table>\n")
                f.write(
                    _(
                        "  <thead><tr><th>Carattere</th><th>Err. Att.</th><th>%Tot Att.</th><th>%Spec Att.</th><th>Err. Prec.</th><th>%Tot Prec.</th><th>%Spec Prec.</th><th>Δ% Tot. Caratt.</th><th>Δ% Caratt. Spec.</th></tr></thead>\n"
                    )
                )
                f.write("  <tbody>\n")
                all_error_chars_set = set(current_aggregates.get("aggregated_errors_detail", {}).keys()) | set(previous_aggregates.get("aggregated_errors_detail", {}).keys())
                if not all_error_chars_set:
                    f.write(_('    <tr><td colspan="9" style="text-align:center;">Nessun errore registrato in nessuno dei due blocchi di riferimento.</td></tr>\n'))
                else:
                    sorted_chars_for_variation = sorted(all_error_chars_set, key=lambda char_key: (-current_aggregates.get("aggregated_errors_detail", {}).get(char_key, 0), char_key))
                    for char_err in sorted_chars_for_variation:
                        curr_count = current_aggregates.get("aggregated_errors_detail", {}).get(char_err, 0)
                        total_chars_curr_block = current_aggregates.get("total_chars_sent_overall", 1)
                        curr_rate_vs_total_chars = curr_count / total_chars_curr_block * 100 if total_chars_curr_block > 0 else 0.0
                        curr_total_sent_of_this_char = current_aggregates.get("aggregated_sent_chars_detail", {}).get(char_err, 0)
                        curr_rate_vs_specific_char = curr_count / curr_total_sent_of_this_char * 100 if curr_total_sent_of_this_char > 0 else 0.0
                        prev_count = previous_aggregates.get("aggregated_errors_detail", {}).get(char_err, 0)
                        total_chars_prev_block = previous_aggregates.get("total_chars_sent_overall", 1)
                        prev_rate_vs_total_chars = prev_count / total_chars_prev_block * 100 if total_chars_prev_block > 0 else 0.0
                        prev_total_sent_of_this_char = previous_aggregates.get("aggregated_sent_chars_detail", {}).get(char_err, 0)
                        prev_rate_vs_specific_char = prev_count / prev_total_sent_of_this_char * 100 if prev_total_sent_of_this_char > 0 else 0.0
                        delta_rate_vs_total_chars = curr_rate_vs_total_chars - prev_rate_vs_total_chars
                        delta_rate_vs_specific_char = curr_rate_vs_specific_char - prev_rate_vs_specific_char
                        delta_total_class = get_delta_class(delta_rate_vs_total_chars, higher_is_better=False)
                        delta_specific_class = get_delta_class(delta_rate_vs_specific_char, higher_is_better=False)
                        f.write(
                            _(
                                '     <tr><td class="char-emphasis">\'{}\'</td><td>{curr_count}</td><td>{curr_rate_vs_total_chars:.2f}%</td><td>{curr_rate_vs_specific_char:.2f}% <span class="details-label">(su {curr_sent_count} inv.)</span></td><td>{prev_count}</td><td>{prev_rate_vs_total_chars:.2f}%</td><td>{prev_rate_vs_specific_char:.2f}% <span class="details-label">(su {prev_sent_count} inv.)</span></td><td class="{delta_total_class}">{delta_rate_vs_total_chars:+.2f} %</td><td class="{delta_specific_class}">{delta_rate_vs_specific_char:+.2f} %</td></tr>\n'
                            ).format(
                                char_err.upper(),
                                curr_count=curr_count,
                                curr_rate_vs_total_chars=curr_rate_vs_total_chars,
                                curr_rate_vs_specific_char=curr_rate_vs_specific_char,
                                curr_sent_count=curr_total_sent_of_this_char,
                                prev_count=prev_count,  # <-- PARAMETRO AGGIUNTO
                                prev_rate_vs_total_chars=prev_rate_vs_total_chars,
                                prev_rate_vs_specific_char=prev_rate_vs_specific_char,
                                prev_sent_count=prev_total_sent_of_this_char,
                                delta_total_class=delta_total_class,
                                delta_rate_vs_total_chars=delta_rate_vs_total_chars,
                                delta_specific_class=delta_specific_class,
                                delta_rate_vs_specific_char=delta_rate_vs_specific_char,
                            )
                        )
                        f.write("  </tbody>\n</table>\n")
            f.write("    </div>\n")
            f.write("</body>\n")
            f.write("</html>\n")
            print(_("Report storico salvato in: {filename}").format(filename=report_filename_full_path))
    except OSError as e:
        print(_("Errore durante il salvataggio del report storico {filename}: {e}").format(filename=report_filename_full_path, e=str(e)))
        return None
    except Exception:  # noqa: BLE001 -- rete di sicurezza sull'intera generazione del report
        print(_("Errore imprevisto durante la generazione del report. Seguono i dettagli."))
        traceback.print_exc()
        return None
    try:
        base_report_filename = os.path.splitext(report_filename_base)[0]
        graphic_report_filename_base = base_report_filename + ".svg"
        graphic_report_filename_full_path = os.path.join(USER_DATA_PATH, graphic_report_filename_base)
        crea_report_grafico(current_aggregates, previous_aggregates, g_value, x_value, num_sessions_in_current_report, graphic_report_filename_full_path, _, app_language)
        print(_("Report grafico salvato in: {filename}").format(filename=graphic_report_filename_full_path))
    except Exception as e:  # noqa: BLE001 -- matplotlib solleva di tutto
        # Il report grafico e' un accessorio: se salta, il report HTML e le
        # statistiche restano validi, quindi si segnala e si prosegue.
        print(_("Errore durante la generazione del report grafico: {errore}").format(errore=e))
    return current_aggregates


def controlla_aggiornamenti():
    """Cerca una versione nuova e, se c'e', ne mostra le novita' prima di chiedere."""
    from GBUtils import perform_update, update_checker

    api_url = "https://api.github.com/repos/GabrieleBattaglia/cwapu/releases/latest"
    print(_("Ricerca aggiornamenti in corso..."))
    has_update, new_ver, dl_url, note_release = update_checker(VERSION, api_url)
    if not has_update:
        print(_("Hai gia' l'ultima versione disponibile ({ver})!").format(ver=VERSION))
        return
    print(_("\nAggiornamento disponibile."))
    print(_("E' disponibile la nuova versione {new_ver}! (Attuale: {curr_ver})").format(new_ver=new_ver, curr_ver=VERSION))
    if note_release:
        print(_("Novita' di questa versione:"))
        print(note_release.strip())
    if not dl_url:
        print(_("I file di installazione non sono ancora pronti per il download.\n\tRiprova piu' tardi."))
        return
    if enter_escape(_("Desideri scaricare e installare l'aggiornamento ora? (INVIO per si', ESC per ignorare): ")):
        print(_("Download dell'aggiornamento in corso. Attendere prego..."))
        if perform_update(dl_url, "cwapu"):
            print(_("Aggiornamento pronto. Cwapu si chiudera' per l'installazione..."))
            sys.exit(0)
        else:
            print(_("Si e' verificato un errore durante la preparazione dell'aggiornamento."))


def apri_manuale():
    """Apre la guida in linea nel browser predefinito.

    La guida e' una pagina HTML con intestazioni vere, quindi si naviga per
    intestazioni con il lettore di schermo, e il browser puo' tradurla da
    solo per chi non legge l'italiano.
    """
    percorso = user_file_path(MANUALE_NAME)
    if not os.path.exists(percorso):
        print(_("Guida non trovata: manca il file {nome}.").format(nome=MANUALE_NAME))
        return
    if getattr(sys, "frozen", False):
        # Da eseguibile la guida sta nella cartella temporanea che PyInstaller
        # cancella all'uscita: se ne tiene una copia accanto al programma, cosi'
        # resta leggibile anche dopo aver chiuso cwapu.
        import shutil

        copia = os.path.join(USER_DATA_PATH, MANUALE_NAME)
        try:
            if not os.path.exists(copia):
                shutil.copyfile(percorso, copia)
            percorso = copia
        except OSError as e:
            print(_("Copia della guida non riuscita: {errore}").format(errore=e))
    import webbrowser

    print(_("Apro la guida nel browser: {percorso}").format(percorso=percorso))
    try:
        aperta = webbrowser.open(f"file:///{percorso.replace(os.sep, '/')}")
    except OSError as e:
        aperta = False
        print(_("Errore aprendo il browser: {errore}").format(errore=e))
    if not aperta:
        print(_("Non sono riuscita ad aprire il browser.\n\tPuoi aprire il file a mano dal percorso qui sopra."))


def mostra_statistiche_timeline():
    """Report testuale della timeline, una categoria alla volta."""
    # timeline si porta dietro pandas e numpy: si carica soltanto qui, cosi'
    # chi non apre le statistiche non ne paga l'attesa a ogni avvio.
    print(_("Preparo le statistiche, un momento..."))
    import timeline

    category_mapping = {"words": _("parole"), "chars": _("caratteri/misto"), "qrz": "QRZ"}
    for category_key, category_name_translated in category_mapping.items():
        log_sessioni = app_data[f"historical_rx_data_{category_key}"]["sessions_log"]
        if not log_sessioni:
            continue
        _clear_screen_ansi()
        print(_("Report Timeline per {category_name}").format(category_name=category_name_translated))
        report_con_header = timeline.genera_report_temporale_completo(log_sessioni, _, app_language)
        chiusura = _("Fine del report. Bye da CWAPU {version}").format(version=VERSION)
        report_finale = report_con_header + "\n" + chiusura + "\n"
        print(report_finale)
        salva = enter_escape(prompt=_("Invio per salvare, Esc per proseguire..."))
        if not salva:
            continue
        nome_file_report = f"CWapu_Timeline_Report_{category_key.capitalize()}.txt"
        percorso_file_report = os.path.join(USER_DATA_PATH, nome_file_report)
        try:
            with open(percorso_file_report, "w", encoding="utf-8") as f:
                f.write(report_finale)
            print(_("\nReport salvato con successo in: {}").format(percorso_file_report))
            time.sleep(1.5)
        except OSError as e:
            print(_("\nErrore durante il salvataggio del file: {}").format(e))
            time.sleep(2.0)


def main():
    """Avvio, menu principale e uscita ordinata."""
    global app_data
    global overall_speed, overall_pitch, overall_dashes, overall_spaces, overall_dots
    global overall_volume, overall_ms, overall_fs, overall_wave
    app_data = load_settings()
    app_data["app_info"]["launch_count"] = app_data.get("app_info", {}).get("launch_count", 0) + 1
    launch_count = app_data["app_info"]["launch_count"]
    overall_settings = app_data["overall_settings"]
    overall_speed = overall_settings.get("speed", 18)
    overall_pitch = overall_settings.get("pitch", 550)
    overall_dashes = overall_settings.get("dashes", 30)
    overall_spaces = overall_settings.get("spaces", 50)
    overall_dots = overall_settings.get("dots", 50)
    overall_volume = overall_settings.get("volume", 0.5)
    overall_ms = overall_settings.get("ms", 1)
    overall_fs = overall_settings.get("fs_index", 5)
    overall_wave = overall_settings.get("wave_index", 1)
    _clear_screen_ansi()
    print(
        _("\nCWAPU - VERSIONE: {version} DEL {data} DI GABRY - IZ4APU.\n\tUtilità per il tuo CW.\n\t\tLancio app: {count}. Scrivi 'm' per il menu.").format(
            version=VERSION, data=RELEASE_DATE, count=launch_count
        )
    )
    print(
        _("\tWPM: {overall_speed}, Hz: {overall_pitch}, Volume: {}\n\tL/S/P: {overall_dashes}/{overall_spaces}/{overall_dots}, Wave: {}, MS:\t{overall_ms}, FS: {}.").format(
            int(overall_volume * 100),
            WAVE_TYPES[overall_wave - 1],
            SAMPLE_RATES[overall_fs],
            overall_speed=overall_speed,
            overall_pitch=overall_pitch,
            overall_dashes=overall_dashes,
            overall_spaces=overall_spaces,
            overall_dots=overall_dots,
            overall_ms=overall_ms,
        )
    )
    if getattr(sys, "frozen", False):
        controlla_aggiornamenti()
    while True:
        k = menu(d=MNMAIN, show=False, keyslist=True, ntf=_("Non è un comando!"))
        _clear_screen_ansi()
        if k == "c":
            Count()
        elif k == "t":
            Txing()
        elif k == "r":
            Rxing()
        elif k == "k":
            KeyboardCW()
        elif k == "l":
            ltc = pyperclip.paste()
            if ltc:
                suona(StringCleaning(ltc))
            else:
                suona(_("vuoti"))
        elif k == "m":
            menu(d=MNMAIN, show_only=True)
        elif k == "w":
            CreateDictionary()
        elif k == "g":
            apri_manuale()
        elif k == "s":
            _clear_screen_ansi()
            mostra_statistiche_timeline()
        elif k == "q":
            break
    app_data["overall_settings"].update(
        {
            "speed": overall_speed,
            "pitch": overall_pitch,
            "dashes": overall_dashes,
            "spaces": overall_spaces,
            "dots": overall_dots,
            "volume": overall_volume,
            "ms": overall_ms,
            "fs_index": overall_fs,
            "wave_index": overall_wave,
        }
    )
    save_settings(app_data)
    print(_("hpe cuagn - 73 de IZ4APU - Gabe in Bologna, JN54pl."))
    suona("bk hpe cuagn - 73 de iz4apu tu e e", sync=True)
    _clear_screen_ansi()
    Donazione(lang=app_language)


if __name__ == "__main__":
    main()
