# CWAPUDEV - Utility per il CW, di Gabry, IZ4APU
# Data concepimento 21/12/2022.
# GitHub publishing on july 2nd, 2024.

import contextlib
import copy
import datetime as dt
import difflib
import io
import json
import os
import random
import re
import string
import sys
import time
import traceback

import pyperclip
from GBUtils import (
    Acusticator,
    CWzator,
    Donazione,
    cartella_applicazione,
    dgt,
    enter_escape,
    key,
    menu,
    percorso_risorsa,
    polipo,
)

import contest as ct
from grafico import crea_report_grafico
from wilson import wilson_score_lower_bound, wilson_score_upper_bound

# installazione percorsi relativi e i18n
APP_DIR = os.path.dirname(os.path.abspath(__file__))


def get_user_data_path():
    """Restituisce un percorso scrivibile per i dati utente.

    Da eseguibile PyInstaller e' la cartella dell'eseguibile, da sorgente e'
    la cartella dello script. Mai la directory di lavoro: lanciando cwapu da
    un'altra cartella si perderebbero impostazioni, archivio storico e diario.
    La logica sta in GBUtils, come tutte le utilita' condivise.
    """
    return cartella_applicazione()


USER_DATA_PATH = get_user_data_path()


def resource_path(relative_path):
    """
    Restituisce il percorso assoluto a una risorsa, funzionante sia in sviluppo
    che per un eseguibile compilato con PyInstaller (anche con la cartella _internal).
    La ricerca sta in GBUtils: prima dentro il pacchetto, poi accanto al
    programma, mai nella directory di lavoro del momento.
    """
    return percorso_risorsa(relative_path)


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
VERSION = "7.0.5"
RELEASE_DATE = "2026-09-24"
# Tetto unico della velocita' per tutta l'applicazione, uguale a quello che
# CWzator V10 accetta. Prima ce n'erano quattro diversi, e il piu' basso, 85,
# era quello che chi riceve veloce incontrava per primo.
WPM_MIN = 5
WPM_MAX = 120
# I limiti del tono, quelli che il comando .h accetta: valgono anche per
# Alt con le frecce nel contest, perche' il tono e' lo stesso.
PITCH_MIN = 200
PITCH_MAX = 2700
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

# Il diario non cresce all'infinito: oltre questo tetto le voci piu' vecchie
# se ne vanno, a voci intere. Deciso da Gabriele con la issue 14.
DIARIO_MAX_BYTE = 1_000_000
# Come finisce una voce, nelle due lingue e nelle versioni fino alla 5, che
# chiudevano con tre asterischi: si taglia solo dopo una di queste righe.
TERMINATORI_DIARIO = ("Fine del rapporto.", "End of report.", "***")


def taglia_diario(testo, massimo=DIARIO_MAX_BYTE):
    """Toglie dalla testa le voci piu' vecchie finche' il diario sta sotto il tetto.

    Restituisce la coppia (testo nuovo, voci tolte). Il taglio cade sempre
    dopo il terminatore di una voce, cosi' la prima voce che resta e'
    intera, e non tocca mai l'ultima voce, quella appena scritta. Si scende
    un dieci per cento sotto il tetto, cosi' il taglio non si ripete a ogni
    esercizio. Con meno di due voci delimitate non si taglia niente:
    meglio un diario sopra il tetto che uno spezzato a meta' voce.
    """
    righe = testo.splitlines(keepends=True)
    byte_totali = sum(len(riga.encode("utf-8")) for riga in righe)
    if byte_totali <= massimo:
        return testo, 0
    terminatori = [indice for indice, riga in enumerate(righe) if riga.strip() in TERMINATORI_DIARIO]
    if len(terminatori) < 2:
        return testo, 0
    # L'ultimo terminatore chiude la voce appena scritta: non e' un punto di
    # taglio, altrimenti un diario con la sola voce nuova delimitata si
    # svuoterebbe per intero, voce nuova compresa.
    candidati = terminatori[:-1]
    da_togliere = byte_totali - int(massimo * 0.9)
    tolti = 0
    taglio = None
    voci = 0
    prossimo = 0
    for indice, riga in enumerate(righe):
        tolti += len(riga.encode("utf-8"))
        if prossimo < len(candidati) and indice == candidati[prossimo]:
            prossimo += 1
            voci = prossimo
            if tolti >= da_togliere:
                taglio = indice + 1
                break
    if taglio is None:
        # Nessun taglio ammesso raggiunge la soglia: si toglie tutto il
        # possibile, cioe' fino al penultimo terminatore.
        taglio = candidati[-1] + 1
        voci = len(candidati)
    while taglio < len(righe) and not righe[taglio].strip():
        taglio += 1
    return "".join(righe[taglio:]), voci


def scrivi_diario(testo):
    """Accoda una voce al diario e lo tiene sotto il tetto, dicendolo in una riga.

    Solleva OSError come farebbe open, cosi' chi chiama continua a dire se
    il rapporto e' stato salvato oppure no. Restituisce quante voci vecchie
    ha tolto, di solito zero.
    """
    with open(DIARY_FILE, "a", encoding="utf-8") as f:
        f.write(testo)
    if os.path.getsize(DIARY_FILE) <= DIARIO_MAX_BYTE:
        return 0
    # errors="replace": il manuale invita ad aprire il diario con qualunque
    # editor, e un editor che salva in ANSI lascia byte che non sono UTF-8.
    # Farebbero cadere il programma a fine esercizio; cosi' diventano il
    # carattere di sostituzione e il file riscritto torna UTF-8 valido.
    with open(DIARY_FILE, encoding="utf-8", errors="replace", newline="") as f:
        intero = f.read()
    nuovo, voci = taglia_diario(intero, DIARIO_MAX_BYTE)
    if nuovo == intero:
        return 0
    # Si scrive un file di appoggio e lo si scambia con il diario in un colpo
    # solo: un guasto a meta' lascia il diario com'era, voce nuova compresa,
    # invece di lasciarlo vuoto come farebbe una riscrittura sul posto.
    appoggio = DIARY_FILE + ".tmp"
    with open(appoggio, "w", encoding="utf-8", newline="") as f:
        f.write(nuovo)
    try:
        os.replace(appoggio, DIARY_FILE)
    except OSError:
        with contextlib.suppress(OSError):
            os.remove(appoggio)
        raise
    print(_("Diario: tolte {voci} voci vecchie, ora {kb} KB.").format(voci=voci, kb=os.path.getsize(DIARY_FILE) // 1024))
    return voci


@contextlib.contextmanager
def apri_diario():
    """Il posto unico da cui il diario si scrive.

    Si usa come open in aggiunta: cio' che si scrive nel blocco finisce nel
    diario alla chiusura, in un colpo solo, e poi il file si tiene sotto il
    tetto. Se il blocco solleva, non si scrive niente.
    """
    buffer = io.StringIO()
    yield buffer
    scrivi_diario(buffer.getvalue())


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
# Il pannello del contest: gli stati e i valori con cui si gioca, con i
# predefiniti presi da cwsim dove cwsim li ha. Chi legge le impostazioni
# completa con questi le chiavi che mancano, cosi' un file vecchio non rompe
# niente.
CONTEST_PREDEFINITI = {
    "qrn": False,
    "qrm": False,
    "qrm_massime": 1,
    "qsb": False,
    "flutter": False,
    "sbadati": True,
    "pileup": False,
    "attivita": 4,
    "stereo": 100,
    "banda": 500,
    "tasto_verticale": True,
    "tasto_probabilita": 30,
    "tasto_l_min": 30,
    "tasto_l_max": 60,
    "tasto_s_min": 25,
    "tasto_s_max": 75,
    "tasto_p_min": 15,
    "tasto_p_max": 50,
    "scambio_veloce": False,
    "scambio_probabilita": 30,
    "scambio_incremento": 20,
}
CONTEST_VOCI = [
    {
        "id": "0",
        "key_state": "scambio_veloce",
        "etichetta": _("5NN accelerato"),
        "chiedi_stati": lambda stati: chiedi_scambio_veloce(stati),
        # Il simbolo di percentuale non va mai seguito da spazio e da una
        # lettera come d o o: Babel scambierebbe la frase per un formato
        # Python e la compilazione dei cataloghi potrebbe fallire.
        "descrivi": lambda stati: _("stazioni {p}%, +{d}%").format(p=stati["scambio_probabilita"], d=stati["scambio_incremento"]),
    },
    {"id": "1", "key_state": "qrn", "etichetta": _("QRN")},
    {
        "id": "2",
        "key_state": "qrm",
        "etichetta": _("QRM"),
        "valore": "qrm_massime",
        "chiedi": lambda salvato: chiedi_intero(_("Stazioni di disturbo insieme"), 1, 5, salvato),
        "descrivi": lambda stati: _("{n} stazioni").format(n=stati["qrm_massime"]),
    },
    {"id": "3", "key_state": "qsb", "etichetta": _("QSB")},
    {"id": "4", "key_state": "flutter", "etichetta": _("flutter")},
    {"id": "5", "key_state": "sbadati", "etichetta": _("operatori sbadati")},
    {
        "id": "6",
        "key_state": "pileup",
        "etichetta": _("pile-up"),
        "valore": "attivita",
        "chiedi": lambda salvato: chiedi_intero(_("Attività, stazioni per chiamata"), 1, 9, salvato),
        "descrivi": lambda stati: _("attività {n}").format(n=stati["attivita"]),
    },
    {
        "id": "7",
        "etichetta": _("stereo"),
        "valore": "stereo",
        "chiedi": lambda salvato: chiedi_intero(_("Larghezza stereo"), 0, 100, salvato),
        "descrivi": lambda stati: _("{n} su 100").format(n=stati["stereo"]),
    },
    {
        "id": "8",
        "etichetta": _("banda"),
        "valore": "banda",
        "chiedi": lambda salvato: arrotonda_banda(chiedi_intero(_("Banda in hertz, a passi di 50"), CONTEST_BANDA_MIN, CONTEST_BANDA_MAX, salvato)),
        "descrivi": lambda stati: _("{n} hertz").format(n=stati["banda"]),
    },
    {
        "id": "9",
        "key_state": "tasto_verticale",
        "etichetta": _("tasto verticale"),
        "descrivi": lambda stati: _("{p}%, L {l0}-{l1}, S {s0}-{s1}, P {p0}-{p1}").format(
            p=stati["tasto_probabilita"],
            l0=stati["tasto_l_min"],
            l1=stati["tasto_l_max"],
            s0=stati["tasto_s_min"],
            s1=stati["tasto_s_max"],
            p0=stati["tasto_p_min"],
            p1=stati["tasto_p_max"],
        ),
    },
]
def chiedi_scambio_veloce(stati):
    """Le due domande del 5NN accelerato: quante stazioni lo fanno e di quanto.

    Nei contest il rapporto e' l'unico gruppo che tutti si aspettano, quindi
    molti operatori lo mandano piu' veloce del resto e rallentano sul numero,
    che e' il dato vero da copiare. La voce del pannello e' una sola, con il
    suo interruttore come tutte le altre, ma i valori sono due e si chiedono
    insieme quando la si accende. Il minimo e' uno: zero vorrebbe dire accesa
    e senza effetto, che a chi legge la riga non direbbe niente.

    Le due risposte si scrivono negli stati del pannello, entrambe. La
    seconda andava direttamente nelle impostazioni salvate, e il pannello,
    che lavora su una copia, alla conferma ci ricopiava sopra la sua: il
    valore chiesto non arrivava ne' alla partita ne' al file, e restava
    quello di prima.
    """
    stati["scambio_probabilita"] = chiedi_intero(
        _("Stazioni che accelerano il 5NN, in percentuale"), 1, 100, max(1, stati.get("scambio_probabilita") or CONTEST_PREDEFINITI["scambio_probabilita"])
    )
    stati["scambio_incremento"] = chiedi_intero(
        _("Di quanto accelerano il 5NN, in percentuale"), 5, 50, stati.get("scambio_incremento", CONTEST_PREDEFINITI["scambio_incremento"])
    )


def chiedi_intero(domanda, minimo, massimo, proposto):
    """Una domanda del contest: cosa si chiede, fra che limiti, e cosa l'Invio conferma.

    Il valore fra quadre e' quello salvato, che un Invio a vuoto conferma; i
    due limiti dicono cosa si puo' scrivere senza doverlo indovinare. Sono una
    richiesta di Gabriele del 21 settembre 2026, e valgono per ogni domanda
    del contest.
    """
    proposto = max(minimo, min(massimo, int(proposto)))
    prompt = _("{domanda}, da {minimo} a {massimo} [{proposto}]: ").format(domanda=domanda, minimo=minimo, massimo=massimo, proposto=proposto)
    return dgt(prompt=prompt, kind="i", imin=minimo, imax=massimo, default=proposto)


def arrotonda_banda(valore):
    """La banda al passo di cinquanta piu' vicino, con il mezzo che sale.

    round di Python arrotonda il mezzo al pari: 325 diviso 50 fa 6,5 e
    diventa 6, cioe' 300, mentre 375 diventa 400. Due valori a mezza via
    che si comportano in modo opposto non si spiegano a chi li scrive.
    """
    passo = CONTEST_PASSO_BANDA
    return max(CONTEST_BANDA_MIN, min(CONTEST_BANDA_MAX, int((int(valore) + passo // 2) // passo * passo)))


def fronte_stereo(primo, secondo, ampiezza):
    """Due rumori indipendenti diventano un fronte largo quanto l'ampiezza chiede.

    A zero i due canali sono identici e il suono sta al centro; a cento sono
    scorrelati e riempie la scena. Serve perche' il rumore di fondo di una
    radio non viene da un punto: viene da tutte le parti, e allargarlo e' il
    modo di dirlo. Uno score lo sintetizza con i due canali identici, quindi
    il fronte si costruisce qui da due sintesi diverse.
    La miscela tiene la potenza costante, perche' il fondo non deve cambiare
    livello mentre si allarga: i quadrati dei due pesi sommano a uno.
    """
    import numpy as np

    larghezza = max(0.0, min(1.0, float(ampiezza) / 100.0))
    sinistra = np.asarray(primo, dtype=np.float32)[:, 0]
    destra = np.asarray(secondo, dtype=np.float32)[: len(sinistra), 0]
    miscelato = (1.0 - larghezza**2) ** 0.5 * sinistra[: len(destra)] + larghezza * destra
    return np.stack([sinistra[: len(destra)], miscelato], axis=1).astype(np.float32)


def effetti_non_disponibili():
    """Gli effetti radio che la GBUtils installata non sa ancora fare.

    QSB e flutter vogliono il parametro qsb di CWzator, il fondo di QRN vuole
    Acusticator.ciclo: sono arrivati insieme con la V165. Con una GBUtils piu'
    vecchia gli interruttori restano, e dicono che non e' ancora il momento,
    invece di far fallire il contest a meta'.
    """
    import inspect

    mancanti = []
    if not hasattr(Acusticator, "ciclo"):
        mancanti.append("qrn")
    try:
        parametri = inspect.signature(CWzator).parameters
        if "qsb" not in parametri:
            mancanti.extend(("qsb", "flutter"))
        elif "chirp" not in parametri:
            # Il flutter porta con se' i difetti di nota, che sono arrivati
            # con la V167: senza di quelli l'interruttore prometterebbe piu'
            # di quello che sa fare.
            mancanti.append("flutter")
    except (TypeError, ValueError):  # pragma: no cover - una firma illeggibile e' un caso che non si e' mai visto
        mancanti.extend(("qsb", "flutter"))
    return tuple(mancanti)


CONTEST_NON_DISPONIBILI = effetti_non_disponibili()
# Il fondo di rumore: dieci secondi sintetizzati una volta sola e tenuti in
# ciclo sotto le stazioni, limitati alla banda del filtro del ricevitore.
CONTEST_FONDO_SECONDI = 10.0
CONTEST_FONDO_VOLUME = 0.5
# Il fondo non ha dissolvenze ai capi: a chiuderlo su se' stesso ci pensa
# Acusticator, che dalla V166 taglia i due transitori e incrocia la testa
# con la coda.
CONTEST_FONDO_ADSR = [0, 0, 100, 0]
# Quanto la mano deve stare ferma prima che il valore cambiato venga detto.
# Annunciarlo a ogni pressione riempie la voce di numeri che scorrono e non
# si ascoltano: e' il rilievo di Gabriele del 21 settembre 2026.
CONTEST_ATTESA_ANNUNCIO = 2.0
# Le due durate proposte quando si sceglie come finire il contest.
CONTEST_QSO_PREDEFINITI = 50
CONTEST_MINUTI_PREDEFINITI = 10
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
    "overall_settings": {
        "app_language": "en",
        "speed": 18,
        "pitch": 550,
        "dashes": 30,
        "spaces": 50,
        "dots": 50,
        "volume": 0.5,
        "ms": 1,
        "fs_index": 5,
        "wave_index": 1,
        "farnsworth": 0,
        "uscita_interfaccia": "",
        "uscita_dispositivo": "",
        "contest_call": "",
    },
    "rxing_stats_words": {"total_calls": 0, "sessions": 0, "total_correct": 0, "total_wrong_items": 0, "total_time_seconds": 0.0},
    "rxing_stats_chars": {"total_calls": 0, "sessions": 0, "total_correct": 0, "total_wrong_items": 0, "total_time_seconds": 0.0},
    "rxing_stats_qrz": {"total_calls": 0, "sessions": 0, "total_correct": 0, "total_wrong_items": 0, "total_time_seconds": 0.0},
    "rxing_stats_contest": {"total_calls": 0, "sessions": 0, "total_correct": 0, "total_wrong_items": 0, "total_time_seconds": 0.0},
    "counting_stats": {"exercise_number": 1},
    "contest_settings": dict(CONTEST_PREDEFINITI),
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
    "historical_rx_data_contest": {"chars_since_last_report": 0, "sessions_log": [], "historical_reports": []},
}
# Le categorie dell'archivio storico, ciascuna con statistiche, registro e
# rapporti suoi. Il contest ha la sua dalla 7.0.5, issue 15: fino ad allora
# scriveva nelle chiavi del QRZ, dove un item e' un nominativo mandato,
# mentre per lui e' un QSO messo a log, e le due serie si mescolavano.
CATEGORIE_ARCHIVIO = ("words", "chars", "qrz", "contest")


def nome_categoria(category_key):
    """Il nome di una categoria dell'archivio come lo legge l'utente."""
    nomi = {"words": _("parole"), "chars": _("caratteri/misto"), "qrz": "QRZ", "contest": _("contest")}
    return nomi.get(category_key, category_key)
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


COMANDO_NUMERICO = re.compile(r"([a-zA-Z])\s*(\d+)")


def comando_numerico(testo):
    """Legge un comando della sezione tastiera fatto di lettera e numero.

    Accetta il numero attaccato alla lettera e anche dopo uno spazio: w25 e
    w 25 sono lo stesso comando. Fino alla 6.0.5 la seconda forma non era
    riconosciuta e il testo finiva trasmesso in CW, cosi' ".m 50" si sentiva
    come "m 50" e sembrava un feedback, mentre non era cambiato niente.
    Restituisce la coppia (lettera minuscola, valore), oppure None quando il
    testo non ha quella forma, per esempio "t 3-7" oppure "sv ciao".
    """
    letto = COMANDO_NUMERICO.fullmatch(testo.strip())
    if letto is None:
        return None
    return letto.group(1).lower(), int(letto.group(2))


def rampa_massima_ms(wpm, peso_punto=50):
    """Quanto puo' durare davvero la dissolvenza a questa velocita'.

    CWzator accorcia ogni rampa a meta' dell'elemento, e il punto e'
    l'elemento piu' corto: 1200 diviso wpm millesimi, scalati dal peso.
    Oltre questo valore, .m non cambia piu' niente sul punto.
    """
    return 600.0 / wpm * peso_punto / 50.0


def limita_farnsworth(valore, wpm):
    """Il Farnsworth che si puo' davvero impostare.

    Zero o meno spegne. Altrimenti sta fra il minimo del motore e la
    velocita' dei caratteri, perche' il Farnsworth allarga le spaziature e
    quindi la velocita' effettiva sta sotto a quella dei caratteri, mai sopra.
    """
    if valore <= 0:
        return 0
    return max(WPM_MIN, min(int(wpm), int(valore)))


def pavimento_velocita(farnsworth):
    """Sotto quale velocita' dei caratteri la velocita' variabile non scende.

    Con il Farnsworth impostato e' il Farnsworth stesso: deciso da Gabriele
    il 2026-09-17, il Farnsworth resta fermo mentre i caratteri salgono e
    scendono, e i caratteri non gli passano mai sotto.
    """
    return max(WPM_MIN, int(farnsworth or 0))


def farnsworth_impostato():
    """Vero quando in k c'e' un Farnsworth: gli esercizi si fanno, ma non lasciano tracce su disco."""
    return bool(overall_farnsworth)


def pavimento_ammesso(farnsworth, wpm, l, s, p):
    """La velocita' dei caratteri piu' bassa a cui questo Farnsworth e' ancora ammesso.

    Con i pesi standard e' il Farnsworth stesso; con spazi larghi sta piu' in
    alto, perche' il tetto che i pesi impongono scende con la velocita': con
    s a 75, un Farnsworth di 15 regge a 20 wpm e non a 19. Si interroga il
    motore a vuoto da pavimento_velocita in su, fino a wpm: la seconda
    revisione del 2026-09-17 ha misurato 116 prove in cinque millesimi.
    """
    base = pavimento_velocita(farnsworth)
    if not farnsworth:
        return base
    velocita = base
    while velocita < int(wpm) and not farnsworth_ammesso(farnsworth, velocita, l, s, p):
        velocita += 1
    return velocita


def farnsworth_ammesso(farnsworth, wpm, l, s, p):
    """Vero se il motore accetta questo Farnsworth con questi pesi.

    Prova a vuoto, senza suonare: il limite che i pesi impongono si calcola
    sulla parola campione e non dipende dal messaggio, quindi bastano due
    lettere.
    """
    prova, _rwpm = CWzator(msg="ee", wpm=limita_wpm(wpm), l=l, s=s, p=p, farnsworth=farnsworth, play=False)
    return prova is not None


def allinea_farnsworth():
    """Tiene il Farnsworth dentro cio' che velocita' e pesi consentono, e lo dice.

    Il Farnsworth non supera la velocita' dei caratteri e non chiede
    spaziature piu' strette dei pesi: quando un comando cambia velocita' o
    pesi, il Farnsworth scende fino al massimo ammesso, e a zero se non ne
    esiste uno. Va chiamata dopo ogni cambiamento di velocita' o di pesi,
    e all'avvio, perche' la coppia salvata potrebbe essere nata incoerente.
    L'ha chiesto la revisione del 2026-09-17, che aveva trovato tre strade
    per portare i caratteri sotto il Farnsworth: a quel punto il motore
    rifiutava ogni messaggio e l'esercizio, trasmesso a CW standard, non
    veniva nemmeno salvato. Restituisce il valore nuovo, o None se non ha
    toccato niente.
    """
    global overall_farnsworth
    if not overall_farnsworth:
        return None
    nuovo = min(int(overall_farnsworth), int(overall_speed))
    while nuovo >= WPM_MIN and not farnsworth_ammesso(nuovo, overall_speed, overall_dashes, overall_spaces, overall_dots):
        nuovo -= 1
    if nuovo < WPM_MIN:
        nuovo = 0
    if nuovo == overall_farnsworth:
        return None
    overall_farnsworth = nuovo
    if nuovo == 0:
        print(_("FW spento: con questi pesi nessuna velocità effettiva è raggiungibile."))
    elif nuovo == overall_speed:
        print(_("FW portato a {fw}, la velocità dei caratteri.").format(fw=nuovo))
    else:
        print(_("FW portato a {fw}, il massimo che questi pesi consentono.").format(fw=nuovo))
    return nuovo


def valore_comando_fw(msg):
    """Il numero di un comando .fw, oppure None se il comando e' malformato.

    Accetta le maiuscole e lo spazio, come gli altri comandi numerici. Usa
    isdecimal e non isdigit: isdigit accetta anche apici e cifre cerchiate,
    che int rifiuta, e un ValueError qui farebbe cadere l'applicazione
    senza salvare le impostazioni.
    """
    resto = msg.strip()[3:].strip()
    if not resto or not resto.isdecimal():
        return None
    return int(resto)


def descrivi_uscita(voce):
    """La riga di menu di un dispositivo di uscita, tutta a parole.

    Interfaccia, nome, latenza e frequenza, e poi cio' che conta per
    scegliere: se porta alla scheda su cui si sta gia' ascoltando, che e'
    il dato da mostrare, se e' il predefinito di sistema, che di solito e'
    la via lenta alla stessa scheda, se prende il dispositivo in esclusiva,
    e se non si apre, con il motivo.
    """
    # Il nome si ripulisce solo qui, per la lettura: certi driver Bluetooth
    # ci mettono dentro un ritorno a capo vero, che spezzerebbe la riga in
    # due e con lo screen reader farebbe sembrare la coda una voce orfana.
    # Per il confronto e per il salvataggio il nome resta quello grezzo.
    nome = " ".join(str(voce["dispositivo"]).split())
    parti = [f"{voce['breve']}, {nome}, {voce['latenza']:.0f} ms, {voce['frequenza']:.0f} Hz"]
    if voce.get("stessa_scheda"):
        parti.append(_("stessa scheda di adesso"))
    if voce.get("predefinito"):
        parti.append(_("predefinito di sistema"))
    if voce.get("esclusiva"):
        # Con una scheda sola, l'esclusiva zittisce anche il lettore di
        # schermo per tutto il tempo in cui il mixer tiene aperta la scheda.
        parti.append(_("esclusiva, zittirebbe NVDA e gli altri programmi"))
    if voce.get("apribile") is False:
        parti.append(_("non si apre: {motivo}").format(motivo=voce.get("motivo") or "?"))
    return ", ".join(parti)


def ordina_uscite(elenco):
    """Prima le uscite che si aprono, nell'ordine di GBUtils; in fondo quelle che non si aprono.

    Non si nascondono: un elenco che tace su una scelta che il sistema
    offre lascia l'utente a chiedersi dove sia finita. Si segnano, con il
    motivo, e stanno in coda.
    """
    return [v for v in elenco if v.get("apribile") is not False] + [v for v in elenco if v.get("apribile") is False]


def risolvi_uscita_audio(interfaccia, dispositivo, elenco=None):
    """L'indice di oggi dell'uscita salvata, o None se non c'e' o se la scelta e' automatica.

    Si salva la coppia interfaccia e nome, non l'indice: gli indici cambiano
    quando si attacca o si stacca una periferica, i nomi no. Se la coppia
    salvata oggi non c'e', per esempio una scheda USB staccata, si torna
    alla scelta automatica per questa volta e la coppia resta salvata per
    quando tornera'.
    """
    if not interfaccia or not dispositivo:
        return None
    if elenco is None:
        elenco = CWzator.elenco_dispositivi(prova="nessuno")
    for voce in elenco:
        if voce["breve"] == interfaccia and voce["dispositivo"] == dispositivo:
            return voce["indice"]
    return None


def descrizione_uscita(interfaccia, dispositivo):
    """Come l'uscita si legge nei riepiloghi: automatica, oppure interfaccia e nome."""
    if not interfaccia:
        return _("automatica")
    return f"{interfaccia}, {' '.join(str(dispositivo).split())}"


def uscita_automatica(elenco=None):
    """Interfaccia e nome del dispositivo che CWzator sceglie da se', o (None, None).

    Si legge dalla cache di CWzator, che dalla seconda volta non costa
    niente, e si cerca nell'elenco dei dispositivi per dare all'utente il
    nome e non un numero. (None, None) quando CWzator lascia fare al
    sistema, per esempio fuori da Windows.
    """
    try:
        indice, _nome_api = CWzator.scegli_dispositivo()
    except Exception:  # noqa: BLE001 -- senza una scelta si dice "automatica" e basta
        return None, None
    if indice is None:
        return None, None
    if elenco is None:
        elenco = CWzator.elenco_dispositivi(prova="nessuno")
    for voce in elenco:
        if voce["indice"] == indice:
            return voce["breve"], voce["dispositivo"]
    return None, None


def descrizione_uscita_corrente(elenco=None):
    """L'uscita su cui si suona adesso, a parole.

    Quella scelta con .o se oggi c'e'; altrimenti la scelta automatica,
    con il dispositivo che CWzator ha scelto quando lo sa. Cosi' chi legge
    "automatica" sa anche dove sta andando il suono.
    """
    if overall_uscita_interfaccia and overall_api is not None:
        return descrizione_uscita(overall_uscita_interfaccia, overall_uscita_dispositivo)
    interfaccia, dispositivo = uscita_automatica(elenco)
    if not interfaccia:
        return _("automatica")
    return _("automatica: {uscita}").format(uscita=descrizione_uscita(interfaccia, dispositivo))


def scegli_uscita_audio(elenco=None, chiedi=None, automatica=None):
    """Il comando .o: elenca le uscite e ne fa scegliere una, o lascia scegliere a CWapu.

    Restituisce la coppia scelta (interfaccia, dispositivo), vuota per la
    scelta automatica, oppure None se non e' cambiato niente. L'elenco si
    costruisce provando ad aprire ogni dispositivo, perche' cio' che il
    sistema dichiara e cio' che si apre davvero non coincidono: sulla
    macchina di sviluppo sei dispositivi su ventuno non si aprono. Costa
    un quarto di secondo, una volta sola.
    elenco, chiedi e automatica servono alle prove, che passano un elenco
    finto, una domanda che risponde da sola e l'indice della scelta
    automatica; di serie l'indice lo dice CWzator.
    """
    global overall_uscita_interfaccia, overall_uscita_dispositivo, overall_api
    if elenco is None:
        print(_("Provo ad aprire ogni uscita, un attimo..."))
        elenco = CWzator.elenco_dispositivi(prova="tutti")
    voci = ordina_uscite(elenco)
    if not voci:
        print(_("Nessuna uscita audio trovata."))
        return None
    if automatica is None:
        try:
            automatica, _nome_api = CWzator.scegli_dispositivo()
        except Exception:  # noqa: BLE001 -- senza la scelta automatica l'elenco resta buono, solo senza il segno
            automatica = None
    # La coppia salvata conta come scelta solo se oggi c'e': altrimenti si
    # sta suonando in automatico, e l'elenco deve dirlo.
    scelta_esplicita = bool(overall_uscita_interfaccia) and overall_api is not None
    predefinito = 0
    for numero, voce in enumerate(voci, start=1):
        e_quella_scelta = scelta_esplicita and voce["breve"] == overall_uscita_interfaccia and voce["dispositivo"] == overall_uscita_dispositivo
        if e_quella_scelta:
            predefinito = numero
        coda = ""
        if e_quella_scelta:
            coda = _(", scelta adesso")
        elif not scelta_esplicita and automatica is not None and voce["indice"] == automatica:
            coda = _(", quella che CWapu sceglie adesso")
        print(f"{numero}. {descrivi_uscita(voce)}{coda}")
    if overall_uscita_interfaccia and overall_api is None:
        print(_("L'uscita salvata, {uscita}, oggi non c'è: si sta suonando in automatico.").format(uscita=descrizione_uscita(overall_uscita_interfaccia, overall_uscita_dispositivo)))
    print(_("0. Lascia scegliere a CWapu"))
    if chiedi is None:
        chiedi = dgt
    numero = chiedi(prompt=_("Numero da 0 a {massimo}, Invio per {predefinito}> ").format(massimo=len(voci), predefinito=predefinito), kind="i", imin=0, imax=len(voci), default=predefinito)
    if numero == 0:
        # Lo zero e' "niente da cambiare" solo se la scelta e' gia' automatica
        # per scelta: con una coppia salvata ma assente oggi, lo zero la
        # cancella davvero, altrimenti l'avviso tornerebbe a ogni avvio.
        if not overall_uscita_interfaccia:
            return None
        overall_uscita_interfaccia, overall_uscita_dispositivo, overall_api = "", "", None
        return ("", "")
    if numero == predefinito:
        return None
    voce = voci[numero - 1]
    overall_uscita_interfaccia, overall_uscita_dispositivo, overall_api = voce["breve"], voce["dispositivo"], voce["indice"]
    return (voce["breve"], voce["dispositivo"])


def suona(msg, wpm=None, pitch=None, l=None, s=None, p=None, sync=False, to_file=False, avvisa=True, farnsworth=None, pan=0, vol=None, qsb=None, chirp=None, vibrato=None, ritardo=None):
    """Manda un messaggio al motore CW con le impostazioni correnti dell'utente.

    Raccoglie i dieci parametri che ogni chiamata ripeteva identici e lascia
    al chiamante soltanto cio' che cambia davvero. Restituisce la coppia
    (handle, velocita' effettiva) di CWzator. Quando la libreria rifiuta il
    messaggio restituisce (None, 0.0) e lo dice: prima si proseguiva in
    silenzio e l'utente restava senza suono senza sapere perche'.
    farnsworth: None prende il valore impostato nella sezione k; zero lo
    spegne per questo messaggio, ed e' cio' che fa il contest, dove per
    decisione presa il Farnsworth non esiste. Se il motore rifiuta il
    Farnsworth, perche' i pesi degli spazi non consentono la velocita'
    effettiva chiesta, lo si dice con le parole del motore, che spiegano
    fin dove si puo' arrivare, e si trasmette senza.
    pan: da meno cento a piu' cento, la posizione fra gli altoparlanti; zero
    e' il centro, ed e' cio' che CWapu ha sempre fatto. vol: la forza di
    questo messaggio da zero a uno; None prende il volume generale. Servono al
    pile-up, dove ogni stazione arriva da una sua posizione e con una sua
    forza, e non cambiano niente per chi non li passa.
    qsb: la banda in hertz dell'evanescenza, cioe' il segnale che va e viene;
    chirp: lo scarto in hertz con cui il tono scivola dentro ogni elemento;
    vibrato: la profondita' e la frequenza con cui il tono oscilla. None non
    ne mette. Si passano al motore soltanto quando ci sono, cosi' con una
    GBUtils che non li conosce tutto il resto continua a funzionare.
    """
    effettiva = overall_farnsworth if farnsworth is None else farnsworth
    parametri = {
        "msg": msg,
        "wpm": limita_wpm(overall_speed if wpm is None else wpm),
        "pitch": overall_pitch if pitch is None else pitch,
        "l": overall_dashes if l is None else l,
        "s": overall_spaces if s is None else s,
        "p": overall_dots if p is None else p,
        "vol": overall_volume if vol is None else max(0.0, min(1.0, float(vol))) * overall_volume,
        "pan": max(-100.0, min(100.0, float(pan))),
        "ms": overall_ms,
        "fs": SAMPLE_RATES[overall_fs],
        "wv": overall_wave,
        "sync": sync,
        "to_file": to_file,
        "farnsworth": effettiva or None,
        "api": overall_api,
    }
    for nome, valore in (("qsb", qsb), ("chirp", chirp), ("vibrato", vibrato)):
        if valore is not None:
            parametri[nome] = valore
    if ritardo:
        # Il silenzio davanti al messaggio, in secondi: il trattino basso e'
        # il segnaposto che CWzator riempie con la pausa chiesta, esatta al
        # millesimo e indipendente dalla velocita'. Serve a far partire un
        # pezzo nell'istante giusto senza aspettare che il precedente
        # finisca, cioe' a rimettere insieme un messaggio spezzato.
        parametri["msg"] = "_ " + parametri["msg"]
        parametri["pausa"] = float(ritardo) * 1000.0
    handle, rwpm = CWzator(**parametri)
    errore = getattr(CWzator, "ultimo_errore", None)
    if handle is None and effettiva and "farnsworth" in str(errore).lower():
        # Solo un rifiuto che riguarda davvero il Farnsworth giustifica il
        # secondo tentativo: per ogni altro errore riprovare senza sarebbe
        # inutile e attribuirebbe al Farnsworth una colpa non sua.
        if avvisa:
            print(_("Farnsworth non applicato: {errore}").format(errore=errore))
        parametri["farnsworth"] = None
        handle, rwpm = CWzator(**parametri)
    if handle is None:
        if avvisa:
            print(_("Il motore CW non ha trasmesso il messaggio: {errore}").format(errore=getattr(CWzator, "ultimo_errore", None)))
        return None, 0.0
    if getattr(handle, "errore", None) and not (to_file and getattr(handle, "file_salvato", None) is None):
        # Il motore ha accettato il messaggio ma il mixer non l'ha suonato,
        # per esempio perche' l'uscita scelta con .o non si apre. Con
        # to_file lo stesso attributo porta anche un WAV non scritto mentre
        # il CW e' gia' uscito: quello lo dice gia' chi ha chiesto il file.
        if avvisa:
            print(_("Il motore CW non ha trasmesso il messaggio: {errore}").format(errore=handle.errore))
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


def riga_interruttore(voce, stati):
    """La riga di una voce del pannello: numero, nome, indicatore, stato e valore.

    Ogni riga resta una frase, perche' lo screen reader la legge di seguito:
    "2. QRM <X> ATTIVATO, 2 stazioni". Le voci che sono solo un valore, come
    lo stereo e la banda, non hanno indicatore ne' stato: hanno il valore.
    """
    chiave = voce.get("key_state")
    acceso = bool(stati.get(chiave)) if chiave else True
    if chiave:
        # Il nome in maiuscolo quando e' acceso, in minuscolo quando e' spento:
        # lo stato si sente anche dal nome, non solo dall'indicatore.
        etichetta = voce["etichetta"].upper() if acceso else voce["etichetta"].lower()
        marcatore = "<X>" if acceso else "< >"
        riga = "{}. {} {} {}".format(voce["id"], etichetta, marcatore, _("ATTIVATO") if acceso else _("disattivato"))
    else:
        # Le voci che sono solo un valore non si accendono: il nome resta com'e'.
        riga = "{}. {}".format(voce["id"], voce["etichetta"])
    if voce.get("descrivi") and acceso:
        riga += ", " + voce["descrivi"](stati)
    return riga


def pannello_interruttori(voci, stati, titolo, al_cambio=None, alla_conferma=None):
    """Il pannello a interruttori, quello degli esercizi Rx, usato anche dal contest.

    voci: l'elenco delle voci. Ognuna porta id, il numero che la accende;
      etichetta, cio' che si legge; key_state, la chiave dello stato, che le
      voci di solo valore non hanno; e, dove c'e' un valore, valore con la sua
      chiave, chiedi per domandarlo e descrivi per raccontarlo.
    stati: il dizionario degli stati e dei valori, cambiato sul posto.
    titolo: la riga che sta sopra il pannello.
    al_cambio: chiamata con (stati, voce) dopo ogni cambio; restituisce il
      messaggio da mostrare, o la stringa vuota.
    alla_conferma: chiamata con (stati, riga) all'Invio, dove riga e' la riga
      dello schermo su cui puo' scrivere; restituisce un messaggio che
      impedisce di uscire, o la stringa vuota per uscire.
    Restituisce vero se si e' confermato con l'Invio, falso se si e' usciti
    con Escape senza scegliere.
    """
    riga_base = 3
    # Il messaggio sta subito sotto l'ultima voce e il prompt subito sotto di
    # lui: fra le voci e il prompt resta al massimo una riga vuota, quella del
    # messaggio quando non c'e' niente da dire, e nessuna quando c'e'.
    riga_messaggi = riga_base + len(voci)
    riga_prompt = riga_messaggi + 1
    messaggio = ""
    while True:
        _move_cursor(riga_base - 1, 1)
        sys.stdout.write(titolo)
        _clear_line_from_cursor()
        print()
        for indice, voce in enumerate(voci):
            _move_cursor(riga_base + indice, 1)
            sys.stdout.write(riga_interruttore(voce, stati))
            _clear_line_from_cursor()
        _move_cursor(riga_messaggi, 1)
        if messaggio:
            sys.stdout.write(messaggio)
        _clear_line_from_cursor()
        messaggio = ""
        sommario = []
        for voce in voci:
            chiave = voce.get("key_state")
            # Le voci che sono solo un valore contano come accese quando il
            # valore non e' zero: lo stereo a zero e' spento, e nel sommario
            # si legge fra angolari come tutto cio' che e' spento. E' una
            # richiesta di Gabriele del 21 settembre 2026.
            acceso = bool(stati.get(chiave)) if chiave else bool(stati.get(voce.get("valore")))
            sommario.append("[{}]".format(voce["id"]) if acceso else "<{}>".format(voce["id"]))
        _move_cursor(riga_prompt, 1)
        _clear_line_from_cursor()
        sys.stdout.flush()
        scelta = key(prompt="\r" + " ".join(sommario) + ": \r")
        if scelta == "\x1b":
            pulisci_pannello(riga_base, len(voci))
            return False
        if not scelta or scelta == "\r":
            messaggio = alla_conferma(stati, riga_prompt + 1) if alla_conferma else ""
            if messaggio:
                suona("?")
                continue
            pulisci_pannello(riga_base, len(voci))
            return True
        scelto = next((v for v in voci if v["id"] == scelta), None)
        if scelto is None:
            messaggio = _("Scelta non valida.")
            suona("?")
            continue
        chiave = scelto.get("key_state")
        if chiave:
            stati[chiave] = not stati.get(chiave)
        if (scelto.get("valore") or scelto.get("chiedi_stati")) and (not chiave or stati.get(chiave)):
            # Accendendo una voce con un valore lo si chiede subito, con il
            # salvato come predefinito: un Invio lo conferma. Una voce con
            # piu' valori li chiede tutti e li scrive negli stati del
            # pannello, che sono gli stessi che poi si salvano e si usano.
            _move_cursor(riga_prompt + 1, 1)
            _clear_screen_from_cursor()
            if scelto.get("chiedi_stati"):
                scelto["chiedi_stati"](stati)
            else:
                stati[scelto["valore"]] = scelto["chiedi"](stati.get(scelto["valore"]))
            _move_cursor(riga_prompt + 1, 1)
            _clear_screen_from_cursor()
        if al_cambio:
            messaggio = al_cambio(stati, scelto) or ""


def pulisci_pannello(riga_base, quante):
    """Cancella le righe del pannello e riporta il cursore in cima."""
    for scarto in range(quante + 4):
        _move_cursor(riga_base - 1 + scarto, 1)
        _clear_line_from_cursor()
    # E poi tutto cio' che sta sotto, che nessuno sa quanto e': le domande
    # rifiutate scrivono una riga per rifiuto.
    _move_cursor(riga_base + quante + 3, 1)
    _clear_screen_from_cursor()
    _move_cursor(riga_base, 1)


def seleziona_modalita_rx():
    """Il pannello degli esercizi Rx: quali tipi di item mandare.

    La tecnica del pannello sta in pannello_interruttori, che il contest usa
    con le sue voci; qui restano le regole degli esercizi Rx, cioe'
    l'esclusione fra i gruppi, il filtro delle parole, il set personalizzato e
    la lunghezza dei gruppi generati.
    """
    switcher_settings_key = "rx_menu_switcher_states"
    if switcher_settings_key not in app_data:
        app_data[switcher_settings_key] = DEFAULT_DATA[switcher_settings_key].copy()
    stati = app_data[switcher_settings_key].copy()
    sessione = {"parole": None, "custom": stati.get("custom_set_string", ""), "lunghezza": 0}
    if stati.get("parole"):
        minimo = stati.get("parole_filter_min", 0)
        massimo = stati.get("parole_filter_max", 0)
        if minimo > 0 and massimo > 0 and minimo <= massimo:
            sessione["parole"] = [w for w in words if minimo <= len(w) <= massimo]
            if not sessione["parole"]:
                stati["parole"] = False
        else:
            stati["parole"] = False
    if stati.get("custom") and not sessione["custom"]:
        stati["custom"] = False

    def al_cambio(stati, voce):
        chiave = voce["key_state"]
        if not stati.get(chiave):
            return ""
        applica_esclusione_switcher(stati, chiave)
        if chiave == "parole":
            minimo = stati.get("parole_filter_min", 0)
            massimo = stati.get("parole_filter_max", 0)
            if not (minimo > 0 and massimo > 0 and minimo <= massimo):
                stati["parole"] = False
                sessione["parole"] = None
                return _("Filtro parole non impostato/valido. Usa il comando '.t #-#' nelle Impostazioni (k). Switcher 'Parole' disattivato.")
            sessione["parole"] = [w for w in words if minimo <= len(w) <= massimo]
            if not sessione["parole"]:
                stati["parole"] = False
                return _("Filtro parole caricato dalle impostazioni non ha prodotto risultati. Switcher 'Parole' disattivato.")
            return _("Filtro parole applicato dalle impostazioni ({count} parole).").format(count=len(sessione["parole"]))
        if chiave == "custom":
            if sessione["custom"] and len(sessione["custom"]) >= 2:
                return _("Gruppo Custom caricato dalle impostazioni: [{set_string}]").format(set_string=sessione["custom"])
            pulisci_pannello(3, len(RX_SWITCHER_ITEMS))
            _move_cursor(1, 1)
            sys.stdout.write(_("Avvio configurazione gruppo personalizzato...") + "\n\n")
            sys.stdout.flush()
            nuovo = CustomSet(overall_speed)
            if len(nuovo) >= 2:
                sessione["custom"] = nuovo
                stati["custom_set_string"] = nuovo
                return ""
            stati["custom"] = False
            sessione["custom"] = ""
            stati["custom_set_string"] = ""
            return _("Gruppo Custom non creato o non valido. Switcher 'Custom' disattivato.")
        return ""

    def alla_conferma(stati, riga):
        if not any(stati.get(voce["key_state"]) for voce in RX_SWITCHER_ITEMS):
            return _("Nessuna modalità di esercizio selezionata! Attiva almeno uno switcher.")
        if stati.get("parole") and not sessione["parole"]:
            return _("Errore: 'Parole' attivo ma il filtro non è impostato o non produce risultati. Usa '.t #-#'.")
        if stati.get("custom") and (not sessione["custom"] or len(sessione["custom"]) < 2):
            return _("Errore: il set personalizzato non è valido o è vuoto. Controlla le impostazioni.")
        if not any(stati.get(chiave) for chiave in ("lettere", "numeri", "custom", "lettere e numeri", "simboli")):
            return ""
        _move_cursor(riga, 1)
        domanda = _("Lunghezza gruppi (1-7 per Lettere/Numeri/Simboli/Custom):")
        sys.stdout.write(domanda)
        _clear_line_from_cursor()
        sys.stdout.flush()
        _move_cursor(riga, len(domanda) + 1)
        scritto = input()
        if scritto.isdigit() and 1 <= int(scritto) <= 7:
            sessione["lunghezza"] = int(scritto)
            return ""
        return _("Lunghezza non valida. Inserire un numero da 1 a 7.")

    if not pannello_interruttori(RX_SWITCHER_ITEMS, stati, _("Esercizi Rx - Seleziona Tipi (Invio per iniziare):"), al_cambio, alla_conferma):
        return None
    app_data[switcher_settings_key].update(stati)
    return {
        "active_switcher_states": stati,
        "parole_filtrate_list": sessione["parole"] if stati.get("parole") else None,
        "custom_set_string_active": sessione["custom"] if stati.get("custom") else None,
        "group_length_for_generated": sessione["lunghezza"],
    }


def _move_cursor(riga, colonna):
    """Muove il cursore alla riga e colonna specificata (1-based)."""
    sys.stdout.write(f"\x1b[{riga};{colonna}H")


def _clear_line_from_cursor():
    """Pulisce la linea dalla posizione attuale del cursore fino alla fine."""
    sys.stdout.write("\x1b[K")


def _clear_screen_from_cursor():
    """Pulisce dal cursore fino in fondo allo schermo.

    Serve dove non si sa quante righe si sono sporcate: una domanda
    rifiutata da dgt ne scrive una per ogni rifiuto, e nessuno sa quanti
    ne farai. Cancellare solo la riga corrente lasciava sotto il pannello
    le spiegazioni di una domanda gia' chiusa, e fra quelle l'unica riga
    che diceva che il valore era stato riportato dentro i limiti.
    """
    sys.stdout.write("\x1b[J")


def separa_archivio_contest(dati):
    """Sposta dall'archivio QRZ a quello del contest le sessioni del contest.

    Fino alla 7.0.4 il contest scriveva nelle chiavi del QRZ, issue 15. Le
    sue sessioni si riconoscono dal campo punteggio_grezzo, che scrive solo
    lui; quelle del contest di prima della 7.0.0 non lo portano e non si
    distinguono con certezza, quindi restano dove sono. I contatori passano
    con le sessioni: il tempo passa con la durata attiva, l'unica che il
    registro conserva, e i caratteri verso il prossimo rapporto con quelli
    della sessione, senza mai scendere sotto zero. Una seconda chiamata non
    trova piu' niente da spostare. Restituisce quante sessioni ha spostato.
    """
    registro_qrz = dati["historical_rx_data_qrz"].get("sessions_log", [])
    sessioni_contest = [s for s in registro_qrz if "punteggio_grezzo" in s]
    if not sessioni_contest:
        return 0
    dati["historical_rx_data_qrz"]["sessions_log"] = [s for s in registro_qrz if "punteggio_grezzo" not in s]
    archivio = dati["historical_rx_data_contest"]
    archivio["sessions_log"] = sorted(archivio.get("sessions_log", []) + sessioni_contest, key=lambda s: s.get("timestamp_iso", ""))
    caratteri = sum(s.get("chars_sent_session", 0) for s in sessioni_contest)
    storico_qrz = dati["historical_rx_data_qrz"]
    storico_qrz["chars_since_last_report"] = max(0, storico_qrz.get("chars_since_last_report", 0) - caratteri)
    archivio["chars_since_last_report"] = archivio.get("chars_since_last_report", 0) + caratteri
    spostati = {
        "sessions": len(sessioni_contest),
        "total_calls": sum(s.get("items_sent_session", 0) for s in sessioni_contest),
        "total_correct": sum(s.get("items_correct_session", 0) for s in sessioni_contest),
        "total_wrong_items": sum(s.get("items_sent_session", 0) - s.get("items_correct_session", 0) for s in sessioni_contest),
        "total_time_seconds": sum(s.get("duration_seconds", 0.0) for s in sessioni_contest),
    }
    conta_qrz = dati["rxing_stats_qrz"]
    conta_contest = dati["rxing_stats_contest"]
    for chiave, valore in spostati.items():
        conta_qrz[chiave] = max(0, conta_qrz.get(chiave, 0) - valore)
        conta_contest[chiave] = conta_contest.get(chiave, 0) + valore
    # Il contatore delle sessioni non scende sotto quelle che il registro
    # tiene ancora, come nella ripulitura delle sessioni vuote.
    conta_qrz["sessions"] = max(conta_qrz["sessions"], len(dati["historical_rx_data_qrz"]["sessions_log"]))
    return len(sessioni_contest)


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
                    # Copia profonda: con quella di superficie una sezione che
                    # il file non ha, come l'archivio del contest in un file
                    # della 7.0.4, divideva il suo registro con DEFAULT_DATA,
                    # e la prima sessione archiviata finiva anche li'.
                    merged_section = copy.deepcopy(default_values)
                else:  # Per valori non dizionari, come liste o semplici tipi
                    merged_section = default_values

                if isinstance(merged_section, dict) and isinstance(loaded_section, dict):
                    merged_section.update(loaded_section)  # Applica i valori caricati sui default
                merged_data[main_key] = merged_section

            # Assicurati che le nuove chiavi siano inizializzate se non presenti dopo la migrazione
            for key_suffix in CATEGORIE_ARCHIVIO:
                rx_stats_key = f"rxing_stats_{key_suffix}"
                if rx_stats_key not in merged_data:
                    merged_data[rx_stats_key] = copy.deepcopy(DEFAULT_DATA[rx_stats_key])
                hist_data_key = f"historical_rx_data_{key_suffix}"
                if hist_data_key not in merged_data:
                    merged_data[hist_data_key] = copy.deepcopy(DEFAULT_DATA[hist_data_key])

            spostate = separa_archivio_contest(merged_data)
            if spostate:
                print(_("Archivio: {quante} sessioni del contest spostate dall'archivio QRZ al loro.").format(quante=spostate))

            # Ripulitura delle sessioni vuote lasciate dalle versioni fino alla
            # 5.1.12: uscendo dal contest prima del primo QSO si registrava una
            # sessione senza dati, con velocita' minima 100 e massima 0, che
            # falsava le medie dell'archivio. Ora non se ne creano piu'.
            sessioni_vuote = 0
            for key_suffix in CATEGORIE_ARCHIVIO:
                hist_data_key = f"historical_rx_data_{key_suffix}"
                log = merged_data[hist_data_key].get("sessions_log", [])
                log_pulito = [s for s in log if s.get("items_sent_session", 0) > 0]
                if len(log_pulito) != len(log):
                    tolte = len(log) - len(log_pulito)
                    sessioni_vuote += tolte
                    merged_data[hist_data_key]["sessions_log"] = log_pulito
                    # Il contatore scende insieme al registro. Prima no, e i
                    # due numeri divergevano in silenzio: il rapporto QRZ
                    # diceva 78 sessioni e il contest 81, che sono le stesse
                    # sessioni contate da due parti diverse, meno tre vuote
                    # tolte il 7 settembre e mai scalate.
                    conta = merged_data[f"rxing_stats_{key_suffix}"]
                    conta["sessions"] = max(len(log_pulito), conta.get("sessions", 0) - tolte)
            if sessioni_vuote:
                print(_("Archivio ripulito: tolte {quante} sessioni senza dati.").format(quante=sessioni_vuote))
            print(_("Impostazioni generali caricate"))
            return merged_data
        except (OSError, json.JSONDecodeError, TypeError):
            print(_("Errore durante il caricamento del file di impostazioni."))
            return copy.deepcopy(DEFAULT_DATA)
    else:
        print(_("Impostazioni generali di default"))
        return copy.deepcopy(DEFAULT_DATA)


def save_settings(data, annuncia=True):
    """Salva le impostazioni correnti nel file JSON.

    Alla fine di ogni esercizio si salva con annuncia falso: il salvataggio
    riuscito si da' per scontato e lo si dice soltanto uscendo da CWapu,
    issue 18. Gli errori si dicono sempre.
    """
    try:
        data_to_save = data.copy()
        if "rxing_stats" in data_to_save and isinstance(data_to_save["rxing_stats"].get("total_time"), dt.timedelta):
            data_to_save["rxing_stats"]["total_time_seconds"] = data_to_save["rxing_stats"]["total_time"].total_seconds()
            data_to_save["rxing_stats"].pop("total_time", None)
        elif "rxing_stats" in data_to_save and "total_time" in data_to_save["rxing_stats"]:
            data_to_save["rxing_stats"].pop("total_time", None)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, indent=4, ensure_ascii=False)
        if annuncia:
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
    global overall_speed, overall_pitch, overall_dashes, overall_spaces, overall_dots, overall_volume, overall_ms, overall_fs, overall_wave, overall_farnsworth
    global overall_uscita_interfaccia, overall_uscita_dispositivo, overall_api
    # Le righe si concatenano invece di continuare con la barra rovesciata:
    # cosi' non finiscono ventotto spazi in fondo a ognuna, che a schermo
    # erano rumore e nel catalogo delle traduzioni erano peggio.
    MNKeyboard_settings = _(
        "Benvenuto nella sezione dove potrai ascoltare il CW e configurare tutti i suoi parametri.\n"
        "Questi parametri saranno validi e attivi in tutto CWapu e verranno salvati automaticamente quando esci dall'app.\n"
        "Ora, leggi attentamente quanto segue:\n"
        "\tPremi Invio senza digitare nulla per uscire e tornare al menu principale;\n"
        "\tdigita .w seguito da un valore numerico per impostare il WPM, da 5 a 120;\n"
        "\tdigita .fw seguito dalla velocità effettiva Farnsworth, da 5 alla velocità dei caratteri, oppure .fw 0 per spegnerlo;\n"
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
        "\tdigita .o per scegliere da quale uscita audio suonare;\n"
        "\tdigita ? per vedere questo messaggio di aiuto;\n"
        "\tdigita ?? per visualizzare i parametri impostati;\n"
        "\tdigita .rs per reimpostare il CW al peso standard di 1/3 e spegnere il Farnsworth;\n"
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
            base_settings_line2 = _("\tL/S/P: {overall_dashes}/{overall_spaces}/{overall_dots}, FW: {fw}, Wave: {}, MS: {overall_ms}, FS: {}.").format(
                WAVE_TYPES[overall_wave - 1],
                SAMPLE_RATES[overall_fs],
                overall_dashes=overall_dashes,
                overall_spaces=overall_spaces,
                overall_dots=overall_dots,
                overall_ms=overall_ms,
                fw=overall_farnsworth or _("no"),
            )
            history_settings_line = _("\tMax Exercises History (g): {current_max_sessions_g_val}, Report size (x): {current_report_interval_x_val}.").format(
                current_max_sessions_g_val=current_max_sessions_g_val, current_report_interval_x_val=current_report_interval_x_val
            )
            new_filter_settings_line = _("\tWord Filter (T): {t_filter_display}, Custom Set (Y): {y_custom_set_display}").format(
                t_filter_display=t_filter_display, y_custom_set_display=y_custom_set_display
            )
            print(base_settings_line1)
            print(base_settings_line2)
            print(_("\tUscita audio: {uscita}.").format(uscita=descrizione_uscita_corrente()))
            if overall_uscita_interfaccia and overall_api is None:
                print(_("Uscita audio salvata non trovata oggi: lascio scegliere a CWapu, e la riprovo al prossimo avvio."))
            print(history_settings_line)
            print(new_filter_settings_line)
            msg_for_cw = "bk r parameters are bk"
        elif msg == ".o ":
            prima = (overall_uscita_interfaccia, overall_uscita_dispositivo, overall_api)
            cambiata = scegli_uscita_audio() is not None
            # Il feedback suona sull'uscita di adesso ed e' la prova vera,
            # anche quando non e' cambiato niente: cosi' si sente sempre da
            # dove si sta suonando. Se non si apre e si era appena cambiata,
            # si torna a quella di prima e lo si dice.
            plo, rwpm_temp = suona("bk r out ok bk", avvisa=False)
            if plo is None:
                errore = getattr(CWzator, "ultimo_errore", None)
                if cambiata:
                    overall_uscita_interfaccia, overall_uscita_dispositivo, overall_api = prima
                    dove = descrizione_uscita(prima[0], prima[1]) if prima[2] is not None else _("automatica")
                    print(_("Uscita non utilizzabile, torno a {uscita}: {errore}").format(uscita=dove, errore=errore))
                    plo, rwpm_temp = suona("?")
                else:
                    print(_("Il motore CW non ha trasmesso il messaggio: {errore}").format(errore=errore))
            if rwpm_temp is not None:
                rwpm = rwpm_temp
            msg_for_cw = ""
        elif msg == ".sr ":
            new_fs_index = ItemChooser(SAMPLE_RATES)
            if new_fs_index != overall_fs:
                overall_fs = new_fs_index
            # Il mixer condiviso apre la scheda alla propria frequenza e
            # riporta a quella ogni messaggio: senza questa riga la
            # frequenza di .sr non arrivava alla scheda, come invece
            # promette. Il feedback che segue suona gia' alla frequenza
            # nuova, e se l'uscita non la regge suona() lo dice.
            Acusticator.setup(fs=SAMPLE_RATES[overall_fs])
            plo, rwpm_temp = suona(_("bk fs is {} bk").format(SAMPLE_RATES[overall_fs]))
            if rwpm_temp is not None:
                rwpm = rwpm_temp
            msg_for_cw = ""
        elif msg == ".rs ":
            if not (overall_dashes == 30 and overall_spaces == 50 and (overall_dots == 50)):
                overall_dashes, overall_spaces, overall_dots = (30, 50, 50)
            # Il CW standard e' anche senza Farnsworth: lasciarlo acceso qui
            # farebbe di "reimposta al peso standard" una mezza verita'.
            overall_farnsworth = 0
            plo, rwpm_temp = suona("bk reset ok bk")
            if rwpm_temp is not None:
                rwpm = rwpm_temp
            msg_for_cw = ""
        elif msg.lower().startswith(".fw"):
            # Sta prima del parser numerico generico, che leggerebbe .fw8
            # come il comando f seguito da spazzatura.
            valore_fw = valore_comando_fw(msg)
            if valore_fw is not None:
                richiesto = limita_farnsworth(valore_fw, overall_speed)
                if richiesto == 0:
                    overall_farnsworth = 0
                    feedback_fw = "bk r fw off bk"
                elif farnsworth_ammesso(richiesto, overall_speed, overall_dashes, overall_spaces, overall_dots):
                    overall_farnsworth = richiesto
                    feedback_fw = _("bk r fw is {fw} bk").format(fw=richiesto)
                else:
                    # I pesi di adesso non consentono questa velocita'
                    # effettiva: il messaggio del motore dice fin dove si
                    # puo' arrivare, e il valore non si imposta.
                    print(_("Farnsworth non impostato: {errore}").format(errore=getattr(CWzator, "ultimo_errore", None)))
                    feedback_fw = "?"
            else:
                feedback_fw = "?"
            plo, rwpm_temp = suona(feedback_fw)
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
            letto_numerico = comando_numerico(command_candidate_str)
            if letto_numerico is not None:
                cmd_letter_parsed, value_int_parsed = letto_numerico
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
                        # Il registro e' diviso in categorie: la potatura va
                        # ripetuta su tutte, non su una chiave sola.
                        for suffisso_categoria in CATEGORIE_ARCHIVIO:
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
                    allinea_farnsworth()
                    feedback_cw = _("bk r w is {overall_speed} bk").format(overall_speed=overall_speed)
                    command_processed_internally = True
                elif cmd_letter_parsed == "m":
                    if overall_ms != value_int_parsed:
                        new_ms = max(1, min(30, value_int_parsed))
                        if overall_ms != new_ms:
                            overall_ms = new_ms
                    # Il valore si salva intero, ma CWzator accorcia ogni rampa
                    # a meta' dell'elemento: a 47 wpm tutto cio' che supera 12
                    # suona uguale sul punto, e va detto invece di lasciarlo
                    # scoprire all'orecchio.
                    tetto_ms = rampa_massima_ms(overall_speed, overall_dots)
                    if overall_ms > tetto_ms:
                        print(_("MS {ms}, a {wpm} wpm il punto la limita a {tetto:.0f}.").format(ms=overall_ms, wpm=overall_speed, tetto=tetto_ms))
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
                        new_pitch = max(PITCH_MIN, min(PITCH_MAX, value_int_parsed))
                        if overall_pitch != new_pitch:
                            overall_pitch = new_pitch
                    feedback_cw = _("bk r h is {overall_pitch} bk").format(overall_pitch=overall_pitch)
                    command_processed_internally = True
                elif cmd_letter_parsed == "l":
                    if overall_dashes != value_int_parsed:
                        new_dashes = max(1, min(99, value_int_parsed))
                        if overall_dashes != new_dashes:
                            overall_dashes = new_dashes
                    allinea_farnsworth()
                    feedback_cw = _("bk r l is {overall_dashes} bk").format(overall_dashes=overall_dashes)
                    command_processed_internally = True
                elif cmd_letter_parsed == "s":
                    if overall_spaces != value_int_parsed:
                        new_spaces = max(3, min(99, value_int_parsed))
                        if overall_spaces != new_spaces:
                            overall_spaces = new_spaces
                    allinea_farnsworth()
                    feedback_cw = _("bk r s is {overall_spaces} bk").format(overall_spaces=overall_spaces)
                    command_processed_internally = True
                elif cmd_letter_parsed == "p":
                    if overall_dots != value_int_parsed:
                        new_dots = max(1, min(99, value_int_parsed))
                        if overall_dots != new_dots:
                            overall_dots = new_dots
                    allinea_farnsworth()
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
            "Attenzione! Si prega di leggere attentamente.\nPer gli esercizi di ricezione, (r) dal menu principale, CWapu utilizza il file words.txt, che deve stare nella stessa cartella di cwapu.py o di cwapu.exe. Se questo file non esiste, creane uno con un editor di testo e scrivi alcune parole al suo interno, una parola per linea, quindi salva.\nLa procedura WordsCreator ti permette di scansionare tutti i file txt contenuti nelle cartelle che indichi e aggiungere tutte le parole da questi file a words.txt. Le parole saranno aggiunte unicamente, cioè saranno tutte diverse tra loro.\nIl file prodotto da questo processo sarà denominato words_updated.txt. Controllalo con un editor di testo e, se sei soddisfatto, rinominalo in words.txt, sostituendo l'esistente words.txt.\nPuoi ripetere questa operazione tutte le volte che vuoi: words_updated.txt conterrà le parole da words.txt più tutte quelle raccolte dai nuovi file .txt elaborati."
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
        # Il registro e' diviso in parole, caratteri, QRZ e contest: un errore
        # su una lettera resta un errore su quella lettera, quindi si guardano
        # tutte. Prima si leggeva una chiave che non esiste piu' dalla
        # migrazione, e la precompilazione non ha mai avuto dati veri.
        sessions_log = []
        for suffisso_categoria in CATEGORIE_ARCHIVIO:
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
            with apri_diario() as f:
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


# Il contest: i valori che si regolano con i tasti durante la sessione e non
# stanno nelle impostazioni, perche' valgono per il contest in corso.
CONTEST_BANDA_DEFAULT = 500
CONTEST_BANDA_MIN = 100
CONTEST_BANDA_MAX = 600
CONTEST_PASSO_BANDA = 50
CONTEST_PASSO_PITCH = 50
CONTEST_PASSO_WPM = 2
# Il volume si muove in percentuale, come lo scrive il comando .v.
CONTEST_PASSO_VOLUME = 5
# Ogni quanto il ciclo guarda la tastiera e fa girare l'orologio del motore.
# key con un'attesa breve su Windows aspetta dentro il sistema, quindi il
# ciclo non consuma processore come farebbe un giro a vuoto.
CONTEST_PASSO_CICLO = 0.05
CONTEST_TAGLIO_NUMERI = {"T": "0", "O": "0", "N": "9"}


def descrivi_pannello_contest(stati):
    """Gli interruttori e i valori con cui la sessione e' stata fatta.

    Vanno nel rapporto e nel diario perche' una sessione in pile-up con il
    tasto verticale al cento per cento e una da sola con tutti in automatico
    non sono confrontabili, e l'archivio deve poterlo dire.
    """
    pezzi = [_("pile-up con attività {n}").format(n=stati["attivita"]) if stati["pileup"] else _("una stazione alla volta")]
    if stati["qrm"]:
        pezzi.append(_("QRM fino a {n}").format(n=stati["qrm_massime"]))
    for chiave, nome in (("qrn", _("QRN")), ("qsb", _("QSB")), ("flutter", _("flutter")), ("sbadati", _("operatori sbadati"))):
        if stati[chiave]:
            pezzi.append(nome)
    pezzi.append(_("stereo {n}").format(n=stati["stereo"]))
    pezzi.append(_("banda {n} hertz").format(n=stati["banda"]))
    if stati["tasto_verticale"]:
        pezzi.append(
            _("manipolazione manuale al {p}%, L {l0}-{l1}, S {s0}-{s1}, P {p0}-{p1}").format(
                p=stati["tasto_probabilita"],
                l0=stati["tasto_l_min"],
                l1=stati["tasto_l_max"],
                s0=stati["tasto_s_min"],
                s1=stati["tasto_s_max"],
                p0=stati["tasto_p_min"],
                p1=stati["tasto_p_max"],
            )
        )
    else:
        pezzi.append(_("tutti in manipolazione automatica"))
    return ", ".join(pezzi)


class InsiemeDiSuoni:
    """Piu' pezzi che insieme fanno un messaggio solo.

    Il ciclo del contest tiene una voce per stazione e la interroga per
    sapere se ha finito, o la zittisce quando comincio a trasmettere. Un
    messaggio spezzato in pezzi sono piu' voci, ma per il ciclo devono
    restare una cosa sola: altrimenti ne fermerebbe uno e gli altri
    continuerebbero a suonare sotto la mia trasmissione.
    """

    def __init__(self, pezzi, durata):
        self.pezzi = list(pezzi)
        self.durata = float(durata)
        self.is_playing = self

    def is_set(self):
        """Suona finche' almeno un pezzo suona."""
        return any(h.is_playing.is_set() for h in self.pezzi)

    def stop(self):
        for h in self.pezzi:
            h.stop()
        return True


def buco_fra_pezzi(wpm, s, parola):
    """Il silenzio che separa due pezzi, in secondi.

    Misurato su CWzator: fra due lettere vale 1,4 unita' piu' sei centesimi
    per ogni punto di peso degli spazi sopra venticinque, e fra due parole
    due unita' in piu' ogni venticinque punti di peso. Con i pesi standard
    fanno 2,9 e 6,9 unita', e la formula segue la misura entro tre
    millesimi di secondo da diciotto a cinquanta parole al minuto.
    """
    unita = 1.2 / max(1, int(wpm))
    lettere = 1.4 + (int(s) - 25) * 0.06
    return unita * (lettere + (2.0 * int(s) / 25.0 if parola else 0.0))


def righe_rapporto_contest(punteggio, stati, durata_secondi, con_rinunce=True):
    """Le righe che il contest aggiunge al rapporto, a video e nel diario.

    Con con_rinunce falso si lascia fuori l'elenco di chi se n'e' andato,
    che a schermo e' una riga lunga di nominativi che scorrono via senza
    servire a niente: nel diario invece si rilegge con calma.

    Sono quelle di cwsim: punti, prefissi e punteggio grezzi e verificati, la
    percentuale di errore, il ritmo per ogni cinque minuti, cio' che e' stato
    copiato male e chi se n'e' andato, piu' i valori del pannello.
    """
    righe = [
        _("Punti {punti}, prefissi {prefissi}, punteggio {totale}.").format(
            punti=punteggio.punti_grezzi, prefissi=len(punteggio.prefissi_grezzi), totale=punteggio.punteggio_grezzo
        ),
        _("Verificati: punti {punti}, prefissi {prefissi}, punteggio {totale}.").format(
            punti=punteggio.punti_verificati, prefissi=len(punteggio.prefissi_verificati), totale=punteggio.punteggio_verificato
        ),
        _("QSO sbagliati: {errore:.1f}%.").format(errore=punteggio.percentuale_errore),
    ]
    ritmo = punteggio.qso_all_ora(durata_secondi)
    if ritmo:
        righe.append(_("Ritmo: ") + "; ".join(_("dal {da} al {a} minuto {quanti} all'ora").format(da=da, a=a, quanti=quanti) for da, a, quanti in ritmo) + ".")
    sbagliati = punteggio.nominativi_sbagliati()
    if sbagliati:
        righe.append(_("Nominativi copiati male: {elenco}.").format(elenco=", ".join(sbagliati)))
    scambi = punteggio.scambi_sbagliati()
    if scambi:
        righe.append(_("Scambi copiati male: {elenco}.").format(elenco=", ".join(f"{v.nominativo} {v.rst_ricevuto} {v.nr_ricevuto}" for v in scambi)))
    if punteggio.rinunce and con_rinunce:
        # Le occasioni perse dicono qualcosa di vero, cioe' quanto sono stato
        # lento a rispondere, ma non sono QSO copiati male: stanno fuori da
        # QSO, percentuali, velocita' e durata. E stanno fuori anche dalla
        # console, dove l'elenco dei nominativi e' rumore che scorre via:
        # nel diario invece resta, e li' serve.
        righe.append(_("Se ne sono andate {quante}: {elenco}.").format(quante=len(punteggio.rinunce), elenco=", ".join(punteggio.rinunce)))
    righe.append(_("Sessione fatta con: {valori}.").format(valori=descrivi_pannello_contest(stati)))
    return righe


def chiedi_pesi_tasto(stati):
    """I sette valori del tasto verticale, uno per uno, con dgt che ne tiene i limiti.

    Decisioni D13 e D14: la probabilita' e' una sola, come oggi, e ogni valore
    si chiede con dgt proponendo il salvato, cosi' sette Invio confermano
    tutto e nessun valore puo' finire fuori intervallo. Il massimo si chiede
    dopo il minimo con il minimo come limite inferiore, cosi' un intervallo
    rovesciato non si puo' nemmeno scrivere. I limiti sono da 1 a 100, che e'
    cio' che CWzator accetta.
    """
    stati["tasto_probabilita"] = chiedi_intero(_("Tasto verticale, percentuale"), 0, 100, stati["tasto_probabilita"])
    for lettera, nome in (("l", _("linea")), ("s", _("spazio")), ("p", _("punto"))):
        minimo = chiedi_intero(_("{nome}, minimo").format(nome=nome), 1, 100, stati[f"tasto_{lettera}_min"])
        massimo = chiedi_intero(_("{nome}, massimo").format(nome=nome), minimo, 100, max(minimo, stati[f"tasto_{lettera}_max"]))
        stati[f"tasto_{lettera}_min"] = minimo
        stati[f"tasto_{lettera}_max"] = massimo


def impostazioni_contest():
    """Gli stati del contest salvati, completati con i predefiniti dove mancano.

    Le chiavi del tasto verticale si sono chiamate manipolo per un giorno
    solo, il 20 settembre 2026: un file salvato quel giorno le porta ancora,
    e si leggono lo stesso invece di tornare ai predefiniti senza dirlo.
    """
    salvati = app_data.setdefault("contest_settings", {})
    letti = {}
    for chiave, valore in salvati.items():
        if chiave == "manipolo":
            chiave = "tasto_verticale"
        elif chiave.startswith("manipolo_"):
            chiave = "tasto_" + chiave[len("manipolo_") :]
        if chiave in CONTEST_PREDEFINITI:
            letti[chiave] = valore
    return {**CONTEST_PREDEFINITI, **letti}


def pesi_del_tasto(stati):
    """Gli intervalli del tasto verticale come il motore li vuole.

    Con il tasto verticale spento la probabilita' e' zero, e tutte le
    stazioni manipolano in automatico, con i pesi standard di CWzator.
    """
    probabilita = stati["tasto_probabilita"] if stati["tasto_verticale"] else 0
    return (
        probabilita,
        (stati["tasto_l_min"], stati["tasto_l_max"]),
        (stati["tasto_s_min"], stati["tasto_s_max"]),
        (stati["tasto_p_min"], stati["tasto_p_max"]),
    )


def pannello_contest():
    """Il pannello del contest: restituisce gli stati, o None se si esce con Escape.

    Gli stati e i valori si salvano in cwapu_settings.json sotto una chiave
    propria del contest, come quelli degli esercizi Rx.
    """
    stati = impostazioni_contest()

    def al_cambio(stati, voce):
        chiave = voce.get("key_state")
        if chiave in CONTEST_NON_DISPONIBILI and stati.get(chiave):
            stati[chiave] = False
            return _("Non c'è ancora: arriverà quando il motore audio saprà farlo.")
        if chiave == "tasto_verticale" and stati.get(chiave):
            pulisci_pannello(3, len(CONTEST_VOCI))
            _move_cursor(1, 1)
            chiedi_pesi_tasto(stati)
            # Sette domande scritte dalla riga uno in giu': senza questo, la
            # prima resta sopra il titolo del pannello con dentro la risposta
            # che hai dato, e se poi cambi idea dice un valore che non e' piu'
            # vero.
            _move_cursor(1, 1)
            _clear_screen_from_cursor()
        return ""

    if not pannello_interruttori(CONTEST_VOCI, stati, _("Contest - Interruttori e valori (Invio comincia, Esc annulla tutto):"), al_cambio):
        return None
    app_data.setdefault("contest_settings", {}).update(stati)
    return stati


def numero_dal_taglio(testo):
    """Le abbreviazioni dei numeri tornano cifre: T e O valgono zero, N vale nove.

    Sono le sole tre che le stazioni producono, e sono quelle che conviene
    scrivere al volo invece di tradurle a mente: 5NN TT1 vale 599 1.
    """
    return "".join(CONTEST_TAGLIO_NUMERI.get(c, c) for c in testo.upper())


def leggi_scambio(testo):
    """Il campo dello scambio: restituisce (rapporto, numero), o None se non si legge.

    Decisione D8 del 2026-09-15: si scrive il solo numero, oppure rapporto e
    numero separati da uno spazio. Senza rapporto vale 599, che in contest si
    manda sempre.
    """
    pezzi = numero_dal_taglio(testo).split()
    if not pezzi:
        return None
    rst, nr = ("599", pezzi[0]) if len(pezzi) == 1 else (pezzi[0], pezzi[1])
    if not rst.isdecimal() or not nr.isdecimal():
        return None
    return int(rst), int(nr)


def chiedi_nominativo_contest():
    """Il nominativo con cui si va in contest, chiesto la prima volta e riproposto poi.

    Decisione D7 del 2026-09-15. Restituisce la stringa vuota se non lo si
    vuole dare, e allora il contest non comincia.
    """
    global overall_contest_call
    salvato = overall_contest_call or ""
    prompt = _("Il tuo nominativo [{proposto}]: ").format(proposto=salvato) if salvato else _("Il tuo nominativo: ")
    scritto = dgt(prompt=prompt, kind="s", smin=0, smax=12, default=salvato)
    scritto = (scritto or "").strip().upper()
    if scritto:
        overall_contest_call = scritto
    return overall_contest_call


def RxingContest(menu_config_scelta):
    """Il contest con il motore di contest.py: modo singolo, una stazione alla volta.

    Tappa 3 del piano della issue 7. Il ciclo non inventa piu' i QSO: chiede
    al motore cosa suonare, gli dice quali suoni sono finiti e gli riferisce i
    tasti. pynput esce di scena, perche' i tasti arrivano da key con un'attesa
    breve. Il pile-up, il pannello dei valori e gli effetti sono le tappe
    seguenti, e qui non ci sono: una stazione alla volta, al centro, senza
    disturbi. Nel contest il Farnsworth non esiste, per decisione presa: ogni
    messaggio parte con farnsworth zero e le statistiche si salvano sempre.
    """
    global overall_speed, overall_pitch, overall_volume
    mio_nominativo = chiedi_nominativo_contest()
    if not mio_nominativo:
        print(_("Senza nominativo il contest non si fa."))
        key(_("Premi un tasto per tornare al menu..."))
        return
    stati = pannello_contest()
    if stati is None:
        return
    scelta_durata = menu(d={"1": _("Numero di QSO"), "2": _("Tempo (minuti)")}, p=_("Scegli la durata: "))
    if not scelta_durata:
        return
    duration_type = int(scelta_durata)
    if duration_type == 1:
        limit = chiedi_intero(_("Quanti QSO"), 1, 500, CONTEST_QSO_PREDEFINITI)
    else:
        limit = chiedi_intero(_("Quanti minuti"), 1, 60, CONTEST_MINUTI_PREDEFINITI)
    if stati["pileup"]:
        print(_("Contest come {call}, pile-up con attività {n}.").format(call=mio_nominativo, n=stati["attivita"]))
    else:
        print(_("Contest come {call}, una stazione alla volta.").format(call=mio_nominativo))
    print(_("F1 CQ, F2 scambio, F3 TU, F4 il mio call"))
    print(_("F5 il suo call, F6 QSO B4, F7 ?, F8 NIL"))
    print(_("Invio manda cio' che serve e mette a log"))
    print(_("Esc ferma la trasmissione o pulisce la riga"))
    print(_("Backspace a riga vuota torna al nominativo"))
    print(_("Frecce, Inizio, Fine e Canc dentro la riga"))
    print(_("Spazio passa al numero senza trasmettere"))
    print(_("Alt+S dice tempo, QSO, punti e punteggio"))
    print(_("F9 e PagGiu' meno 2 WPM, F10 e PagSu piu' 2"))
    print(_("Alt+F9 e Alt+F10 abbassano e alzano il volume"))
    print(_("Alt+Su e Alt+Giu' il tono, Shift+Su e Giu' la banda"))
    print(_("Alt+W pulisce i campi, Alt+X chiude il contest"))
    key(_("Premi un tasto per iniziare..."))

    def prossimo_nominativo():
        return Mkdqrz(random.choices(list(MDL.keys()), weights=list(MDL.values()), k=1))

    banda = stati["banda"]
    motore = ct.Contest(
        mio_nominativo,
        overall_speed,
        overall_pitch,
        prossimo_nominativo,
        pileup=stati["pileup"],
        attivita=stati["attivita"],
        sbadati=stati["sbadati"],
        qrm=stati["qrm"],
        qrm_massime=stati["qrm_massime"],
        qsb=stati["qsb"],
        flutter=stati["flutter"],
        ampiezza_stereo=stati["stereo"],
        banda=banda,
        pesi_manuali=pesi_del_tasto(stati),
        # La mia manipolazione ha i miei pesi, quelli di .l .s .p, come in
        # tutta l'applicazione. Dal 22 settembre la mia richiesta passava per
        # la stessa strada di quelle delle stazioni, e portava i pesi
        # standard che il motore le dava: la mia stazione manipolava a 30 50
        # 50 qualunque cosa avessi impostato. Trovato da Gabriele provando
        # l'eseguibile compilato della 7.0.0.
        mio_pesi=(overall_dashes, overall_spaces, overall_dots),
        # Spento vuol dire che non lo fa nessuno, e nemmeno io.
        scambio_probabilita=stati["scambio_probabilita"] if stati["scambio_veloce"] else 0,
        scambio_incremento=stati["scambio_incremento"],
    )
    start_time = dt.datetime.now()
    session_calls = 0
    correct_calls = 0
    total_calls_correct = 0
    total_serials_correct = 0
    item_details = []
    sent_chars_detail_this_session = {}
    char_error_counts = {}
    total_mistakes_calculated = 0
    minwpm = None
    maxwpm = 0
    sum_wpm = 0.0
    active_exerctime = dt.timedelta(0)
    campo = ""
    # Dove sta il cursore dentro il campo: il nominativo si corregge come in
    # un editor, non solo cancellando dalla coda.
    cursore = 0
    stadio = "call"
    suo_call = ""
    # Cosa ho gia' detto a questa stazione. Sono le due spie di Morse
    # Runner: senza, l'Invio rimandava ogni volta tutto da capo, anche cio'
    # che lei aveva gia' sentito e confermato.
    suo_mandato = False
    scambio_mandato = False
    # Il nominativo a cui le spie si riferiscono: se nel frattempo nella riga
    # ce n'e' un altro, quello che ho detto non vale per lui.
    nominativo_mandato = ""
    suoni = {}
    # I messaggi dei tasti funzione battuti mentre ne suona un altro: si
    # accodano invece di tagliarlo, e ognuno porta con se' il nominativo
    # che c'era nella riga quando il tasto e' stato premuto.
    coda = []
    # L'istante in cui la mia ultima trasmissione finisce davvero: il ciclo
    # se ne accorge fino a un passo dopo, e il messaggio accodato deve
    # contare anche il silenzio gia' trascorso.
    fine_mia = 0.0
    da_chiudere = set()
    # Cio' che il motore ha prodotto in un giro di orologio fatto fuori dal
    # ciclo, cioe' in chiudi_i_finiti: il ciclo lo raccoglie al primo giro
    # utile, che dista al massimo un passo.
    richieste_rimandate = []
    eventi_rimandati = []
    rwpm_corrente = 0.0
    fondo = None
    fondo_pronto = None
    # Cio' con cui il fruscio pronto e' stato fatto: se non cambia, non si
    # rifa'.
    fondo_chiave = None
    annunci = {}
    attesa_fine = {}

    def prepara_fondo():
        """Sintetizza il fruscio di QRN, largo quanto lo stereo chiede.

        Costa un decimo di secondo, quindi si fa solo quando cambia qualcosa
        che lo riguarda: la banda, il tono, o l'inizio del contest. Stringere
        il filtro deve stringere anche il rumore.

        E si fa solo quando cambia davvero. Alt e le frecce al tetto del tono
        non lo alzano, ma rifacevano il fruscio da capo a ogni pressione, con
        una grana nuova ogni volta e un decimo di secondo di ciclo perso:
        tenendo premuto si sentiva un rumore che si interrompe e riparte molte
        volte al secondo, e a orecchio sembrava che si stringesse la banda.
        """
        nonlocal fondo_pronto, fondo_chiave
        if not stati["qrn"]:
            spegni_fondo()
            fondo_pronto = None
            fondo_chiave = None
            return
        basso = max(50, overall_pitch - banda // 2)
        alto = max(basso + 50, overall_pitch + banda // 2)
        chiave = (basso, alto, overall_volume, stati["stereo"], overall_fs)
        if fondo_pronto is not None and chiave == fondo_chiave:
            return
        spegni_fondo()
        fondo_pronto = None
        fondo_chiave = chiave
        # Il fruscio segue il volume generale, come tutto il resto: se non lo
        # seguisse, abbassando il volume si alzerebbe rispetto alle stazioni.
        score = [f"{basso}-{alto}", CONTEST_FONDO_SECONDI, 0.0, CONTEST_FONDO_VOLUME * overall_volume]
        frequenza = SAMPLE_RATES[overall_fs]
        # Due sintesi, una per canale: lo score da solo le farebbe identiche.
        primo = Acusticator.sintetizza(score, kind=6, adsr=CONTEST_FONDO_ADSR, fs=frequenza)
        secondo = Acusticator.sintetizza(score, kind=6, adsr=CONTEST_FONDO_ADSR, fs=frequenza)
        if primo is None or secondo is None:
            return
        fondo_pronto = fronte_stereo(primo, secondo, stati["stereo"])

    def accendi_fondo():
        """Rimette in aria il fruscio gia' pronto: non risintetizza niente."""
        nonlocal fondo
        if fondo is None and fondo_pronto is not None:
            fondo = Acusticator.ciclo_di(fondo_pronto, fs=SAMPLE_RATES[overall_fs])

    def spegni_fondo():
        """Spegne il fondo, e soltanto quello: le stazioni proseguono."""
        nonlocal fondo
        if fondo is not None:
            fondo.stop()
            fondo = None

    def metti_in_aria(richiesta, inizio=0.0):
        """Sintetizza la richiesta, in un pezzo solo o in piu' pezzi allineati.

        Quando la stazione accelera il rapporto, il messaggio si spezza: ogni
        pezzo e' una sintesi a se', e i pezzi dopo il primo partono con un
        silenzio davanti pari a tutto quello che li precede, invece di
        aspettare che il precedente finisca. Cosi' escono tutti nello stesso
        giro di ciclo e il messaggio si riunisce al millesimo: aspettare il
        giro dopo avrebbe aperto un buco di cinquanta millesimi in mezzo a un
        gruppo di lettere, che si sente come uno strappo.

        Restituisce una voce sola per il ciclo, e la velocita' di base, che e'
        quella del primo pezzo: registrando quella accelerata, le statistiche
        del QSO direbbero una velocita' che non e' mai stata la sua.

        Con inizio maggiore di zero tutto il messaggio parte piu' tardi: e' il
        silenzio che separa un mio messaggio accodato da quello che lo
        precede.
        """
        voce = {
            "pitch": richiesta.pitch,
            "l": richiesta.l,
            "s": richiesta.s,
            "p": richiesta.p,
            "sync": False,
            "farnsworth": 0,
            "pan": richiesta.pan,
            # La mia trasmissione usa il volume generale, non un volume di
            # stazione: e' la stessa cosa in uscita, ma dice a chi ascolta il
            # ciclo che quella voce sono io.
            "vol": None if richiesta.stazione == ct.IO else richiesta.volume,
            "qsb": richiesta.qsb,
            "chirp": richiesta.chirp,
            "vibrato": richiesta.vibrato,
        }
        if not richiesta.pezzi:
            return suona(richiesta.testo, wpm=richiesta.wpm, ritardo=inizio or None, **voce)
        maniglie = []
        # L'istante in cui ogni pezzo deve cominciare, contato dall'inizio
        # del messaggio: e' la somma di tutto cio' che lo precede, suono e
        # silenzio. La durata che il motore restituisce per un pezzo
        # ritardato comprende gia' il suo silenzio iniziale, quindi va
        # tolta per sapere quanto dura il solo suono.
        base = 0.0
        for indice, (testo, wpm_pezzo, parola) in enumerate(richiesta.pezzi):
            if indice:
                inizio += buco_fra_pezzi(richiesta.wpm, richiesta.s, parola)
            handle, rwpm = suona(testo, wpm=wpm_pezzo, ritardo=inizio or None, **voce)
            if handle is None:
                for gia in maniglie:
                    gia.stop()
                return None, 0.0
            maniglie.append(handle)
            if not indice:
                base = rwpm
            inizio = durata_suono(handle)
        return InsiemeDiSuoni(maniglie, inizio), base

    def durata_suono(handle):
        """I secondi che quel messaggio durera', per sapere quando finirebbe anche zittito."""
        if isinstance(handle, InsiemeDiSuoni):
            return handle.durata
        try:
            return handle.audio_data.size / float(handle.sample_rate)
        except (AttributeError, TypeError, ValueError, ZeroDivisionError):
            return 0.0

    def chiudi_i_finiti(adesso):
        """Dice al motore chi ha appena finito, prima che io cominci a parlare.

        Il ciclo se ne accorge una volta ogni cinquanta millesimi, ma il tasto
        si batte quando si vuole: fra l'ultimo elemento di una stazione e il
        giro che lo registra c'e' una finestra cieca in cui lei, per il
        motore, sta ancora trasmettendo. Partendo li' dentro la stazione
        sente spazzatura e butta via tutto il messaggio, compreso il proprio
        nominativo: ripete, si riscrive uguale, ripete ancora, e dopo tre o
        quattro giri se ne va. Chi copia al volo ci cade spesso, e non ha
        modo di accorgersene, perche' il ricevitore si spegne nell'istante
        del tasto.
        """
        finiti = {chi for chi, handle in suoni.items() if chi != ct.IO and not handle.is_playing.is_set()}
        if not finiti:
            return
        for chi in finiti:
            ferma(chi)
            attesa_fine.pop(chi, None)
        esito = motore.avanza(adesso, finiti)
        # Cio' che nasce in questo giro fuori turno non si butta: una stazione
        # che riparte proprio adesso, o un QSO che si chiude, li prende il
        # ciclo al giro seguente, che dista al massimo un passo.
        richieste_rimandate.extend(esito.richieste)
        eventi_rimandati.extend(esito.eventi)

    def zittisci_ricezione():
        """Mentre trasmetto non sento niente: ne' il fruscio ne' chi e' gia' in aria.

        In radio il ricevitore tace mentre si trasmette, e sentirsi le
        stazioni sopra la propria chiamata non succede. Chi era in aria
        prosegue per conto suo, e il motore lo sa: qui si toglie soltanto il
        suono, e l'istante in cui quel messaggio sarebbe finito resta
        segnato, cosi' i tempi del contest non si muovono di un millesimo.
        """
        spegni_fondo()
        for chi in [c for c in suoni if c != ct.IO]:
            ferma(chi)

    def in_trasmissione():
        """Vero se il mio tasto e' abbassato, cioe' se il ricevitore deve tacere."""
        return motore.io_trasmette or ct.IO in suoni

    def ferma(chi):
        """Zittisce una trasmissione e la toglie dai suoni in corso."""
        handle = suoni.pop(chi, None)
        if handle is not None:
            handle.stop()

    def riga_di_stato():
        """La riga che si riscrive: e' quella di oggi, dentro i quaranta caratteri.

        Decisione D2: si riscrive solo quando si batte un tasto, cosi' il
        display braille non insegue una riga che cambia da sola. Il campo e'
        uno: prima aspetta il nominativo, poi il numero.
        In testa non c'e' piu' il numero del QSO, che non diceva niente, ma
        come sto andando: piu' i QSO giusti, meno quelli sbagliati, uguale il
        punteggio, cioe' punti per prefissi. E' una richiesta di Gabriele del
        21 settembre 2026.
        """
        punteggio = motore.punteggio
        sbagliati = punteggio.punti_grezzi - punteggio.punti_verificati
        conto = f"+{punteggio.punti_verificati} -{sbagliati} ={punteggio.punteggio_verificato}"
        etichetta = "CALL:" if stadio == "call" else f"{suo_call} 5NN NR:"
        riga = f"{conto} {etichetta} {campo}"
        # Il cursore di sistema va sulla cella del carattere corrente: si
        # stampa la riga intera, poi si torna a colonna zero e si riscrive il
        # solo pezzo che precede il cursore. Niente sequenze ANSI e nessuna
        # parola in piu' a coprire il CW: sul display braille il cursore si
        # legge com'e' abituato a leggerlo in qualunque campo di testo.
        prefisso = riga[: len(riga) - len(campo) + cursore]
        print(f"\r{' ' * 79}\r{riga}\r{prefisso}", end="", flush=True)

    def stato_a_richiesta(adesso):
        """Alt+S: tempo trascorso, QSO, punti, prefissi, punteggio e quanto manca.

        Quanto manca perche' altrimenti non c'era modo di saperlo: la riga di
        stato dice come sto andando, non a che punto sono della sessione.
        """
        punteggio = motore.punteggio
        minuti, secondi = divmod(int(adesso), 60)
        if duration_type == 1:
            manca = f" -{max(0, limit - punteggio.punti_grezzi)} QSO"
        else:
            resta = max(0, int(limit * 60.0 - adesso))
            manca = f" -{resta // 60:d}:{resta % 60:02d}"
        dillo(f"{minuti:02d}:{secondi:02d} QSO {punteggio.punti_grezzi} PT {punteggio.punti_verificati} PFX {len(punteggio.prefissi_verificati)} = {punteggio.punteggio_verificato}{manca}")

    def conferma_in_cw():
        """Una r in CW a ogni valore cambiato, perche' la mano sappia subito che e' arrivato.

        L'annuncio a voce aspetta che la mano si fermi; questo no, ed e' il
        segno che in radio si manda per dire ricevuto. Esce con il tono, la
        velocita' e il volume del momento, quindi dice anche com'e' il valore
        nuovo. Richiesta di Gabriele del 21 settembre 2026.
        """
        suona("r", sync=False, farnsworth=0)

    def annuncia(chiave, riga, adesso):
        """Rimanda l'annuncio di un valore: chi lo cambia in raffica lo sente una volta sola.

        Decisione di Gabriele del 21 settembre 2026. Il valore si sente subito
        nell'audio, perche' la banda e il tono cambiano cio' che arriva: a
        dirlo si fa in tempo quando la mano si ferma.
        L'attesa vale per ogni valore a se': con una sola in comune, chi cambia
        la velocita' e poi il tono perderebbe il primo annuncio, perche' il
        secondo gli prenderebbe il posto.
        """
        annunci[chiave] = (riga, adesso + CONTEST_ATTESA_ANNUNCIO)

    def annunci_maturi(adesso, tutti=False):
        """Dice gli annunci la cui attesa e' scaduta, nell'ordine in cui scadono.

        Con tutti li dice comunque: serve alla chiusura, perche' chi cambia un
        valore e chiude subito dopo non deve restare senza saperlo.
        """
        pronti = sorted((quando, chiave) for chiave, (_, quando) in annunci.items() if tutti or adesso >= quando)
        for _, chiave in pronti:
            dillo(annunci.pop(chiave)[0])

    def dillo(riga):
        """Una riga di servizio in mezzo al contest, al posto della riga di stato.

        Non ridisegna: la riga di stato torna alla prossima battuta, perche'
        la decisione D2 vuole che si riscriva quando si batte un tasto.

        Finisce con un ritorno a capo senza andare a capo davvero, cosi' il
        cursore di sistema resta sulla riga e il display braille la mostra da
        solo: altrimenti bisogna andarla a cercare, e intanto il contest
        corre.
        """
        print(f"\r{' ' * 79}\r{riga}\r", end="", flush=True)

    def trasmetti(messaggi, adesso):
        """Un tasto funzione: il messaggio parte, o si mette in coda se ne sta suonando un altro.

        Accodare e non tagliare e' il gesto di Morse Runner: F5 e poi F7
        mandano il nominativo copiato e poi il punto interrogativo, che e' il
        modo di chiedere la ripetizione. Prima il primo messaggio spariva del
        tutto, e non tagliato a meta': fermandolo, il ciclo non scopriva piu'
        che era finito e il motore non lo raccontava alle stazioni, che quindi
        non sapevano di essere state chiamate.

        Il nominativo si congela adesso, quando il tasto viene premuto: se lo
        leggessimo al momento di suonare, andrebbe in aria un nominativo
        diverso da quello che avevo in mente.
        """
        nominativo = (campo if stadio == "call" else suo_call).strip()
        if ct.Msg.SUO in messaggi and not nominativo:
            # Senza un nominativo nella riga il suo nominativo e' un vuoto: il
            # motore CW rifiuta un messaggio vuoto, e le stazioni sentirebbero
            # chiamare qualcun altro e smetterebbero di rispondere. In
            # radio, del resto, non si risponde a chi non si e' ancora copiato.
            return
        segna_cosa_ho_detto(messaggi, nominativo)
        if ct.IO in suoni:
            coda.append((list(messaggi), nominativo))
            return
        manda(messaggi, nominativo, adesso, accoda=False)

    def segna_cosa_ho_detto(messaggi, nominativo):
        """Tiene il conto di cio' che la stazione ha gia' sentito da me.

        Il suo nominativo, una volta mandato, resta mandato. Il mio scambio
        resta mandato anch'esso, tranne quando torno a ripeterle il
        nominativo: vuol dire che il primo scambio non e' arrivato. In Morse
        Runner lo spegneva qualunque altro messaggio, compreso il punto
        interrogativo, e dopo un ? l'Invio le rimandava lo scambio che lei
        aveva gia' copiato: chiedere il suo numero non vuol dire che lei non
        abbia il mio. Il CQ, il NIL e il QSO B4 chiudono il QSO in corso e
        spengono tutte e due le spie.
        """
        nonlocal suo_mandato, scambio_mandato, nominativo_mandato
        for m in messaggi:
            if m == ct.Msg.SUO:
                suo_mandato, scambio_mandato = True, False
                nominativo_mandato = nominativo
            elif m == ct.Msg.NR:
                scambio_mandato = True
            elif m in (ct.Msg.CQ, ct.Msg.NIL, ct.Msg.B4):
                suo_mandato, scambio_mandato = False, False

    def manda(messaggi, nominativo, adesso, accoda):
        """Mette in aria un messaggio: il primo di una trasmissione o uno della coda.

        Se il motore CW non suona, la trasmissione si dichiara finita subito:
        altrimenti le stazioni resterebbero in ascolto di una voce che non
        arriva mai e il contest si fermerebbe.
        """
        nonlocal fine_mia
        chiudi_i_finiti(adesso)
        zittisci_ricezione()
        richiesta = motore.io_trasmetti(messaggi, adesso, suo_nominativo=nominativo, accoda=accoda)
        if not richiesta.testo.strip():
            motore.io_finito(adesso)
            return
        # Un messaggio accodato parte dopo il silenzio di uno spazio di
        # parola, come fra due parole dello stesso messaggio. Il punto
        # interrogativo no: in radio chi chiede la ripetizione lo attacca
        # all'ultima cosa che ha detto, per fare prima, e DL3XY? si manda
        # come una parola sola. Attaccato vuol dire con il silenzio fra due
        # lettere, non zero, che fonderebbe gli elementi in un carattere che
        # non esiste. Scelta di Gabriele del 23 settembre 2026.
        attaccato = bool(messaggi) and messaggi[0] == ct.Msg.QM
        inizio = 0.0
        if accoda:
            # Il ciclo si accorge della fine del messaggio precedente fino a
            # cinquanta millesimi dopo: quel silenzio c'e' gia' stato, e va
            # tolto, altrimenti il punto interrogativo attaccato arriverebbe
            # a meta' strada fra lo spazio di lettera e quello di parola.
            # L'orologio si legge adesso, non all'inizio del giro: un tasto
            # arriva dopo un'attesa fino a cinquanta millesimi, e il tempo del
            # giro sarebbe vecchio proprio di quel tanto.
            trascorso = max(0.0, time.monotonic() - t0 - fine_mia)
            inizio = max(0.0, buco_fra_pezzi(richiesta.wpm, richiesta.s, not attaccato) - trascorso)
        handle, _rwpm = metti_in_aria(richiesta, inizio)
        if handle is None:
            motore.io_finito(adesso)
            return
        suoni[ct.IO] = handle
        fine_mia = time.monotonic() - t0 + durata_suono(handle)

    def conta_caratteri(testo):
        """I caratteri che mi sono stati mandati, per il tasso di errore per carattere."""
        for ch in testo:
            if ch.isalnum():
                sent_chars_detail_this_session[ch.lower()] = sent_chars_detail_this_session.get(ch.lower(), 0) + 1

    def segna_velocita(rwpm):
        """La velocita' davvero prodotta da questo QSO entra nelle statistiche."""
        nonlocal minwpm, maxwpm, sum_wpm
        minwpm = rwpm if minwpm is None else min(minwpm, rwpm)
        maxwpm = max(maxwpm, rwpm)
        sum_wpm += rwpm

    def chiudi_qso(voce, verifica, verita):
        """Un QSO e' a log: statistiche, errori per carattere e la riga che lo dice.

        La verifica del motore dice dov'e' l'errore: vuota se e' tutto giusto,
        NIL se il nominativo e' sbagliato, NR se il numero, RST se il rapporto.
        I caratteri mandati si contano una volta per QSO, come faceva il
        contest di prima, cosi' le sessioni restano confrontabili nell'archivio
        anche se una stazione ha ripetuto dieci volte.
        """
        nonlocal session_calls, correct_calls, total_calls_correct, total_serials_correct, total_mistakes_calculated
        vero_call, _vero_rst, vero_nr = verita if verita else (voce.nominativo, voce.rst_ricevuto, voce.nr_ricevuto)
        call_ok = verifica != "NIL"
        serial_ok = verifica in ("", "RST")
        session_calls += 1
        if verifica == "":
            correct_calls += 1
        if call_ok:
            total_calls_correct += 1
        if serial_ok:
            total_serials_correct += 1
        rwpm = rwpm_corrente if rwpm_corrente > 0 else float(overall_speed)
        item_details.append({"rwpm": rwpm, "correct": verifica == ""})
        segna_velocita(rwpm)
        conta_caratteri(f"{vero_call} 5NN {vero_nr}")
        if verita and not call_ok:
            total_mistakes_calculated += collect_char_errors(vero_call.lower(), voce.nominativo.lower(), char_error_counts)
        if verita and not serial_ok:
            total_mistakes_calculated += collect_char_errors(str(vero_nr), str(voce.nr_ricevuto), char_error_counts)
        # Il QSO riuscito non si annuncia: i contatori in testa alla riga lo
        # dicono gia', e in radio non c'e' nessuno che te lo conferma. Quello
        # sbagliato si', perche' cosa fosse davvero non lo si saprebbe.
        if verifica:
            riga = f"#{session_calls} {voce.nominativo} {voce.rst_ricevuto} {voce.nr_ricevuto} {verifica}"
            if verita:
                riga += f" = {vero_call} {vero_nr}"
            dillo(riga)

    def durata_finita(adesso):
        """Vero quando il contest ha raggiunto i QSO chiesti o i minuti chiesti.

        I QSO sono quelli a log, non le stazioni viste: contava anche chi se
        ne andava senza essere lavorato, e una sessione da otto QSO finiva
        dopo due o tre. Il conto lo tiene il motore, che sa cosa e' finito nel
        log, cosi' i due mestieri restano separati per sempre.
        """
        if duration_type == 1:
            return motore.punteggio.punti_grezzi >= limit
        return adesso >= limit * 60.0

    t0 = time.monotonic()
    try:
        prepara_fondo()
        trasmetti([ct.Msg.CQ], 0.0)
        riga_di_stato()
        while True:
            adesso = time.monotonic() - t0
            finite = set(da_chiudere)
            da_chiudere.clear()
            for chi, handle in list(suoni.items()):
                if handle.is_playing.is_set():
                    continue
                del suoni[chi]
                attesa_fine.pop(chi, None)
                if chi == ct.IO and coda:
                    # La coda non e' vuota: parte il messaggio seguente e la
                    # trasmissione non si dichiara finita. Le stazioni devono
                    # ricevere l'elenco completo in una volta sola, alla fine
                    # di tutta la coda: una fine per ogni pezzo costerebbe
                    # loro un punto di pazienza a testa, e nel buco fra i due
                    # farebbero in tempo a partire sopra la mia chiamata.
                    messaggi_in_coda, nominativo_in_coda = coda.pop(0)
                    manda(messaggi_in_coda, nominativo_in_coda, adesso, accoda=True)
                    continue
                finite.add(chi)
            for chi, quando in list(attesa_fine.items()):
                if chi not in suoni and adesso >= quando:
                    finite.add(chi)
                    del attesa_fine[chi]
            esito = motore.avanza(adesso, finite)
            richieste = richieste_rimandate + esito.richieste
            eventi = eventi_rimandati + esito.eventi
            richieste_rimandate.clear()
            eventi_rimandati.clear()
            for richiesta in richieste:
                handle, rwpm = metti_in_aria(richiesta, richiesta.ritardo)
                if handle is None:
                    da_chiudere.add(richiesta.stazione)
                    continue
                suoni[richiesta.stazione] = handle
                attesa_fine[richiesta.stazione] = adesso + durata_suono(handle)
                if richiesta.stazione != ct.IO and in_trasmissione():
                    # Nata mentre il mio tasto e' abbassato: prosegue per conto
                    # suo e non si sente, come quelle che zittisci_ricezione
                    # trova gia' in aria. Prima venivano zittite solo quelle,
                    # una volta sola, all'inizio della mia trasmissione: le
                    # stazioni di disturbo, che nascono quando vogliono, mi
                    # partivano sopra a piena voce, misurate quindici volte su
                    # ventuno in mezz'ora. L'istante in cui il loro messaggio
                    # sarebbe finito resta segnato in attesa_fine, quindi i
                    # tempi del contest non si muovono di un millesimo.
                    ferma(richiesta.stazione)
                # Solo le stazioni che si lavorano danno la velocita' del QSO.
                # Le stazioni di disturbo nascono fra trenta e cinquanta parole
                # al minuto a prescindere dalla mia, e con il QRM acceso la riga
                # delle velocita' del rapporto misurava loro invece di chi
                # stavo copiando.
                if rwpm > 0 and richiesta.dx:
                    rwpm_corrente = rwpm
            if not in_trasmissione():
                # Ho smesso di trasmettere: il ricevitore torna in ascolto.
                accendi_fondo()
            for evento in eventi:
                # La verita' viaggia dentro l'evento di log, perche' il motore
                # sa quale stazione ho lavorato meglio di quanto possa saperlo
                # il ciclo, e a fine contest non c'e' nessun altro evento dello
                # stesso giro da cui prenderla. Le rinunce non passano di qui:
                # stanno nel rapporto, contate a parte, e non sono QSO ne'
                # consumano la durata della sessione.
                if evento[0] == "log":
                    chiudi_qso(evento[1], evento[2], evento[3])
            if durata_finita(adesso):
                break
            annunci_maturi(adesso)
            tasto = key(attesa=CONTEST_PASSO_CICLO, alla_scadenza=None)
            if tasto is None:
                continue
            if tasto == "alt-x":
                break
            if tasto == "\x1b":
                # Decisione D4: se sto trasmettendo, Esc zittisce; altrimenti
                # pulisce la riga. Un Esc solo butta via tutta la coda, come
                # fa Morse Runner: chi si accorge di aver premuto il tasto
                # sbagliato vuole il silenzio subito, non il messaggio dopo.
                if ct.IO in suoni:
                    coda.clear()
                    ferma(ct.IO)
                    tagliata = list(motore.io_messaggi)
                    motore.annulla_trasmissione(adesso)
                    if stadio == "nr" and (ct.Msg.SUO in tagliata or ct.Msg.NR in tagliata):
                        # La mia risposta non e' andata in aria: la stazione ha
                        # sentito spazzatura, non sa che stavo rispondendo a lei
                        # e non parlera' piu' finche' non le rimando qualcosa.
                        # La riga torna al nominativo, gia' pieno, cosi' un
                        # Invio lo rimanda; restando sul numero, invece, quel
                        # tasto metteva a log un QSO che la stazione non aveva
                        # mai concluso, e usciva NIL ogni volta. E si sente:
                        # la riga passa da DL3XY 5NN NR: a CALL: DL3XY.
                        campo, stadio, suo_call = suo_call, "call", ""
                        cursore = len(campo)
                        # Il messaggio e' stato tagliato: cio' che c'era dentro
                        # lei non l'ha sentito, e va rimandato.
                        if ct.Msg.SUO in tagliata:
                            suo_mandato = False
                        if ct.Msg.NR in tagliata:
                            scambio_mandato = False
                else:
                    campo, cursore = "", 0
            elif tasto == "alt-w":
                if ct.IO in suoni:
                    coda.clear()
                    ferma(ct.IO)
                    motore.annulla_trasmissione(adesso)
                campo, stadio, suo_call, cursore = "", "call", "", 0
                suo_mandato, scambio_mandato = False, False
            elif tasto == "alt-s":
                stato_a_richiesta(adesso)
            elif tasto == "\r":
                # L'Invio manda soltanto cio' che alla stazione manca, e chiude
                # il QSO appena c'e' tutto, senza mai ripetere cio' che lei ha
                # gia' sentito. Il suo nominativo va sempre insieme al mio
                # scambio, perche' e' il nominativo a dirle che lo scambio e'
                # per lei; se il nominativo gliel'ho gia' dato, per esempio con
                # F5, basta lo scambio.
                nominativo = campo.strip() if stadio == "call" else suo_call
                if nominativo != nominativo_mandato:
                    # Il nominativo nella riga non e' quello a cui ho parlato:
                    # quello che ho detto non vale per lui.
                    suo_mandato, scambio_mandato = False, False
                if not nominativo:
                    # A riga vuota l'Invio e' un CQ.
                    trasmetti([ct.Msg.CQ], adesso)
                elif stadio == "call":
                    suo_call = nominativo
                    campo, stadio, cursore = "", "nr", 0
                    if not suo_mandato:
                        trasmetti([ct.Msg.SUO, ct.Msg.NR], adesso)
                    elif not scambio_mandato:
                        trasmetti([ct.Msg.NR], adesso)
                    # Se le ho gia' detto nominativo e scambio, per esempio
                    # con F5 e F2, l'Invio passa al numero e basta. Prima
                    # mandava un punto interrogativo e la costringeva a
                    # ripetere un numero gia' copiato.
                else:
                    letto = leggi_scambio(campo)
                    messaggi = []
                    if not suo_mandato:
                        messaggi += [ct.Msg.SUO, ct.Msg.NR]
                    elif not scambio_mandato:
                        messaggi.append(ct.Msg.NR)
                    if letto is None:
                        # Le ho gia' detto tutto e non ho il suo scambio: il
                        # punto interrogativo e' il modo di chiederglielo.
                        trasmetti(messaggi or [ct.Msg.QM], adesso)
                    else:
                        motore.registra_qso(adesso, suo_call, letto[1], letto[0])
                        trasmetti([*messaggi, ct.Msg.TU], adesso)
                        campo, stadio, suo_call, cursore = "", "call", "", 0
                        suo_mandato, scambio_mandato = False, False
            elif tasto == "\x08":
                if cursore > 0:
                    campo = campo[: cursore - 1] + campo[cursore:]
                    cursore -= 1
                elif not campo and stadio == "nr":
                    # Cancellato tutto il numero, il Backspace torna al
                    # nominativo e lo rimette nella riga da correggere: e' il
                    # modo di rimediare quando la stazione ci fa capire che
                    # l'avevamo copiato male, senza buttare via il QSO.
                    campo, stadio, suo_call = suo_call, "call", ""
                    cursore = len(campo)
                    # Se il nominativo era sbagliato, chi mi ascoltava non era
                    # lei: tutto quello che ho detto va ridetto.
                    suo_mandato, scambio_mandato = False, False
            elif tasto == "f1":
                trasmetti([ct.Msg.CQ], adesso)
            elif tasto == "f2":
                trasmetti([ct.Msg.NR], adesso)
            elif tasto == "f3":
                trasmetti([ct.Msg.TU], adesso)
            elif tasto == "f4":
                trasmetti([ct.Msg.MIO], adesso)
            elif tasto == "f5":
                trasmetti([ct.Msg.SUO], adesso)
            elif tasto == "f6":
                trasmetti([ct.Msg.B4], adesso)
            elif tasto == "f7":
                trasmetti([ct.Msg.QM], adesso)
            elif tasto == "f8":
                trasmetti([ct.Msg.NIL], adesso)
            elif tasto in ("f10", "pageup", "f9", "pagedown"):
                # Senza tetto si superava il massimo che il motore CW accetta,
                # e da li' in poi non si sentiva piu' niente.
                if tasto in ("f10", "pageup"):
                    overall_speed = min(WPM_MAX, overall_speed + CONTEST_PASSO_WPM)
                else:
                    overall_speed = max(WPM_MIN, overall_speed - CONTEST_PASSO_WPM)
                motore.mio_wpm = overall_speed
                conferma_in_cw()
                annuncia("wpm", _("WPM {valore}").format(valore=overall_speed), adesso)
                # La velocita' e' quella globale e resta dopo il contest: il
                # Farnsworth di k deve seguirla.
                allinea_farnsworth()
            elif tasto in ("alt-f10", "alt-f9"):
                # Il volume sta sui tasti funzione con Alt, accanto a quelli
                # della velocita': e' il quarto valore che si muove durante il
                # contest, e come gli altri conferma in CW e si annuncia dopo.
                passo = CONTEST_PASSO_VOLUME if tasto == "alt-f10" else -CONTEST_PASSO_VOLUME
                overall_volume = max(0, min(100, round(overall_volume * 100) + passo)) / 100.0
                prepara_fondo()
                conferma_in_cw()
                annuncia("volume", _("Volume {valore}").format(valore=round(overall_volume * 100)), adesso)
            elif tasto in ("alt-up", "alt-down"):
                passo = CONTEST_PASSO_PITCH if tasto == "alt-up" else -CONTEST_PASSO_PITCH
                # Gli stessi limiti del comando .h della sezione k: il tono e'
                # quello generale e resta dopo il contest, quindi qui non puo'
                # avere un tetto piu' basso, che lo abbasserebbe in silenzio a
                # chi lo tiene alto.
                overall_pitch = max(PITCH_MIN, min(PITCH_MAX, overall_pitch + passo))
                motore.mio_pitch = overall_pitch
                prepara_fondo()
                conferma_in_cw()
                annuncia("tono", _("Tono {valore}").format(valore=overall_pitch), adesso)
            elif tasto in ("shift-up", "shift-down"):
                # La banda sta su Shift e non su Ctrl con le frecce: in una
                # console di Windows, Ctrl con le frecce fa scorrere il buffer
                # del terminale, e lo screen reader ricomincia a leggere tutto
                # da capo. Shift con le frecce, in CWapu, e' libero: in Morse
                # Runner e' il RIT, che qui non c'e'.
                passo = CONTEST_PASSO_BANDA if tasto == "shift-up" else -CONTEST_PASSO_BANDA
                banda = max(CONTEST_BANDA_MIN, min(CONTEST_BANDA_MAX, banda + passo))
                motore.banda = banda
                prepara_fondo()
                conferma_in_cw()
                annuncia("banda", _("Banda {valore}").format(valore=banda), adesso)
            elif tasto in ("left", "right", "home", "end", "delete"):
                # Il nominativo si corregge dove serve, non solo cancellando
                # dalla coda: sbagliato il terzo carattere di un nominativo
                # lungo costava fino a dieci battute mentre la stazione
                # trasmetteva. Sono i tasti di qualunque editor, e nel contest
                # erano tutti liberi. Non si usa Ctrl con le frecce, che nelle
                # console di Windows fa scorrere il buffer, ne' il tastierino,
                # che con il blocco numerico spento se lo tiene NVDA.
                if tasto == "left":
                    cursore = max(0, cursore - 1)
                elif tasto == "right":
                    cursore = min(len(campo), cursore + 1)
                elif tasto == "home":
                    cursore = 0
                elif tasto == "end":
                    cursore = len(campo)
                else:
                    # Canc toglie il carattere sotto il cursore e lo lascia
                    # dov'e'; il Backspace toglie quello prima e arretra.
                    campo = campo[:cursore] + campo[cursore + 1 :]
            elif len(tasto) == 1 and (tasto.isalnum() or tasto in "/?"):
                campo = campo[:cursore] + tasto.upper() + campo[cursore:]
                cursore += 1
            elif tasto == " " and stadio == "call" and campo.strip():
                # Come nei logger da contest, lo spazio passa al numero senza
                # trasmettere niente. Serve quando la stazione ha gia' dato il
                # suo scambio prima che io rispondessi: si scrive nominativo,
                # spazio, numero, e un Invio solo le manda nominativo, scambio
                # e TU insieme.
                suo_call = campo.strip()
                campo, stadio, cursore = "", "nr", 0
            elif tasto == " " and stadio == "nr":
                # Lo spazio serve soltanto a separare il rapporto dal numero,
                # quando la stazione sbadata ne ha mandato uno diverso da 599.
                campo = campo[:cursore] + " " + campo[cursore:]
                cursore += 1
            else:
                continue
            riga_di_stato()
    finally:
        annunci_maturi(0.0, tutti=True)
        spegni_fondo()
        for chi in list(suoni):
            ferma(chi)
        for evento in motore.chiudi_contest():
            chiudi_qso(evento[1], evento[2], evento[3])
        active_exerctime = dt.datetime.now() - start_time
        print()
        suona("_ + QRT TU E E", sync=True, farnsworth=0)
        # I tasti battuti mentre suonava il saluto non devono finire nel menu.
        while key(attesa=0, alla_scadenza=None) is not None:
            pass

        # --- STATS SAVING ---
        if session_calls == 0 and not motore.punteggio.rinunce:
            # Uscita prima del primo QSO: non c'e' niente da registrare, e una
            # sessione vuota sporcherebbe le medie dell'archivio storico. Se
            # pero' qualcuno mi ha chiamato e se n'e' andato, il rapporto si
            # legge lo stesso: chi era, quanti erano, con che pannello stavo
            # giocando. Su disco non va, perche' l'archivio scarta le sessioni
            # a zero QSO, e le statistiche storiche restano pulite.
            print(_("Contest chiuso prima del primo QSO: niente da salvare."))
            key(_("Premi un tasto per tornare al menu..."))
        else:
            elapsed_total = (dt.datetime.now() - start_time).total_seconds()
            wrong_calls = session_calls - correct_calls
            avg_wpm_calc = sum_wpm / session_calls if session_calls > 0 else 0
            send_char = sum(sent_chars_detail_this_session.values())
            # Il contest ha statistiche e archivio suoi dalla 7.0.5, issue 15.
            stats = app_data["rxing_stats_contest"]
            # Su disco va solo una sessione che ha messo qualcosa a log. Quella
            # fatta di sole rinunce si legge nel rapporto, perche' dice quante
            # occasioni sono sfuggite e con che pannello stavo giocando, ma non
            # entra ne' nell'archivio storico ne' nel conto delle sessioni:
            # sarebbe una media calcolata su niente, e load_settings la
            # scarterebbe comunque al riavvio.
            if session_calls:
                stats["sessions"] += 1
                stats["total_calls"] += session_calls
                stats["total_correct"] += correct_calls
                stats["total_wrong_items"] += wrong_calls
                stats["total_time_seconds"] += elapsed_total
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
                # Campi nuovi del contest rifatto: i rapporti storici gia'
                # scritti non li hanno e chi li legge li ignora.
                "punteggio_grezzo": motore.punteggio.punteggio_grezzo,
                "punteggio_verificato": motore.punteggio.punteggio_verificato,
                "prefissi_verificati": len(motore.punteggio.prefissi_verificati),
                "contest_settings": dict(stati),
            }
            if session_calls:
                historical_data = app_data["historical_rx_data_contest"]
                historical_rx_log = historical_data.get("sessions_log", [])
                historical_rx_log.append(session_data_for_history)
                historical_settings = app_data["historical_rx_settings"]
                g = historical_settings.get("max_sessions_to_keep", HISTORICAL_RX_MAX_SESSIONS_DEFAULT)
                while len(historical_rx_log) > g:
                    # L'archivio si accorciava in silenzio: l'esercizio di
                    # ricezione dice quale sessione esce dalla coda, e il
                    # contest non lo diceva.
                    sessione_uscita = historical_rx_log.pop(0)
                    print(
                        _("Sessione del {data}, durata {durata}s, contenuto {contenuto} caratteri, eliminata dalla coda degli esercizi di {category_name}.").format(
                            data=dt.datetime.fromisoformat(sessione_uscita.get("timestamp_iso", "N/D")).strftime("%Y-%m-%d %H:%M"),
                            durata=int(sessione_uscita.get("duration_seconds", 0)),
                            contenuto=sessione_uscita.get("chars_sent_session", 0),
                            category_name=nome_categoria("contest"),
                        )
                    )
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
            if minwpm is not None:
                # Senza nemmeno un QSO a log non c'e' nessuna velocita' da
                # raccontare: le stazioni che se ne sono andate non entrano piu'
                # nelle statistiche, e una riga di zeri non direbbe niente.
                print(
                    _(
                        "Durante la sessione, la tua velocità minima è stata {minwpm:.2f}, la massima di {maxwpm:.2f}: pari ad una variazione di {range_wpm:.2f} WPM.\n\tLa velocità media di ricezione è di: {average_wpm:.2f} WPM."
                    ).format(minwpm=minwpm, maxwpm=maxwpm, range_wpm=maxwpm - minwpm, average_wpm=avg_wpm_calc)
                )
            # A schermo l'elenco non si stampa, perche' e' rumore che scorre
            # via. L'unica eccezione e' la sessione senza nemmeno un QSO a
            # log: quella nel diario non ci finisce, quindi se non lo
            # dicessimo qui non lo direbbe piu' nessuno.
            for riga in righe_rapporto_contest(motore.punteggio, stati, active_exerctime.total_seconds(), con_rinunce=not session_calls):
                print(riga)
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
            # Il diario racconta le sessioni che hanno prodotto qualcosa. Una
            # fatta di sole rinunce si e' gia' letta a schermo e non ha ne'
            # QSO ne' velocita' da scrivere: finirebbe nel diario come una
            # riga di zeri e di percentuali calcolate su niente.
            if session_calls:
                stampa_completamento_rapporto("contest", send_char)
                duration_str = str(active_exerctime).split(".")[0]
                adesso = dt.datetime.now()
                date_str = adesso.strftime("%Y/%m/%d")
                time_str = adesso.strftime("%H:%M")
                try:
                    with apri_diario() as f:
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
                        for riga in righe_rapporto_contest(motore.punteggio, stati, active_exerctime.total_seconds()):
                            f.write(riga + "\n")
                        if total_mistakes_calculated > 0:
                            f.write(_("Carattere: errori = Wilson Interval") + "\n")
                            for char, errori in sorted(char_error_counts.items(), key=lambda item: (-item[1], item[0])):
                                inviati = sent_chars_detail_this_session.get(char, 0)
                                inf = wilson_score_lower_bound(errori, inviati) * 100
                                sup = wilson_score_upper_bound(errori, inviati) * 100
                                f.write(f"    '{char.upper()}': {errori}/{inviati} [{inf:.1f}% - {sup:.1f}%]\n")
                        f.write(FINE_RECORD_DIARIO)
                except OSError as e:
                    print(_("Diario non scritto: {errore}").format(errore=e))
                # Che diario e archivio siano stati scritti si da' per
                # scontato, issue 18: a schermo arriva solo cio' che va storto.
                print(_("\nSessione {session_number}, durata attiva {duration}.").format(session_number=stats["sessions"], duration=duration_str))
                # I caratteri del contest portano al rapporto storico del
                # contest, come quelli di ogni esercizio portano al suo.
                avanza_rapporto_storico("contest", send_char)
            # Su disco adesso, non solo uscendo. Le impostazioni si salvavano
            # una volta sola, alla fine della sessione di lavoro: chi faceva
            # sette contest in un pomeriggio li aveva tutti e sette nel diario,
            # che scrive subito, e nessuno nell'archivio finche' non chiudeva
            # con q. Un blocco o una mancanza di corrente li cancellava, e il
            # diario restava a raccontare sessioni che l'archivio non aveva.
            save_settings(app_data, annuncia=False)
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

    # Con il Farnsworth impostato l'esercizio si fa e il rapporto si legge,
    # ma sul disco non resta niente: ne' diario, ne' archivio, ne' statistiche,
    # ne' rapporti generati. Deciso da Gabriele il 2026-09-12 per tenere
    # l'archivio confrontabile, vedi la issue 11. Una condizione sola, letta
    # qui, governa tutti i punti che scrivono.
    traccia_su_disco = not farnsworth_impostato()
    if not traccia_su_disco:
        print(_("Farnsworth a {fw}: l'esercizio si fa, ma non lascia tracce su disco.").format(fw=overall_farnsworth))

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
            category_name=nome_categoria(category_key),
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

    # Con il Farnsworth impostato i caratteri non scendono sotto la velocita'
    # piu' bassa a cui il motore lo accetta ancora con i pesi di adesso,
    # nemmeno alla partenza: il minimo della domanda e' quel pavimento, e
    # vale per tutta la sessione perche' pesi e Farnsworth qui non cambiano.
    minimo_wpm = pavimento_ammesso(overall_farnsworth, overall_speed, overall_dashes, overall_spaces, overall_dots)
    overall_speed = dgt(
        prompt=_("Vuoi cambiare la velocità in WPM, da {minimo} a {massimo}? Invio per accettare {wpm}> ").format(minimo=minimo_wpm, massimo=WPM_MAX, wpm=overall_speed),
        kind="i",
        imin=minimo_wpm,
        imax=WPM_MAX,
        default=max(minimo_wpm, overall_speed),
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
    # Lo zero vuol dire infinito e deve stare dentro i limiti dichiarati: prima
    # era un predefinito fuori dal minimo, cioe' una sentinella che dgt lasciava
    # passare per un suo difetto. Vedi la issue 12 di GBUtils.
    how_many_calls = dgt(prompt=_("\nQuanti ne vuoi ricevere? (INVIO per infinito)> "), kind="i", imin=0, imax=1000, default=0)
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
                if not fix_speed and overall_speed > minimo_wpm:
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
        if traccia_su_disco:
            stampa_completamento_rapporto(category_key, send_char)
        if traccia_su_disco:
            nota = dgt(prompt=_("\nNota su questo esercizio: "), kind="s", smin=0, smax=512)
            adesso = dt.datetime.now()
            date_str = adesso.strftime("%Y/%m/%d")
            time_str = adesso.strftime("%H:%M")
            try:
                with apri_diario() as f:
                    f.write(_("\nEsercizio di ricezione #{sessions} eseguito il {date} alle {time} minuti:\n").format(sessions=numero_sessione, date=date_str, time=time_str))
                    f.write(
                        _("In questa sessione #{sessions}, ti ho inviato {calls} {kindstring} e ne hai ricevuti {callsget_len}: {percentage:.1f}%").format(
                            sessions=numero_sessione, calls=total_sent_processed, kindstring=kindstring, callsget_len=len(callsget), percentage=percentage_correct
                        )
                        + "\n"
                    )
                    f.write(
                        _("\t{first_shot} di questi sono stati ricevuti al primo ascolto: {first_shot_percentage:.1f}%").format(
                            first_shot=first_shot_correct, first_shot_percentage=first_shot_percentage
                        )
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
            except OSError as e:
                print(_("Diario non scritto: {errore}").format(errore=e))
        else:
            print(_("Farnsworth impostato: rapporto letto, ma niente nel diario."))
    else:
        print(_("Hai ricevuto troppo pochi {kindstring} per generare statistiche consistenti.").format(kindstring=kindstring))
    duration_str = str(active_exerctime).split(".")[0]
    # Senza nemmeno un item non c'e' niente da archiviare: una sessione a
    # zero entrava nel contatore e nel registro, e alla ripulitura del
    # riavvio usciva dal registro lasciando il contatore piu' alto. Sono i
    # tre buchi del dicembre 2025. Nel contest questo guard c'e' dal 22
    # settembre, qui mancava.
    if traccia_su_disco and callssend:
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
                    category_name=nome_categoria(category_key),
                )
            )

        current_historical_data["sessions_log"] = historical_rx_log
        avanza_rapporto_storico(category_key, send_char)

        print(_("\nSessione {session_number}, durata attiva {duration}.").format(session_number=current_rx_stats["sessions"], duration=duration_str))
        # La lunghezza si legge dopo la potatura, altrimenti a limite raggiunto
        # l'applicazione annunciava una sessione di troppo e uno spazio negativo.
        x = len(historical_rx_log)
        print(
            _("L'archivio ora contiene {x} sessioni salvate per gli esercizi di {category_name}, ancora {g_minus_x} al raggiungimento del limite stabilito.").format(
                x=x, g_minus_x=max(0, g - x), category_name=nome_categoria(category_key)
            )
        )
    else:
        print(_("\nDurata attiva {duration}: sessione non salvata, con il Farnsworth impostato non entra nell'archivio ne' nelle statistiche.").format(duration=duration_str))
    # Su disco adesso, non solo uscendo, e in silenzio: vale qui come nel
    # contest.
    save_settings(app_data, annuncia=False)
    # La pausa e' informazione di rapporto, non di salvataggio: si legge in
    # tutti e due i casi.
    if total_pause_time.total_seconds() > 0:
        pause_str = str(total_pause_time).split(".")[0]
        print(_("\t(Tempo totale in pausa rilevato: {pause_time})").format(pause_time=pause_str))
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


def stampa_completamento_rapporto(category_key, caratteri):
    """Dice quanti caratteri mancano al prossimo rapporto storico, contando anche quelli della sessione appena finita."""
    report_interval = app_data.get("historical_rx_settings", {}).get("report_interval", HISTORICAL_RX_REPORT_INTERVAL)
    if report_interval <= 0:
        print(_("La generazione automatica dei report è disabilitata."))
        return
    chars_done = app_data[f"historical_rx_data_{category_key}"].get("chars_since_last_report", 0) + caratteri
    percentage_done = chars_done / report_interval * 100
    chars_missing = max(0, report_interval - chars_done)
    print(
        _("Completamento sezione corrente:\n+{s} -> ({x} / {y}) = {z}%, ne mancano {w} alla prossima generazione.").format(
            s=caratteri, x=chars_done, y=report_interval, z=f"{percentage_done:.2f}", w=chars_missing
        )
    )


def avanza_rapporto_storico(category_key, caratteri):
    """Conta i caratteri della sessione appena archiviata e, passata la soglia di .x, genera il rapporto storico.

    La usano l'esercizio di ricezione e il contest, ciascuno sulla propria
    categoria. Il registro deve gia' contenere la sessione: il rapporto
    prende dalla coda tante sessioni quante ne servono a coprire i
    caratteri contati, e l'eccedenza passa al rapporto seguente.
    """
    dati = app_data[f"historical_rx_data_{category_key}"]
    report_interval = app_data.get("historical_rx_settings", {}).get("report_interval", HISTORICAL_RX_REPORT_INTERVAL)
    dati["chars_since_last_report"] = dati.get("chars_since_last_report", 0) + caratteri
    if report_interval <= 0 or dati["chars_since_last_report"] < report_interval:
        return
    print(_("Generazione report storico in corso..."))
    sessions_log = dati.get("sessions_log", [])
    chars_to_account_for = dati["chars_since_last_report"]
    sessions_for_this_report = []
    accumulated_chars = 0
    for session in reversed(sessions_log):
        sessions_for_this_report.insert(0, session)
        accumulated_chars += session.get("chars_sent_session", 0)
        if accumulated_chars >= chars_to_account_for:
            break
    new_report_aggregates = generate_historical_rx_report(sessions_for_this_report, category_key)
    if new_report_aggregates:
        historical_reports = dati.get("historical_reports", [])
        historical_reports.append(new_report_aggregates)
        dati["historical_reports"] = historical_reports
    overshoot = accumulated_chars - report_interval
    dati["chars_since_last_report"] = max(0, overshoot)


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

    cat_display_name = nome_categoria(category_key)

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
            f.write(_("<h1>CWapu - Report Statistiche Storiche Esercizi Rx ({cat})</h1>\n").format(cat=cat_display_name))
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
        if perform_update(dl_url, "CWapu"):
            print(_("Aggiornamento pronto. CWapu si chiudera' per l'installazione..."))
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
    import pathlib
    import webbrowser

    print(_("Apro la guida nel browser: {percorso}").format(percorso=percorso))
    try:
        # as_uri costruisce l'indirizzo giusto su ogni sistema: componendolo a
        # mano, su Mac e Linux un percorso che comincia con la barra produceva
        # quattro barre di fila e il browser non trovava niente.
        aperta = webbrowser.open(pathlib.Path(percorso).as_uri())
    except (OSError, ValueError) as e:
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

    for category_key in CATEGORIE_ARCHIVIO:
        log_sessioni = app_data[f"historical_rx_data_{category_key}"]["sessions_log"]
        if not log_sessioni:
            continue
        _clear_screen_ansi()
        print(_("Report Timeline per {category_name}").format(category_name=nome_categoria(category_key)))
        report_con_header = timeline.genera_report_temporale_completo(log_sessioni, _, app_language)
        chiusura = _("Fine del report. Bye da CWapu {version}").format(version=VERSION)
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
    global overall_volume, overall_ms, overall_fs, overall_wave, overall_farnsworth
    global overall_uscita_interfaccia, overall_uscita_dispositivo, overall_api, overall_contest_call
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
    # La coppia salvata potrebbe essere nata incoerente: il Farnsworth non
    # supera mai la velocita' dei caratteri.
    overall_farnsworth = limita_farnsworth(overall_settings.get("farnsworth", 0), overall_speed)
    overall_uscita_interfaccia = overall_settings.get("uscita_interfaccia", "") or ""
    overall_uscita_dispositivo = overall_settings.get("uscita_dispositivo", "") or ""
    overall_contest_call = (overall_settings.get("contest_call", "") or "").strip().upper()
    overall_api = risolvi_uscita_audio(overall_uscita_interfaccia, overall_uscita_dispositivo)
    # La frequenza di .sr e' quella con cui il mixer apre la scheda: il
    # mixer condiviso di GBUtils parte a 44100 e ricampionerebbe tutto.
    Acusticator.setup(fs=SAMPLE_RATES[overall_fs])
    _clear_screen_ansi()
    print(
        _("\nCWapu - VERSIONE: {version} DEL {data} DI GABRY - IZ4APU.\n\tUtilità per il tuo CW.\n\t\tLancio app: {count}. Scrivi 'm' per il menu.").format(
            version=VERSION, data=RELEASE_DATE, count=launch_count
        )
    )
    print(
        _("\tWPM: {overall_speed}, Hz: {overall_pitch}, Volume: {}\n\tL/S/P: {overall_dashes}/{overall_spaces}/{overall_dots}, FW: {fw}, Wave: {}, MS: {overall_ms}, FS: {}.").format(
            int(overall_volume * 100),
            WAVE_TYPES[overall_wave - 1],
            SAMPLE_RATES[overall_fs],
            overall_speed=overall_speed,
            overall_pitch=overall_pitch,
            overall_dashes=overall_dashes,
            overall_spaces=overall_spaces,
            overall_dots=overall_dots,
            overall_ms=overall_ms,
            fw=overall_farnsworth or _("no"),
        )
    )
    print(_("\tUscita audio: {uscita}.").format(uscita=descrizione_uscita_corrente()))
    if overall_uscita_interfaccia and overall_api is None:
        print(_("Uscita audio salvata non trovata oggi: lascio scegliere a CWapu, e la riprovo al prossimo avvio."))
    # Dopo il riepilogo, cosi' se il Farnsworth salvato non regge i pesi
    # salvati l'utente legge il valore che aveva e poi cosa e' cambiato.
    allinea_farnsworth()
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
            # Appunti fatti di soli simboli restano vuoti dopo la pulizia, e
            # una stringa vuota il motore la rifiuta: vale come appunti vuoti.
            testo_appunti = StringCleaning(pyperclip.paste() or "").strip()
            suona(testo_appunti if testo_appunti else _("vuoti"))
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
            "farnsworth": overall_farnsworth,
            "uscita_interfaccia": overall_uscita_interfaccia,
            "uscita_dispositivo": overall_uscita_dispositivo,
            "contest_call": overall_contest_call,
        }
    )
    save_settings(app_data)
    print(_("hpe cuagn - 73 de IZ4APU - Gabe in Bologna, JN54pl."))
    # Dalla V168 di GBUtils sync aspetta che l'ultima e sia uscita dalle
    # casse, non solo dal mixer: l'applicazione puo' chiudersi subito dopo.
    suona("bk hpe cuagn - 73 de iz4apu tu e e", sync=True)
    _clear_screen_ansi()
    Donazione(lang=app_language)


if __name__ == "__main__":
    main()
