# CWAPUDEV - Utility per il CW, di Gabry, IZ4APU
# Data concepimento 21/12/2022.
# GitHub publishing on july 2nd, 2024.

import sys, random, json, string, pyperclip, re, difflib, os, traceback
import datetime as dt
from pynput import keyboard
from GBUtils import key, dgt, menu, CWzator, Donazione, polipo
from time import localtime as lt
from timeline import wilson_score_lower_bound, wilson_score_upper_bound
import timeline
# installazione percorsi relativi e i18n
def resource_path(relative_path):
    """
    Restituisce il percorso assoluto a una risorsa, funzionante sia in sviluppo
    che per un eseguibile compilato con PyInstaller (anche con la cartella _internal).
    """
    try:
        # PyInstaller crea una cartella temporanea e ci salva il percorso in _MEIPASS
        # Questo è il percorso base per le risorse quando l'app è "congelata"
        base_path = sys._MEIPASS
    except Exception:
        # Se _MEIPASS non esiste, non siamo in un eseguibile PyInstaller
        # o siamo in una build onedir, il percorso base è la cartella dello script
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_user_data_path():
    """Restituisce un percorso scrivibile per i dati utente."""
    if getattr(sys, 'frozen', False):
        # Percorso dell'eseguibile
        return os.path.dirname(sys.executable)
    else:
        # Cartella dello script
        return os.getcwd()

app_language, _ = polipo(source_language="it")

#QC Costanti
VERSION = '4.7.4, 2025-12-17)'
RX_ITEM_TIMEOUT_SECONDS = 30 # Tempo massimo per item prima di considerarlo una pausa
overall_settings_changed = False
SAMPLE_RATES = [8000, 11025, 16000, 22050, 32000, 44100, 48000, 88200, 96000, 176400, 192000, 384000]
WAVE_TYPES = ['sine', 'square', 'triangle', 'sawtooth']
USER_DATA_PATH = get_user_data_path()
SETTINGS_FILE = os.path.join(USER_DATA_PATH, 'cwapu_settings.json')
RX_SWITCHER_ITEMS = [
    {'id': '1', 'key_state': _('parole'), 'label_key': 'menu_rx_switcher_parole', 'is_exclusive': False, 'category_group': 'WORDS'},
    {'id': '2', 'key_state': _('lettere'), 'label_key': 'menu_rx_switcher_lettere', 'is_exclusive': False, 'category_group': 'CHARS'},
    {'id': '3', 'key_state': _('numeri'), 'label_key': 'menu_rx_switcher_numeri', 'is_exclusive': False, 'category_group': 'CHARS'},
    {'id': '4', 'key_state': _('lettere e numeri'), 'label_key': 'menu_rx_switcher_lettere_numeri', 'is_exclusive': False, 'category_group': 'CHARS'},
    {'id': '5', 'key_state': _('simboli'), 'label_key': 'menu_rx_switcher_simboli', 'is_exclusive': False, 'category_group': 'CHARS'},
    {'id': '6', 'key_state': _('custom'), 'label_key': 'menu_rx_switcher_custom', 'is_exclusive': True, 'category_group': 'CUSTOM'},
    {'id': '7', 'key_state': 'qrz', 'label_key': 'menu_rx_switcher_qrz', 'is_exclusive': False, 'category_group': 'QRZ'},
    {'id': '8', 'key_state': 'contest', 'label_key': 'menu_rx_switcher_contest', 'is_exclusive': True, 'category_group': 'QRZ'}
]
HISTORICAL_RX_MAX_SESSIONS_DEFAULT = 730
HISTORICAL_RX_REPORT_INTERVAL = 3500

# Caricamento database QRZ reali (MASTER.SCP)
REAL_CALLS_POOL = []
MASTER_SCP_PATH = resource_path('MASTER.SCP')

def load_master_scp():
    global REAL_CALLS_POOL
    if not os.path.exists(MASTER_SCP_PATH):
        return
    try:
        with open(MASTER_SCP_PATH, 'r') as f:
            lines = f.readlines()
        calls = [x.strip() for x in lines if not x.startswith('#')]
        REAL_CALLS_POOL = sorted(list(set(calls)))
    except Exception:
        pass

load_master_scp()

VALID_MORSE_CHARS_FOR_CUSTOM_SET = {k for k in CWzator(msg=-1) if k != ' ' and k.isprintable()}
LETTERE_MORSE_POOL = {k for k in VALID_MORSE_CHARS_FOR_CUSTOM_SET if k in set(string.ascii_lowercase)}
NUMERI_MORSE_POOL = {k for k in VALID_MORSE_CHARS_FOR_CUSTOM_SET if k in set(string.digits)}
SIMBOLI_MORSE_POOL = VALID_MORSE_CHARS_FOR_CUSTOM_SET - LETTERE_MORSE_POOL - NUMERI_MORSE_POOL
DEFAULT_DATA = {
    'app_info': {
        'launch_count': 0},
        'overall_settings': {'app_language': 'en',
                            'speed': 18,
                            'pitch': 550,
                            'dashes': 30,
                            'spaces': 50,
                            'dots': 50,
                            'volume': 0.5,
                            'ms': 1,
                            'fs_index': 5,
                            'wave_index': 1},
                        'rxing_stats_words': {
                            'total_calls': 0,
                            'sessions': 0,
                            'total_correct': 0,
                            'total_wrong_items': 0,
                            'total_time_seconds': 0.0},
                        'rxing_stats_chars': {
                            'total_calls': 0,
                            'sessions': 0,
                            'total_correct': 0,
                            'total_wrong_items': 0,
                            'total_time_seconds': 0.0},
                        'rxing_stats_qrz': {
                            'total_calls': 0,
                            'sessions': 0,
                            'total_correct': 0,
                            'total_wrong_items': 0,
                            'total_time_seconds': 0.0},
                        'counting_stats': {
                            'exercise_number': 1},
                        'rx_menu_switcher_states': {
                            'parole': True,
                            'lettere': False,
                            'numeri': False,
                            'lettere e numeri': False,
                            'simboli': False,
                            'qrz': False,
                            'custom': False,
                            'parole_filter_min': 3,
                            'parole_filter_max': 7,
                            'custom_set_string': ''},
                        'historical_rx_settings': {
                            'max_sessions_to_keep': HISTORICAL_RX_MAX_SESSIONS_DEFAULT,
                            'report_interval': HISTORICAL_RX_REPORT_INTERVAL,
                            },
                        'historical_rx_data_words': {
                            'chars_since_last_report': 0,
                            'sessions_log': [],
                            'historical_reports': []},
                        'historical_rx_data_chars': {
                            'chars_since_last_report': 0,
                            'sessions_log': [],
                            'historical_reports': []},
                        'historical_rx_data_qrz': {
                            'chars_since_last_report': 0,
                            'sessions_log': [],
                            'historical_reports': []}}
MDL = {'a0a': 4, 'a0aa': 6, 'a0aaa': 15, 'aa0a': 6, 'aa0aa': 18, 'aa0aaa': 36, '0a0a': 2, '0a0aa': 2, '0a0aaa': 2, 'a00a': 3, 'a00aa': 3, 'a00aaa': 4}
words = []
app_data = {}

def _clear_screen_ansi():
    """Pulisce lo schermo usando ANSI e posiziona il cursore in alto a sinistra."""
    sys.stdout.write('\x1b[2J')
    sys.stdout.write('\x1b[H')
    sys.stdout.flush()

def genera_singolo_item_esercizio_misto(active_switcher_states, group_length_for_generated, custom_set_active_string, parole_filtrate_list):
    global overall_speed
    active_and_usable_kinds = []
    if active_switcher_states.get('parole') and parole_filtrate_list:
        active_and_usable_kinds.append('parole')
    if active_switcher_states.get('lettere'):
        active_and_usable_kinds.append('lettere')
    if active_switcher_states.get('numeri'):
        active_and_usable_kinds.append('numeri')
    if active_switcher_states.get('lettere e numeri'):
        active_and_usable_kinds.append('lettere e numeri')
    if active_switcher_states.get('simboli'):
        active_and_usable_kinds.append('simboli')
    if active_switcher_states.get('qrz'):
        active_and_usable_kinds.append('qrz')
    if active_switcher_states.get('custom') and custom_set_active_string and (len(custom_set_active_string) >= 2):
        active_and_usable_kinds.append('custom')
    if not active_and_usable_kinds:
        return 'ERROR_NO_VALID_TYPES'
    chosen_kind = random.choice(active_and_usable_kinds)
    item_generato = ''
    if chosen_kind == 'parole':
        item_generato = random.choice(parole_filtrate_list)
    elif chosen_kind == 'qrz':
        random_mdl_key_list = random.choices(list(MDL.keys()), weights=list(MDL.values()), k=1)
        item_generato = Mkdqrz(random_mdl_key_list)
    elif chosen_kind == 'custom':
        item_generato = GeneratingGroup(kind='4', length=group_length_for_generated, wpm=overall_speed, customized_set_param=custom_set_active_string)
    elif chosen_kind == 'lettere':
        item_generato = GeneratingGroup(kind='1', length=group_length_for_generated, wpm=overall_speed)
    elif chosen_kind == 'numeri':
        item_generato = GeneratingGroup(kind='2', length=group_length_for_generated, wpm=overall_speed)
    elif chosen_kind == 'lettere e numeri':
        item_generato = GeneratingGroup(kind='3', length=group_length_for_generated, wpm=overall_speed)
    elif chosen_kind == 'simboli':
        item_generato = GeneratingGroup(kind='S', length=group_length_for_generated, wpm=overall_speed)
    return item_generato.lower()

def seleziona_modalita_rx():
    global app_data, app_language, overall_settings_changed, words, overall_speed
    global overall_pitch, overall_dashes, overall_spaces, overall_dots, overall_volume, overall_ms, overall_fs, overall_wave
    global SAMPLE_RATES, WAVE_TYPES
    global HISTORICAL_RX_MAX_SESSIONS_DEFAULT, HISTORICAL_RX_REPORT_INTERVAL
    global DEFAULT_DATA
    global RX_SWITCHER_ITEMS
    global VALID_MORSE_CHARS_FOR_CUSTOM_SET
    switcher_settings_key = 'rx_menu_switcher_states'
    if switcher_settings_key not in app_data:
        app_data[switcher_settings_key] = DEFAULT_DATA[switcher_settings_key].copy()
    current_switcher_states = app_data[switcher_settings_key].copy()
    parole_filtrate_sessione = None
    custom_set_string_sessione = current_switcher_states.get('custom_set_string', '')
    if current_switcher_states.get('parole'):
        min_len = current_switcher_states.get('parole_filter_min', 0)
        max_len = current_switcher_states.get('parole_filter_max', 0)
        if min_len > 0 and max_len > 0 and (min_len <= max_len):
            parole_filtrate_sessione = [w for w in words if len(w) >= min_len and len(w) <= max_len]
            if not parole_filtrate_sessione:
                current_switcher_states['parole'] = False
        else:
            current_switcher_states['parole'] = False
    if current_switcher_states.get('custom') and (not custom_set_string_sessione):
        current_switcher_states['custom'] = False
    MENU_BASE_ROW = 3
    user_message_line_row = MENU_BASE_ROW + len(RX_SWITCHER_ITEMS) + 1
    prompt_actual_line_row = MENU_BASE_ROW + len(RX_SWITCHER_ITEMS) + 2

    def _display_single_switcher_line(index, is_on_state):
        item_config = RX_SWITCHER_ITEMS[index]
        riga_da_scrivere = MENU_BASE_ROW + index
        _move_cursor(riga_da_scrivere, 1)
        label_text_trans = item_config['key_state']
        status_marker = '<X>' if is_on_state else '< >'
        status_text_trans = _('ATTIVATO') if is_on_state else _('disattivato')
        display_label_cased = label_text_trans.upper() if is_on_state else label_text_trans.lower()
        line_output = _('{}. {display_label_cased} {status_marker} {status_text_trans}').format(item_config['id'], display_label_cased=display_label_cased, status_marker=status_marker, status_text_trans=status_text_trans)
        sys.stdout.write(line_output)
        _clear_line_from_cursor()
        sys.stdout.flush()
    def _redraw_menu_interface_for_key_prompt(current_states_dict, message_for_user=''):
        _move_cursor(MENU_BASE_ROW - 1, 1)
        sys.stdout.write(_('Esercizi Rx - Seleziona Tipi (Invio per iniziare):'))
        _clear_line_from_cursor()
        print()
        for idx_redraw, item_config_redraw in enumerate(RX_SWITCHER_ITEMS):
            _display_single_switcher_line(idx_redraw, current_states_dict[item_config_redraw['key_state']])
        _move_cursor(user_message_line_row, 1)
        if message_for_user:
            sys.stdout.write(message_for_user)
            _clear_line_from_cursor()
        else:
            _clear_line_from_cursor()
        status_display_parts = []
        for item_cfg_key_prompt in RX_SWITCHER_ITEMS:
            is_on_key_prompt = current_states_dict.get(item_cfg_key_prompt['key_state'], False)
            status_display_parts.append(_('[{}]').format(item_cfg_key_prompt['id']) if is_on_key_prompt else _('<{}>').format(item_cfg_key_prompt['id']))
        _move_cursor(prompt_actual_line_row, 1)
        _clear_line_from_cursor()
        sys.stdout.flush()
        return ' '.join(status_display_parts) + ': '
    user_message_content = ''
    while True:
        prompt_string = _redraw_menu_interface_for_key_prompt(current_switcher_states, user_message_content)
        user_message_content = ''
        scelta = key(prompt=prompt_string)
        if not scelta or scelta == '\r':
            active_switches_final = [item['key_state'] for item in RX_SWITCHER_ITEMS if current_switcher_states.get(item['key_state'])]
            if not active_switches_final:
                user_message_content = _('Nessuna modalità di esercizio selezionata! Attiva almeno uno switcher.')
                CWzator(msg='?', wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
                continue
            if current_switcher_states.get('parole') and (not parole_filtrate_sessione):
                user_message_content = _("Errore: 'Parole' attivo ma il filtro non è impostato o non produce risultati. Usa '.t #-#'.")
                CWzator(msg='?', wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
                continue
            if current_switcher_states.get('custom') and (not custom_set_string_sessione or len(custom_set_string_sessione) < 2):
                user_message_content = _('Errore: il set personalizzato non è valido o è vuoto. Controlla le impostazioni.')
                CWzator(msg='?', wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
                continue
            group_len_val_final = 0
            ask_for_length = False
            if current_switcher_states.get('lettere') or current_switcher_states.get('numeri') or current_switcher_states.get('custom') or current_switcher_states.get('lettere e numeri') or current_switcher_states.get('simboli'):
                ask_for_length = True
            if ask_for_length:
                _move_cursor(prompt_actual_line_row + 1, 1)
                prompt_len_text_final = _('Lunghezza gruppi (1-7 per Lettere/Numeri/Simboli/Custom):')
                sys.stdout.write(prompt_len_text_final)
                _clear_line_from_cursor()
                sys.stdout.flush()
                _move_cursor(prompt_actual_line_row + 1, len(prompt_len_text_final) + 1)
                len_str_final = input()
                if len_str_final.isdigit() and 1 <= int(len_str_final) <= 7:
                    group_len_val_final = int(len_str_final)
                else:
                    user_message_content = _('Lunghezza non valida. Inserire un numero da 1 a 7.')
                    CWzator(msg='?', wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
                    continue
            app_data[switcher_settings_key].update(current_switcher_states)
            overall_settings_changed = True
            for i_clean_final in range(len(RX_SWITCHER_ITEMS) + 4):
                _move_cursor(MENU_BASE_ROW - 1 + i_clean_final, 1)
                _clear_line_from_cursor()
            _move_cursor(MENU_BASE_ROW, 1)
            return {'active_switcher_states': current_switcher_states, 'parole_filtrate_list': parole_filtrate_sessione if current_switcher_states.get('parole') else None, 'custom_set_string_active': custom_set_string_sessione if current_switcher_states.get('custom') else None, 'group_length_for_generated': group_len_val_final}
        elif scelta.isdigit() and '1' <= scelta <= str(len(RX_SWITCHER_ITEMS)):
            chosen_idx = int(scelta) - 1
            item_config_toggled = RX_SWITCHER_ITEMS[chosen_idx]
            item_key_toggle_loop = item_config_toggled['key_state']
            
            # Toggle dello stato
            current_switcher_states[item_key_toggle_loop] = not current_switcher_states[item_key_toggle_loop]
            is_now_active = current_switcher_states[item_key_toggle_loop]

            # Logica di esclusione mutua basata su Category Group
            if is_now_active:
                my_group = item_config_toggled.get('category_group')
                if my_group:
                    for other_item in RX_SWITCHER_ITEMS:
                        # Se l'altro item appartiene a un gruppo DIVERSO, spegnilo.
                        # Gli item dello STESSO gruppo (es. lettere e numeri) possono coesistere.
                        if other_item['key_state'] != item_key_toggle_loop and other_item.get('category_group') != my_group:
                            current_switcher_states[other_item['key_state']] = False

            if is_now_active:
                if item_key_toggle_loop == 'parole':
                    min_len_saved_loop = current_switcher_states.get('parole_filter_min', 0)
                    max_len_saved_loop = current_switcher_states.get('parole_filter_max', 0)
                    if not (min_len_saved_loop > 0 and max_len_saved_loop > 0 and (min_len_saved_loop <= max_len_saved_loop)):
                        user_message_content = _("Filtro parole non impostato/valido. Usa il comando '.t #-#' nelle Impostazioni (k). Switcher 'Parole' disattivato.")
                        current_switcher_states['parole'] = False
                        parole_filtrate_sessione = None
                    else:
                        parole_filtrate_sessione = [w for w in words if len(w) >= min_len_saved_loop and len(w) <= max_len_saved_loop]
                        if not parole_filtrate_sessione:
                            user_message_content = _("Filtro parole caricato dalle impostazioni non ha prodotto risultati. Switcher 'Parole' disattivato.")
                            current_switcher_states['parole'] = False
                        else:
                            user_message_content = _('Filtro parole applicato dalle impostazioni ({count} parole).').format(count=len(parole_filtrate_sessione))
                elif item_key_toggle_loop == 'custom':
                    if not custom_set_string_sessione or len(custom_set_string_sessione) < 2:
                        for i_clean_cs in range(len(RX_SWITCHER_ITEMS) + 4):
                            _move_cursor(MENU_BASE_ROW - 1 + i_clean_cs, 1)
                            _clear_line_from_cursor()
                        _move_cursor(1, 1)
                        sys.stdout.write(_('Avvio configurazione gruppo personalizzato...') + '\n\n')
                        sys.stdout.flush()
                        custom_set_string_nuovo = CustomSet(overall_speed)
                        if len(custom_set_string_nuovo) >= 2:
                            custom_set_string_sessione = custom_set_string_nuovo
                            current_switcher_states['custom_set_string'] = custom_set_string_nuovo
                        else:
                            user_message_content = _("Gruppo Custom non creato o non valido. Switcher 'Custom' disattivato.")
                            current_switcher_states['custom'] = False
                            custom_set_string_sessione = ''
                            current_switcher_states['custom_set_string'] = ''
                    else:
                        user_message_content = _('Gruppo Custom caricato dalle impostazioni: [{set_string}]').format(set_string=custom_set_string_sessione)
            pass
        else:
            user_message_content = _('Scelta non valida.')
            CWzator(msg='?', wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
    return None

def _move_cursor(riga, colonna):
    """Muove il cursore alla riga e colonna specificata (1-based)."""
    sys.stdout.write(_('\x1b[{riga};{colonna}H').format(riga=riga, colonna=colonna))

def _clear_line_from_cursor():
    """Pulisce la linea dalla posizione attuale del cursore fino alla fine."""
    sys.stdout.write('\x1b[K')

def crea_report_grafico(current_aggregates, previous_aggregates, g_val, x_val, num_sessions_in_report, output_filename, lang='en'):
    """
	Crea un report grafico delle statistiche storiche e lo salva come immagine.
	"""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print(_('matplotlib non trovato.'))
        return
    except Exception as e_import:
        print(_("Errore durante l'importazione di matplotlib. Assicurati che sia installato correttamente.").format(error=str(e_import)))
        return
    plt.style.use('dark_background')
    fig_width_inches = 10
    fig_height_inches = 16
    text_color = 'white'
    color_error_very_high = '#B22222'
    color_error_high = '#FF4136'
    color_warning = '#FF851B'
    color_neutral = '#FFDC00'
    color_good = '#2ECC40'
    color_excellent = '#7FDBFF'
    fig = plt.figure(figsize=(fig_width_inches, fig_height_inches))
    fig.patch.set_facecolor('#222222')
    y_cursor = 0.98
    line_height_fig = 0.03
    section_spacing_fig = 0.04
    title_text = _('CWAPU - Report Statistiche Storiche Esercizi Rx')
    fig.text(0.5, y_cursor, title_text, color=text_color, ha='center', va='top', fontsize=16, weight='bold')
    y_cursor -= line_height_fig * 1.5
    subtitle_text = _('Statistiche basate su {count} esercizi').format(count=num_sessions_in_report) + _(' (G={g_val}, X={x_val})').format(g_val=g_val, x_val=x_val)
    fig.text(0.5, y_cursor, subtitle_text, color=text_color, ha='center', va='top', fontsize=12)
    y_cursor -= line_height_fig
    generation_time_text = _('Report generato il: {}').format(dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    fig.text(0.5, y_cursor, generation_time_text, color=text_color, ha='center', va='top', fontsize=10, style='italic')
    y_cursor -= section_spacing_fig * 1.5

    def get_delta_color_and_symbol(delta_value, higher_is_better=True, tolerance=0.01):
        symbol = ''
        color_to_use = color_neutral
        if higher_is_better:
            if delta_value > tolerance:
                color_to_use = color_good
                symbol = '▲'
            elif delta_value < -tolerance:
                color_to_use = color_error_high
                symbol = '▼'
            else:
                symbol = '~'
        elif delta_value < -tolerance:
            color_to_use = color_good
            symbol = '▼'
        elif delta_value > tolerance:
            color_to_use = color_error_high
            symbol = '▲'
        else:
            symbol = '~'
        return (color_to_use, symbol)
    fig.text(0.5, y_cursor, _('Statistiche Velocità Complessive'), color=color_excellent, ha='center', va='top', fontsize=14, weight='bold')
    y_cursor -= line_height_fig * 2.0
    wpm_metrics_data = [
        {
            'label_key': _('WPM Min'), 
            'curr': current_aggregates['wpm_min_overall'], 
            'prev': previous_aggregates['wpm_min_overall'] if previous_aggregates else None, 
            'higher_better': True
        }, 
        {
            'label_key': _('WPM Media'), 
            'curr': current_aggregates['wpm_avg_of_session_avgs'], 
            'prev': previous_aggregates['wpm_avg_of_session_avgs'] if previous_aggregates else None, 
            'higher_better': True
        }, 
        {
            'label_key': _('WPM Max'), 
            'curr': current_aggregates['wpm_max_overall'], 
            'prev': previous_aggregates['wpm_max_overall'] if previous_aggregates else None, 
            'higher_better': True
        }
    ]
    num_wpm_metrics = len(wpm_metrics_data)
    height_per_wpm_metric_group_fig = 0.07
    ax_wpm_needed_height_fig = height_per_wpm_metric_group_fig * num_wpm_metrics
    ax_wpm_left = 0.2
    ax_wpm_width = 0.55
    ax_wpm_bottom = y_cursor - ax_wpm_needed_height_fig
    ax_variation_text_left = ax_wpm_left + ax_wpm_width + 0.03
    ax_wpm = fig.add_axes([ax_wpm_left, ax_wpm_bottom, ax_wpm_width, ax_wpm_needed_height_fig])
    ax_wpm.set_facecolor('#383c44')
    wpm_scale_min = 0
    wpm_scale_max = 100
    ax_wpm.set_xlim(wpm_scale_min, wpm_scale_max)
    ax_wpm.set_xlabel('WPM', color=text_color, fontsize=10)
    ax_wpm.tick_params(axis='x', colors=text_color, labelsize=9)
    ax_wpm.spines['bottom'].set_color(text_color)
    ax_wpm.spines['top'].set_visible(False)
    ax_wpm.spines['right'].set_visible(False)
    ax_wpm.spines['left'].set_visible(False)
    y_tick_positions = np.arange(num_wpm_metrics)
    metric_labels = [m['label_key'] for m in wpm_metrics_data] # <-- CORRETTO
    ax_wpm.set_yticks(y_tick_positions)
    ax_wpm.set_yticklabels(metric_labels[::-1])
    ax_wpm.tick_params(axis='y', colors=text_color, labelsize=10, length=0)
    ax_wpm.invert_yaxis()
    bar_draw_height = 0.35
    for i, metric in enumerate(wpm_metrics_data):
        y_group_center = y_tick_positions[i]
        ax_wpm.barh(y_group_center, wpm_scale_max - wpm_scale_min, height=bar_draw_height * 2.2, left=wpm_scale_min, color='#555555', edgecolor=text_color, linewidth=0.5, zorder=1, alpha=0.5)
        y_curr_bar_pos = y_group_center - bar_draw_height / 2.1
        ax_wpm.barh(y_curr_bar_pos, metric['curr'] - wpm_scale_min, height=bar_draw_height, left=wpm_scale_min, color=color_good, zorder=3, edgecolor=text_color, linewidth=0.5)
        ax_wpm.text(metric['curr'] + 0.015 * wpm_scale_max, y_curr_bar_pos, _('{}').format(metric['curr']), color=text_color, ha='left', va='center', fontsize=9, weight='bold')
        y_prev_bar_pos = y_group_center + bar_draw_height / 2.1
        if metric['prev'] is not None:
            ax_wpm.barh(y_prev_bar_pos, metric['prev'] - wpm_scale_min, height=bar_draw_height, left=wpm_scale_min, color=color_neutral, zorder=2, alpha=0.8, edgecolor=text_color, linewidth=0.5)
            ax_wpm.text(metric['prev'] + 0.015 * wpm_scale_max, y_prev_bar_pos, _('{}').format(metric['prev']), color=text_color, ha='left', va='center', fontsize=9)
        if metric['prev'] is not None:
            delta = metric['curr'] - metric['prev']
            color_txt, symbol = get_delta_color_and_symbol(delta, higher_is_better=metric['higher_better'], tolerance=0.05)
            perc_delta_str = _(' ({}%)').format(delta / metric['prev'] * 100) if metric['prev'] != 0 else ''
            norm_y_in_ax = (y_group_center + 0.5) / num_wpm_metrics
            y_fig_coord_for_text = ax_wpm_bottom + (1 - norm_y_in_ax) * ax_wpm_needed_height_fig
            fig.text(ax_variation_text_left, y_fig_coord_for_text, _('{symbol} {delta}{perc_delta_str}').format(symbol=symbol, delta=delta, perc_delta_str=perc_delta_str), color=color_txt, ha='left', va='center', fontsize=10)
    if any((metric['prev'] is not None for metric in wpm_metrics_data)):
        legend_elements = [plt.Rectangle((0, 0), 1, 1, color=color_good, label=_('Valore Attuale')), plt.Rectangle((0, 0), 1, 1, color=color_neutral, alpha=0.8, label=_('Valore Precedente'))]
        fig.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(ax_wpm_left + ax_wpm_width + 0.01, ax_wpm_bottom + ax_wpm_needed_height_fig + 0.03), fontsize=8, ncol=1, facecolor='#444444', edgecolor=text_color, labelcolor=text_color)
    y_cursor = ax_wpm_bottom - section_spacing_fig
    fig.text(0.5, y_cursor, _('Statistiche Errori Complessive'), color=color_excellent, ha='center', va='top', fontsize=14, weight='bold')
    y_cursor -= line_height_fig * 1.2
    x_text_start = 0.1
    label_overall_err = _('Caratteri totali inviati (nel blocco)')
    value_overall_err_str = _('{}').format(current_aggregates['total_chars_sent_overall'])
    fig.text(x_text_start, y_cursor, _('{label_overall_err}: {value_overall_err_str}').format(label_overall_err=label_overall_err, value_overall_err_str=value_overall_err_str), color=text_color, ha='left', va='top', fontsize=11)
    if previous_aggregates:
        prev_val = previous_aggregates['total_chars_sent_overall']
        delta = current_aggregates['total_chars_sent_overall'] - prev_val
        perc_delta_str = _(' ({}%)').format(delta / prev_val * 100) if prev_val != 0 else ''
        fig.text(x_text_start + 0.4, y_cursor, _('vs. {prev_val} ({delta}{perc_delta_str})').format(prev_val=prev_val, delta=delta, perc_delta_str=perc_delta_str), color=color_neutral, ha='left', va='top', fontsize=10, style='italic')
    y_cursor -= line_height_fig
    total_chars_curr = current_aggregates['total_chars_sent_overall']
    total_errs_curr = current_aggregates['total_errors_chars_overall']
    overall_error_rate_curr = total_errs_curr / total_chars_curr * 100 if total_chars_curr > 0 else 0.0
    label_overall_err = _('Tasso errore generale')
    value_overall_err_str = _('{overall_error_rate_curr}% ({total_errs_curr}/{total_chars_curr})').format(overall_error_rate_curr=overall_error_rate_curr, total_errs_curr=total_errs_curr, total_chars_curr=total_chars_curr)
    fig.text(x_text_start, y_cursor, _('{label_overall_err}: {value_overall_err_str}').format(label_overall_err=label_overall_err, value_overall_err_str=value_overall_err_str), color=text_color, ha='left', va='top', fontsize=11)
    if previous_aggregates:
        total_chars_prev = previous_aggregates['total_chars_sent_overall']
        total_errs_prev = previous_aggregates['total_errors_chars_overall']
        overall_error_rate_prev = total_errs_prev / total_chars_prev * 100 if total_chars_prev > 0 else 0.0
        delta_rate = overall_error_rate_curr - overall_error_rate_prev
        color, symbol = get_delta_color_and_symbol(delta_rate, higher_is_better=False)
        fig.text(x_text_start + 0.4, y_cursor, _('vs. {overall_error_rate_prev}% ({symbol} {delta_rate} punti %)').format(overall_error_rate_prev=overall_error_rate_prev, symbol=symbol, delta_rate=delta_rate), color=color, ha='left', va='top', fontsize=10, style='italic')
    y_cursor -= section_spacing_fig
    fig.text(0.5, y_cursor, _('Dettaglio errori per carattere'), color=color_excellent, ha='center', va='top', fontsize=14, weight='bold')
    y_cursor -= line_height_fig * 0.06
    top_n_errors_to_display = 10
    if current_aggregates['aggregated_errors_detail']:
        sorted_char_errors = sorted(current_aggregates['aggregated_errors_detail'].items(), key=lambda item: (-item[1], item[0]))[:top_n_errors_to_display]
        error_chars = [item[0].upper() for item in sorted_char_errors]
        error_counts = [item[1] for item in sorted_char_errors]
        if error_counts:
            height_per_error_bar_fig = 0.035
            ax_err_needed_height_fig = height_per_error_bar_fig * len(error_chars) + 0.03
            ax_err_left = 0.1
            ax_err_width = 0.8
            ax_err_bottom = y_cursor - ax_err_needed_height_fig
            ax_char_err = fig.add_axes([ax_err_left, ax_err_bottom, ax_err_width, ax_err_needed_height_fig])
            ax_char_err.set_facecolor('#383c44')
            y_positions = np.arange(len(error_chars))
            bar_draw_visual_height = 0.6
            max_error_val = max(error_counts) if error_counts else 1
            plot_area_width = max_error_val * 1.1
            ax_char_err.set_xlim(0, plot_area_width)
            left_offsets = [(plot_area_width - count) / 2 for count in error_counts]
            bar_colors_list = []
            for i in range(len(sorted_char_errors)):
                if i < 3:
                    bar_colors_list.append(color_error_high)
                elif i < 7:
                    bar_colors_list.append(color_neutral)
                else:
                    bar_colors_list.append(color_good)
            bars = ax_char_err.barh(y_positions, error_counts, height=bar_draw_visual_height, left=left_offsets, color=bar_colors_list, edgecolor=text_color, linewidth=0.5, zorder=2)
            ax_char_err.set_yticks(y_positions)
            ax_char_err.set_yticklabels(error_chars, color=text_color, fontsize=9, weight='bold')
            ax_char_err.invert_yaxis()
            ax_char_err.tick_params(axis='y', length=0)
            ax_char_err.set_xticks([])
            ax_char_err.set_xlabel('')
            ax_char_err.spines['bottom'].set_visible(False)
            ax_char_err.spines['top'].set_visible(False)
            ax_char_err.spines['right'].set_visible(False)
            ax_char_err.spines['left'].set_visible(False)
            if error_counts:
                longest_bar_width = error_counts[0]
                left_longest_bar = left_offsets[0]
                right_longest_bar = left_offsets[0] + longest_bar_width
                y_top_line = y_positions[0] + bar_draw_visual_height / 2
                y_bottom_line = y_positions[-1] - bar_draw_visual_height / 2
                ax_char_err.vlines(x=left_longest_bar, ymin=y_bottom_line, ymax=y_top_line, color='white', linestyle='--', linewidth=0.75, alpha=0.7, zorder=1)
                ax_char_err.vlines(x=right_longest_bar, ymin=y_bottom_line, ymax=y_top_line, color='white', linestyle='--', linewidth=0.75, alpha=0.7, zorder=1)
            total_chars_in_block_for_perc = current_aggregates['total_chars_sent_overall']
            aggregated_sent_chars_for_perc = current_aggregates.get('aggregated_sent_chars_detail', {})
            for i, bar_patch in enumerate(bars):
                char_l = error_chars[i].lower()
                count = error_counts[i]
                perc_vs_total = count / total_chars_in_block_for_perc * 100 if total_chars_in_block_for_perc > 0 else 0.0
                errori = count
                inviati = aggregated_sent_chars_for_perc.get(char_l, 0)
                limite_inferiore = wilson_score_lower_bound(errori, inviati) * 100
                limite_superiore = wilson_score_upper_bound(errori, inviati) * 100
                annotation_text = _(" {errori} errori su {inviati}. Tasso err. ~ [{inf:.1f}% - {sup:.1f}%]").format(
                    errori=errori,
                    inviati=inviati,
                    inf=limite_inferiore,
                    sup=limite_superiore
                )
                text_x_pos = bar_patch.get_x() + bar_patch.get_width() + plot_area_width * 0.01
                ax_char_err.text(text_x_pos, bar_patch.get_y() + bar_patch.get_height() / 2, annotation_text, va='center', ha='left', color=text_color, fontsize=8)
            y_cursor = ax_err_bottom - section_spacing_fig
        else:
            no_detail_errors_text = _('Nessun errore di dettaglio da visualizzare nel grafico.')
            fig.text(0.5, y_cursor - line_height_fig, no_detail_errors_text, color=text_color, ha='center', va='top', fontsize=10, style='italic')
            y_cursor -= line_height_fig * 2 + section_spacing_fig
    else:
        no_errors_text = _('Nessun errore registrato per questo blocco di sessioni.')
        fig.text(0.5, y_cursor - line_height_fig, no_errors_text, color=text_color, ha='center', va='top', fontsize=10, style='italic')
        y_cursor -= line_height_fig * 2 + section_spacing_fig
    if previous_aggregates and previous_aggregates['num_sessions_in_block'] > 0:
        fig.text(0.5, y_cursor, _('Variazioni Dettaglio Errori per Carattere'), color=color_excellent, ha='center', va='top', fontsize=14, weight='bold')
        y_cursor -= line_height_fig * 0.06
        if 'sorted_char_errors' not in locals() and 'error_chars' not in locals():
            _potential_chars = list(set(current_aggregates['aggregated_errors_detail'].keys()) | set(previous_aggregates['aggregated_errors_detail'].keys()))
            _sorted_potential_chars = sorted(_potential_chars, key=lambda char_key: (-current_aggregates['aggregated_errors_detail'].get(char_key, 0), char_key))
            chars_for_variation_plot = [item.lower() for item in _sorted_potential_chars][:top_n_errors_to_display]
        elif 'error_chars' in locals():
            chars_for_variation_plot = [char.lower() for char in error_chars]
        else:
            chars_for_variation_plot = []
        variation_data_list = []
        for char_lcase in chars_for_variation_plot:
            curr_count = current_aggregates['aggregated_errors_detail'].get(char_lcase, 0)
            prev_count = previous_aggregates['aggregated_errors_detail'].get(char_lcase, 0)
            curr_total_sent = current_aggregates.get('aggregated_sent_chars_detail', {}).get(char_lcase, 0)
            prev_total_sent = previous_aggregates.get('aggregated_sent_chars_detail', {}).get(char_lcase, 0)
            if curr_total_sent > 0 or prev_total_sent > 0:
                curr_rate_spec = curr_count / curr_total_sent * 100 if curr_total_sent > 0 else 0.0
                prev_rate_spec = prev_count / prev_total_sent * 100 if prev_total_sent > 0 else 0.0
                delta = curr_rate_spec - prev_rate_spec
                variation_data_list.append({'char': char_lcase.upper(), 'delta': delta})
        if variation_data_list:
            deltas_values = [item['delta'] for item in variation_data_list]
            bar_colors_variation = []
            stable_threshold_abs = 1.0
            significant_improvements = sorted([d for d in deltas_values if d < -stable_threshold_abs])
            significant_worsenings = sorted([d for d in deltas_values if d > stable_threshold_abs])
            split_azzurro_verde = np.median(significant_improvements) if significant_improvements else -stable_threshold_abs
            split_arancione_rossocupo = np.median(significant_worsenings) if significant_worsenings else stable_threshold_abs
            for d_val in deltas_values:
                if d_val < -stable_threshold_abs:
                    if d_val <= split_azzurro_verde and significant_improvements:
                        bar_colors_variation.append(color_excellent)
                    else:
                        bar_colors_variation.append(color_good)
                elif d_val > stable_threshold_abs:
                    if d_val >= split_arancione_rossocupo and significant_worsenings:
                        bar_colors_variation.append(color_error_very_high)
                    else:
                        bar_colors_variation.append(color_warning)
                else:
                    bar_colors_variation.append(color_neutral)
            height_per_var_bar_fig = 0.035
            ax_var_needed_height_fig = height_per_var_bar_fig * len(variation_data_list) + 0.05
            ax_var_left = 0.15
            ax_var_width = 0.7
            ax_var_bottom = y_cursor - ax_var_needed_height_fig
            ax_err_var = fig.add_axes([ax_var_left, ax_var_bottom, ax_var_width, ax_var_needed_height_fig])
            ax_err_var.set_facecolor('#383c44')
            plot_chars = [item['char'] for item in variation_data_list]
            plot_deltas = [item['delta'] for item in variation_data_list]
            y_var_positions = np.arange(len(plot_chars))
            max_abs_delta_val = max((abs(d) for d in plot_deltas)) if plot_deltas else 1.0
            axis_plot_limit = max_abs_delta_val * 1.15
            ax_err_var.set_xlim(-axis_plot_limit, axis_plot_limit)
            ax_err_var.axvline(0, color='white', linestyle=':', linewidth=0.7, alpha=0.7, zorder=1)
            ax_err_var.axvline(-max_abs_delta_val, color='white', linestyle='--', linewidth=0.75, alpha=0.5, zorder=1)
            ax_err_var.axvline(max_abs_delta_val, color='white', linestyle='--', linewidth=0.75, alpha=0.5, zorder=1)
            for i in range(len(plot_chars)):
                delta_val = plot_deltas[i]
                bar_w = abs(delta_val)
                bar_l = delta_val if delta_val < 0 else 0
                ax_err_var.barh(y_var_positions[i], bar_w, left=bar_l, color=bar_colors_variation[i], height=0.5, edgecolor=text_color, linewidth=0.5, zorder=2)
                text_x_offset = axis_plot_limit * 0.02
                ha_val = 'right' if delta_val < 0 else 'left'
                text_x = delta_val - text_x_offset if delta_val < 0 else delta_val + text_x_offset
                ax_err_var.text(text_x, y_var_positions[i], _('{delta_val}%').format(delta_val=delta_val), va='center', ha=ha_val, color=text_color, fontsize=8)
            ax_err_var.set_yticks(y_var_positions)
            ax_err_var.set_yticklabels(plot_chars, color=text_color, fontsize=9)
            ax_err_var.invert_yaxis()
            ax_err_var.tick_params(axis='y', length=0)
            ax_err_var.set_xlabel(_('Variaz. % Err. Spec.'), color=text_color, fontsize=10)
            ax_err_var.tick_params(axis='x', colors=text_color, labelsize=9)
            ax_err_var.spines['bottom'].set_color(text_color)
            ax_err_var.spines['top'].set_visible(False)
            ax_err_var.spines['right'].set_visible(False)
            ax_err_var.spines['left'].set_visible(False)
            y_cursor = ax_var_bottom - section_spacing_fig
        else:
            fig.text(0.5, y_cursor - line_height_fig, _('Nessuna variazione significativa degli errori per carattere da visualizzare.'), color=text_color, ha='center', va='top', fontsize=10, style='italic')
            y_cursor -= line_height_fig * 2 + section_spacing_fig
    else:
        fig.text(0.5, y_cursor - line_height_fig, _('Dati precedenti non disponibili per calcolare le variazioni.'), color=text_color, ha='center', va='top', fontsize=10, style='italic')
        y_cursor -= line_height_fig * 2 + section_spacing_fig
    try:
        plt.savefig(output_filename, format='svg', bbox_inches='tight', pad_inches=0.3, facecolor=fig.get_facecolor())
        plt.close(fig)
    except Exception as e_save:
        if 'fig' in locals() and fig:
            plt.close(fig)
        print(_('Errore nel salvataggio del file grafico'))

def load_settings():
    """Carica le impostazioni dal file JSON o restituisce i default."""
    global overall_settings_changed
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
            
            # --- Logica di Migrazione ---
            overall_settings_changed = False # Reset per questa sezione

            # Migrazione delle vecchie statistiche rxing
            if 'rxing_stats' in loaded_data:
                if 'rxing_stats_words' not in loaded_data:
                    loaded_data['rxing_stats_words'] = loaded_data['rxing_stats']
                del loaded_data['rxing_stats']
                print(_("Migrated old 'rxing_stats' to 'rxing_stats_words'."))
                overall_settings_changed = True

            # Migrazione dei vecchi dati storici rxing
            if 'historical_rx_data' in loaded_data:
                old_historical_data = loaded_data['historical_rx_data']

                # Migra le impostazioni condivise se non esistono ancora
                if 'historical_rx_settings' not in loaded_data:
                    loaded_data['historical_rx_settings'] = {
                        'max_sessions_to_keep': old_historical_data.get('max_sessions_to_keep', HISTORICAL_RX_MAX_SESSIONS_DEFAULT),
                        'report_interval': old_historical_data.get('report_interval', HISTORICAL_RX_REPORT_INTERVAL),
                    }
                
                # Migra i dati effettivi (log delle sessioni) in _words
                if 'historical_rx_data_words' not in loaded_data:
                    loaded_data['historical_rx_data_words'] = {
                        'chars_since_last_report': old_historical_data.get('chars_since_last_report', 0),
                        'sessions_log': old_historical_data.get('sessions_log', []),
                        'historical_reports': old_historical_data.get('historical_reports', [])
                    }
                del loaded_data['historical_rx_data']
                print(_("Migrated old 'historical_rx_data' to 'historical_rx_data_words' and extracted settings."))
                overall_settings_changed = True

            # Fine Logica di Migrazione

            merged_data = {}
            for main_key, default_values in DEFAULT_DATA.items():
                loaded_section = loaded_data.get(main_key, {})
                # Gestione speciale per historical_rx_settings se c'è un'override nelle default_values
                if main_key == 'historical_rx_settings' and 'max_sessions_to_keep' in loaded_section and 'report_interval' in loaded_section:
                    merged_data[main_key] = loaded_section  # Usa i valori caricati, non i default
                    continue
                elif main_key == 'historical_rx_settings': # Se non ci sono override nei loaded_section per questi valori
                    merged_data[main_key] = default_values.copy() # Usa i default
                    if 'max_sessions_to_keep' in loaded_section:
                        merged_data[main_key]['max_sessions_to_keep'] = loaded_section['max_sessions_to_keep']
                    if 'report_interval' in loaded_section:
                        merged_data[main_key]['report_interval'] = loaded_section['report_interval']
                    continue
                # Il resto della gestione è per le altre sezioni che non hanno logica di merge speciale
                if isinstance(default_values, dict):
                    merged_section = default_values.copy()
                else: # Per valori non dizionari, come liste o semplici tipi
                    merged_section = default_values

                if isinstance(merged_section, dict) and isinstance(loaded_section, dict):
                    merged_section.update(loaded_section) # Applica i valori caricati sui default
                merged_data[main_key] = merged_section
            
            # Assicurati che le nuove chiavi siano inizializzate se non presenti dopo la migrazione
            for key_suffix in ['words', 'chars', 'qrz']:
                rx_stats_key = f'rxing_stats_{key_suffix}'
                if rx_stats_key not in merged_data:
                    merged_data[rx_stats_key] = DEFAULT_DATA[rx_stats_key].copy()
                hist_data_key = f'historical_rx_data_{key_suffix}'
                if hist_data_key not in merged_data:
                    merged_data[hist_data_key] = DEFAULT_DATA[hist_data_key].copy()

            overall_settings_default = DEFAULT_DATA.get('overall_settings', {})
            app_language_default = overall_settings_default.get('app_language', 'en')
            loaded_overall_settings = merged_data.get('overall_settings', overall_settings_default)
            print(_('Impostazioni generali caricate'))
            return merged_data
        except (json.JSONDecodeError, IOError, TypeError) as e:
            print(_('Errore durante il caricamento del file di impostazioni.'))
            overall_settings_changed = True
            return {k: v.copy() if isinstance(v, dict) else v for k, v in DEFAULT_DATA.items()}
    else:
        overall_settings_default = DEFAULT_DATA.get('overall_settings', {})
        app_language_default = overall_settings_default.get('app_language', 'en')
        print(_('Impostazioni generali di default'))
        overall_settings_changed = True
        return {k: v.copy() if isinstance(v, dict) else v for k, v in DEFAULT_DATA.items()}

def save_settings(data):
    """Salva le impostazioni correnti nel file JSON."""
    global app_language
    try:
        data_to_save = data.copy()
        if 'rxing_stats' in data_to_save and isinstance(data_to_save['rxing_stats'].get('total_time'), dt.timedelta):
            data_to_save['rxing_stats']['total_time_seconds'] = data_to_save['rxing_stats']['total_time'].total_seconds()
            data_to_save['rxing_stats'].pop('total_time', None)
        elif 'rxing_stats' in data_to_save and 'total_time' in data_to_save['rxing_stats']:
            data_to_save['rxing_stats'].pop('total_time', None)
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, indent=4, ensure_ascii=False)
        print(_('Impostazioni generali salvate sul disco.'))
    except IOError as e:
        print(_('Errore nel salvare {SETTINGS_FILE}: {e}').format(SETTINGS_FILE=SETTINGS_FILE, e=e))
    except TypeError as e:
        print(_('Errore di tipo durante la preparazione dei dati per JSON: {e} - Dati: {data_to_save}').format(e=e, data_to_save=data_to_save))

def ItemChooser(items):
    for i, item in enumerate(items, start=1):
        print(_('{i}. {item}').format(i=i, item=item))
    while True:
        try:
            choice = dgt(prompt='N.? > ', kind='i', imin=1, imax=len(items), default=6)
            if 1 <= choice <= len(items):
                return choice - 1
        except ValueError:
            print(_('Inserisci un numero valido.'))

def KeyboardCW():
    """Settings for CW and tx with keyboard"""
    global overall_speed, overall_pitch, overall_dashes, overall_spaces, overall_dots, overall_volume, overall_settings_changed, overall_ms, overall_fs, overall_wave
    global app_data
    MNKeyboard_settings= _("Benvenuto nella sezione dove potrai ascoltare il CW e configurare tutti i suoi parametri. \
                           \nQuesti parametri saranno validi e attivi in tutto CWAPU e verranno salvati automaticamente quando esci dall'app. \
                           \nOra, leggi attentamente quanto segue: \
                           \ntPremi Invio senza digitare nulla per uscire e tornare al menu principale; \
                           \n\tdigita .w seguito da un valore numerico per impostare il WPM; \
                           \n\tdigita .h seguito da un valore per il pitch del picco della nota CW che vuoi usare; \
                           \n\tdigita .l seguito da un valore per impostare la linea, il default è 30; \
                           \n\tdigita .s seguito da un valore per impostare lo spazio, il default è 50; \
                           \n\tdigita .p proprio come .s ma per i punti; \
                           \n\tdigita .v seguito da un valore tra 0 e 100 per impostare il volume; \
                           \n\tdigita .f1 .f2 .f3 o .f4 per cambiare la forma d'onda; \
                           \n\tdigita .m seguito da millisecondi per impostare il fade in e out per la nota CW; \
                           \n\tdigita .g seguito da un valore per impostare la quantità di esercizi per le statistiche globali; \
                           \n\tdigita .x seguito da un valore per impostare ogni quanti caratteri aggiornare le stats globali; \
                           \n\tdigita .t #-# dove i # sono i valori minimo-massimo del filtro per la scelta delle parole; \
                           \n\tdigita .y per impostare un gruppo personalizzato di caratteri su cui allenarti; \
                           \n\tdigita .sr per impostare il sample rate da inviare alla scheda audio; \
                           \n\tdigita ? per vedere questo messaggio di aiuto; \
                           \n\tdigita ?? per visualizzare i parametri impostati; \
                           \n\tdigita .rs per reimpostare il CW al peso standard di 1/3; \
                           \n\tdigita .sv <testo> per salvare il CW in un file .wav \
                           \n")
    tosave = False
    rwpm = overall_speed
    print("\n"+MNKeyboard_settings)
    while True:
        if rwpm is not None and overall_speed != rwpm:
            current_prompt = _('RWPM: {rwpm:.2f}').format(rwpm=rwpm)
        else:
            current_prompt = _('WPM: {overall_speed:.2f}').format(overall_speed=overall_speed)
        if tosave:
            print(current_prompt + ' SV>', end='', flush=True)
            tosave = False
        else:
            print(current_prompt + '> ', end='', flush=True)
        msg_input = sys.stdin.readline()
        if not msg_input:
            break
        msg = msg_input[:-1] + ' '
        msg_for_cw = msg
        if msg == ' ':
            plo, rwpm_temp = CWzator(msg='73', wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
            if rwpm_temp is not None:
                rwpm = rwpm_temp
            break
        elif msg == '? ':
            print('\n' + MNKeyboard_settings)
            msg_for_cw = 'bk the commands are bk'
        elif msg == '?? ':
            current_max_sessions_g_val = app_data.get('historical_rx_data', {}).get('max_sessions_to_keep', HISTORICAL_RX_MAX_SESSIONS_DEFAULT)
            current_report_interval_x_val = app_data.get('historical_rx_data', {}).get('report_interval', HISTORICAL_RX_REPORT_INTERVAL)
            switcher_states_config = app_data.get('rx_menu_switcher_states', {})
            parole_min = switcher_states_config.get('parole_filter_min', 0)
            parole_max = switcher_states_config.get('parole_filter_max', 0)
            custom_set_str = switcher_states_config.get('custom_set_string', '')
            t_filter_display = _('{parole_min}-{parole_max}').format(parole_min=parole_min, parole_max=parole_max) if parole_min > 0 and parole_max > 0 else _('Filtro non impostato')
            y_custom_set_display = _('"{custom_set_str}"').format(custom_set_str=custom_set_str) if custom_set_str else _('Gruppo vuoto')
            base_settings_line1 = _('\n\tWPM: {overall_speed}, Hz: {overall_pitch}, Volume: {}').format(int(overall_volume * 100), overall_speed=overall_speed, overall_pitch=overall_pitch)
            base_settings_line2 = _('\tL/S/P: {overall_dashes}/{overall_spaces}/{overall_dots}, Wave: {}, MS: {overall_ms}, FS: {}.').format(WAVE_TYPES[overall_wave - 1], SAMPLE_RATES[overall_fs], overall_dashes=overall_dashes, overall_spaces=overall_spaces, overall_dots=overall_dots, overall_ms=overall_ms)
            history_settings_line = _('\tMax Exercises History (g): {current_max_sessions_g_val}, Report size (x): {current_report_interval_x_val}.').format(current_max_sessions_g_val=current_max_sessions_g_val, current_report_interval_x_val=current_report_interval_x_val)
            new_filter_settings_line = _('\tWord Filter (T): {t_filter_display}, Custom Set (Y): {y_custom_set_display}').format(t_filter_display=t_filter_display, y_custom_set_display=y_custom_set_display)
            print(base_settings_line1)
            print(base_settings_line2)
            print(history_settings_line)
            print(new_filter_settings_line)
            msg_for_cw = 'bk r parameters are bk'
        elif msg == '.sr ':
            new_fs_index = ItemChooser(SAMPLE_RATES)
            if new_fs_index != overall_fs:
                overall_fs = new_fs_index
                overall_settings_changed = True
            plo, rwpm_temp = CWzator(msg=_('bk fs is {} bk').format(SAMPLE_RATES[overall_fs]), wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
            if rwpm_temp is not None:
                rwpm = rwpm_temp
            msg_for_cw = ''
        elif msg == '.rs ':
            if not (overall_dashes == 30 and overall_spaces == 50 and (overall_dots == 50)):
                overall_dashes, overall_spaces, overall_dots = (30, 50, 50)
                overall_settings_changed = True
            plo, rwpm_temp = CWzator(msg='bk reset ok bk', wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
            if rwpm_temp is not None:
                rwpm = rwpm_temp
            msg_for_cw = ''
        elif msg.startswith('.sv '):
            msg_for_cw = msg[4:]
            tosave = True
        elif msg.startswith('.'):
            command_candidate_str = msg[1:].strip()
            cmd_letter_parsed = ''
            value_int_parsed = None
            value_str_parsed = ''
            is_value_numeric_type = False
            is_value_special_format = False
            match_val_num = re.match('([a-zA-Z])(\\d+)', command_candidate_str)
            if match_val_num and command_candidate_str == match_val_num.group(0):
                cmd_letter_parsed = match_val_num.group(1).lower()
                value_int_parsed = int(match_val_num.group(2))
                is_value_numeric_type = True
            else:
                parts = command_candidate_str.split(maxsplit=1)
                cmd_letter_parsed = parts[0].lower()
                if len(parts) > 1:
                    value_str_parsed = parts[1]
                    is_value_special_format = True
            command_processed_internally = False
            feedback_cw = ''
            if cmd_letter_parsed == 'y':
                if command_candidate_str == 'y':
                    print(_('Avvio editor gruppo Custom...'))
                    custom_string_result = CustomSet(overall_speed)
                    current_saved_set = app_data['rx_menu_switcher_states'].get('custom_set_string', '')
                    if current_saved_set != custom_string_result:
                        app_data['rx_menu_switcher_states']['custom_set_string'] = custom_string_result
                        overall_settings_changed = True
                    if custom_string_result:
                        feedback_cw = _('Set custom: {num_chars} car.').format(num_chars=len(custom_string_result))
                    else:
                        feedback_cw = 'bk r custom set empty bk'
                    command_processed_internally = True
                    print('\n' + _("Benvenuto nella sezione dove potrai ascoltare il CW e configurare tutti i suoi parametri.\nQuesti parametri saranno validi e attivi in tutto CWAPU e verranno salvati automaticamente quando esci dall'app.\nOra, leggi attentamente quanto segue:\ntPremi Invio senza digitare nulla per uscire e tornare al menu principale;\n\tdigita .w seguito da un valore numerico per impostare il WPM;\n\tdigita .h seguito da un valore per il pitch del picco della nota CW che vuoi usare;\n\tdigita .l seguito da un valore per impostare la linea, il default è 30;\n\tdigita .s seguito da un valore per impostare lo spazio, il default è 50;\n\tdigita .p proprio come .s ma per i punti;\n\tdigita .v seguito da un valore tra 0 e 100 per impostare il volume;\n\tdigita .f1 .f2 .f3 o .f4 per cambiare la forma d'onda;\n\tdigita .m seguito da millisecondi per impostare il fade in e out per la nota CW;\n\tdigita .g seguito da un valore per impostare la quantità di esercizi per le statistiche globali;\n\tdigita .x seguito da un valore per impostare ogni quanti caratteri aggiornare le stats globali;\n\tdigita .t #-# dove i # sono i valori minimo-massimo del filtro per la scelta delle parole;\n\tdigita .y per impostare un gruppo personalizzato di caratteri su cui allenarti;\n\tdigita .sr per impostare il sample rate da inviare alla tua scheda audio;\n\tdigita ? per vedere questo messaggio di aiuto;\n\tdigita ?? per visualizzare i parametri impostati;\n\tdigita .rs per reimpostare il CW al peso standard di 1/3\n\tdigita .sv <testo> per salvare il CW in un file .wav\n"))
                else:
                    feedback_cw = '?'
                    command_processed_internally = True
            elif cmd_letter_parsed == 't':
                if is_value_special_format and '-' in value_str_parsed:
                    min_max_parts = value_str_parsed.split('-')
                    if len(min_max_parts) == 2 and min_max_parts[0].isdigit() and min_max_parts[1].isdigit():
                        p_min = int(min_max_parts[0])
                        p_max = int(min_max_parts[1])
                        p_min_validated = max(1, min(10, p_min))
                        p_max_validated = max(3, min(35, p_max))
                        if p_min_validated > p_max_validated:
                            p_min_validated = p_max_validated
                        if app_data['rx_menu_switcher_states'].get('parole_filter_min') != p_min_validated or app_data['rx_menu_switcher_states'].get('parole_filter_max') != p_max_validated:
                            app_data['rx_menu_switcher_states']['parole_filter_min'] = p_min_validated
                            app_data['rx_menu_switcher_states']['parole_filter_max'] = p_max_validated
                            overall_settings_changed = True
                        feedback_cw = _('bk r word filter is {p_min_validated} {p_max_validated} bk').format(p_min_validated=p_min_validated, p_max_validated=p_max_validated)
                        command_processed_internally = True
                    else:
                        feedback_cw = '?'
                        command_processed_internally = True
                else:
                    feedback_cw = '?'
                    command_processed_internally = True
            elif is_value_numeric_type and value_int_parsed is not None:
                if cmd_letter_parsed == 'g':
                    min_val_g, max_val_g = (20, 5000)
                    actual_val_g = app_data.get('historical_rx_data', {}).get('max_sessions_to_keep', HISTORICAL_RX_MAX_SESSIONS_DEFAULT)
                    new_val_g = max(min_val_g, min(max_val_g, value_int_parsed))
                    if actual_val_g != new_val_g:
                        app_data['historical_rx_data']['max_sessions_to_keep'] = new_val_g
                        sessions_log = app_data['historical_rx_data'].get('sessions_log', [])
                        if len(sessions_log) > new_val_g:
                            app_data['historical_rx_data']['sessions_log'] = sessions_log[-new_val_g:]
                        overall_settings_changed = True
                    feedback_cw = _('bk r max exercises is {new_val_g} bk').format(new_val_g=new_val_g)
                    command_processed_internally = True
                elif cmd_letter_parsed == 'x':
                    min_val_x, max_val_x = (500, 15000)
                    actual_val_x = app_data.get('historical_rx_data', {}).get('report_interval', HISTORICAL_RX_REPORT_INTERVAL)
                    new_val_x = max(min_val_x, min(max_val_x, value_int_parsed))
                    if actual_val_x != new_val_x:
                        app_data['historical_rx_data']['report_interval'] = new_val_x
                        overall_settings_changed = True
                    feedback_cw = _('bk r report size is {new_val_x} bk').format(new_val_x=new_val_x)
                    command_processed_internally = True
                elif cmd_letter_parsed == 'w':
                    if overall_speed != value_int_parsed:
                        new_speed = max(5, min(99, value_int_parsed))
                        if overall_speed != new_speed:
                            overall_speed = new_speed
                            overall_settings_changed = True
                    feedback_cw = _('bk r w is {overall_speed} bk').format(overall_speed=overall_speed)
                    command_processed_internally = True
                elif cmd_letter_parsed == 'm':
                    if overall_ms != value_int_parsed:
                        new_ms = max(1, min(30, value_int_parsed))
                        if overall_ms != new_ms:
                            overall_ms = new_ms
                            overall_settings_changed = True
                    feedback_cw = _('bk r ms is {overall_ms} bk').format(overall_ms=overall_ms)
                    command_processed_internally = True
                elif cmd_letter_parsed == 'f':
                    new_wave_idx_user = max(1, min(len(WAVE_TYPES), value_int_parsed))
                    if overall_wave != new_wave_idx_user:
                        overall_wave = new_wave_idx_user
                        overall_settings_changed = True
                    feedback_cw = _('bk r wave is {} bk').format(WAVE_TYPES[overall_wave - 1])
                    command_processed_internally = True
                elif cmd_letter_parsed == 'h':
                    if overall_pitch != value_int_parsed:
                        new_pitch = max(200, min(2700, value_int_parsed))
                        if overall_pitch != new_pitch:
                            overall_pitch = new_pitch
                            overall_settings_changed = True
                    feedback_cw = _('bk r h is {overall_pitch} bk').format(overall_pitch=overall_pitch)
                    command_processed_internally = True
                elif cmd_letter_parsed == 'l':
                    if overall_dashes != value_int_parsed:
                        new_dashes = max(1, min(99, value_int_parsed))
                        if overall_dashes != new_dashes:
                            overall_dashes = new_dashes
                            overall_settings_changed = True
                    feedback_cw = _('bk r l is {overall_dashes} bk').format(overall_dashes=overall_dashes)
                    command_processed_internally = True
                elif cmd_letter_parsed == 's':
                    if overall_spaces != value_int_parsed:
                        new_spaces = max(3, min(99, value_int_parsed))
                        if overall_spaces != new_spaces:
                            overall_spaces = new_spaces
                            overall_settings_changed = True
                    feedback_cw = _('bk r s is {overall_spaces} bk').format(overall_spaces=overall_spaces)
                    command_processed_internally = True
                elif cmd_letter_parsed == 'p':
                    if overall_dots != value_int_parsed:
                        new_dots = max(1, min(99, value_int_parsed))
                        if overall_dots != new_dots:
                            overall_dots = new_dots
                            overall_settings_changed = True
                    feedback_cw = _('bk r p is {overall_dots} bk').format(overall_dots=overall_dots)
                    command_processed_internally = True
                elif cmd_letter_parsed == 'v':
                    new_volume_percent = max(0, min(100, value_int_parsed))
                    if abs(overall_volume * 100 - new_volume_percent) > 0.01:
                        overall_volume = new_volume_percent / 100.0
                        overall_settings_changed = True
                    feedback_cw = _('bk r v is {new_volume_percent} bk').format(new_volume_percent=new_volume_percent)
                    command_processed_internally = True
            if command_processed_internally:
                if feedback_cw:
                    plo, rwpm_temp = CWzator(msg=feedback_cw, wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
                    if rwpm_temp is not None:
                        rwpm = rwpm_temp
                msg_for_cw = ''
        if msg_for_cw.strip():
            plo, rwpm_temp = CWzator(msg=msg_for_cw, wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave, file=tosave)
            if rwpm_temp is not None:
                rwpm = rwpm_temp
            elif msg_for_cw.strip():
                rwpm = overall_speed
            if tosave:
                tosave = False
    print(_('Ciao per ora. Torniamo al menu principale.') + '\n')
    return

def StringCleaning(stringa):
    stringa = stringa.strip()
    stringa = stringa.lower()
    cleaned = re.sub('[^a-z0-9\\sàèéìòù@.,;:!?\\\'\\"()-=]', '', stringa)
    cleaned = re.sub('\\s+', ' ', cleaned)
    return cleaned

def CreateDictionary():
    print(_("Attenzione! Si prega di leggere attentamente.\nPer gli esercizi di ricezione, (r) dal menu principale, CWAPU utilizza il file words.txt, che deve essere situato nella cartella da cui hai lanciato cwapu.py o cwapu.exe. Se questo file non esiste, creane uno con un editor di testo e scrivi alcune parole al suo interno, una parola per linea, quindi salva.\nLa procedura WordsCreator ti permette di scansionare tutti i file txt contenuti nelle cartelle che indichi e aggiungere tutte le parole da questi file a words.txt. Le parole saranno aggiunte unicamente, cioè saranno tutte diverse tra loro.\nIl file prodotto da questo processo sarà denominato words_updated.txt. Controllalo con un editor di testo e, se sei soddisfatto, rinominalo in words.txt, sostituendo l'esistente words.txt.\nPuoi ripetere questa operazione tutte le volte che vuoi: words_updated.txt conterrà le parole da words.txt più tutte quelle raccolte dai nuovi file .txt elaborati."))
    import Words_Creator
    Words_Creator.Start()
    return

def CustomSet(overall_speed):
    global app_data, app_language
    cs = set()
    prefill_prompt_text = _('Vuoi iniziare con un gruppo di caratteri precompilato?')
    yes_char = _('s')
    no_char = _('n')
    use_prefill_choice = key(prompt=_('{prefill_prompt_text} [{yes_char}/{no_char}]: ').format(prefill_prompt_text=prefill_prompt_text, yes_char=yes_char, no_char=no_char)).lower()
    if use_prefill_choice == yes_char:
        prefilled_chars_list = []
        sessions_log = app_data.get('historical_rx_data', {}).get('sessions_log', [])
        if sessions_log:
            # 1. Aggreghiamo sia gli errori che i caratteri inviati
            aggregated_errors = {}
            aggregated_sent = {}
            for session_data in sessions_log:
                # Aggrega errori
                for char, count in session_data.get('errors_detail_session', {}).items():
                    char_lower = char.lower()
                    if char_lower in VALID_MORSE_CHARS_FOR_CUSTOM_SET:
                        aggregated_errors[char_lower] = aggregated_errors.get(char_lower, 0) + count
                # Aggrega invii
                for char, count in session_data.get('sent_chars_detail_session', {}).items():
                    char_lower = char.lower()
                    if char_lower in VALID_MORSE_CHARS_FOR_CUSTOM_SET:
                        aggregated_sent[char_lower] = aggregated_sent.get(char_lower, 0) + count
            # 2. Calcoliamo il punteggio di criticità (Wilson Score) per ogni carattere
            char_scores = []
            all_chars = set(aggregated_errors.keys()) | set(aggregated_sent.keys())
            for char in all_chars:
                errori = aggregated_errors.get(char, 0)
                inviati = aggregated_sent.get(char, 0)
                if inviati > 0: # Calcoliamo solo per caratteri inviati almeno una volta
                    score = wilson_score_lower_bound(errori, inviati)
                    char_scores.append({'char': char, 'score': score})
            # 3. Ordiniamo per punteggio decrescente e prendiamo i primi 10
            if char_scores:
                # Ordina per score (più alto è peggio) e poi alfabeticamente
                sorted_critical_chars = sorted(char_scores, key=lambda x: (-x['score'], x['char']))
                prefilled_chars_list = [item['char'] for item in sorted_critical_chars[:10]]
        if prefilled_chars_list:
            print(_('Gruppo precompilato con errori frequenti: {chars}').format(chars=', '.join((c.upper() for c in prefilled_chars_list))))
            for char_err in prefilled_chars_list:
                cs.add(char_err)
        else:
            random_chars_pool = list(VALID_MORSE_CHARS_FOR_CUSTOM_SET)
            if random_chars_pool:
                num_to_add = min(10, len(random_chars_pool))
                cs.update(random.sample(random_chars_pool, num_to_add))
                if cs:
                    print(_('Gruppo precompilato con caratteri casuali: {chars}').format(chars=', '.join(sorted((c.upper() for c in cs)))))
                else:
                    print(_('Impossibile precompilare: nessun carattere valido disponibile.'))
            else:
                print(_('Impossibile precompilare: nessun carattere valido disponibile.'))
    print(_('Inserisci/modifica caratteri (toggle). Invio per terminare.'))
    while True:
        current_set_display = ''.join(sorted(list(cs)))
        user_input_char = key(prompt='\n' + current_set_display)
        if user_input_char == '\r':
            if len(cs) >= 2:
                break
            else:
                CWzator(msg='?', wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
                continue
        if len(user_input_char) == 1 and user_input_char.isprintable():
            char_typed_lower = user_input_char.lower()
            if char_typed_lower not in VALID_MORSE_CHARS_FOR_CUSTOM_SET:
                CWzator(msg='?', wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
                continue
            if char_typed_lower in cs:
                cs.remove(char_typed_lower)
            else:
                cs.add(char_typed_lower)
                CWzator(msg=char_typed_lower, wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
        elif user_input_char != '\r':
            CWzator(msg='?', wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
    return ''.join(sorted(list(cs)))

def GeneratingGroup(kind, length, wpm, customized_set_param=None):
    if kind == '1':
        if not LETTERE_MORSE_POOL:
            return 'ERR_LP'
        pool = list(LETTERE_MORSE_POOL)
        return ''.join(random.choices(pool, k=length))
    elif kind == '2':
        if not NUMERI_MORSE_POOL:
            return 'ERR_NP'
        pool = list(NUMERI_MORSE_POOL)
        return ''.join(random.choices(pool, k=length))
    elif kind == '3':
        if not LETTERE_MORSE_POOL and not NUMERI_MORSE_POOL:
            return 'ERR_LNP' # Errore: pool lettere e numeri vuoto
        pool = list(LETTERE_MORSE_POOL | NUMERI_MORSE_POOL)
        return ''.join(random.choices(pool, k=length))
    elif kind == '4':
        if not customized_set_param or len(customized_set_param) < 1:
            return 'ERR_CS'
        return ''.join(random.choices(list(customized_set_param), k=length))
    elif kind == 'S':
        if not SIMBOLI_MORSE_POOL:
            return 'ERR_SP'
        pool = list(SIMBOLI_MORSE_POOL)
        return ''.join(random.choices(pool, k=length))
    return 'ERR_KD'

def Mkdqrz(c):
    # Se abbiamo un pool di call reali, 50% di probabilità di usarne uno
    if REAL_CALLS_POOL and random.random() < 0.5:
        return random.choice(REAL_CALLS_POOL)

    q = ''
    c = c[0]
    for j in str(c):
        if j.isdigit():
            q += random.choice(string.digits)
        else:
            q += random.choice(string.ascii_uppercase)
    return q

def Txing():
    print(_("Esercizio di trasmissione.\nEcco una serie casuale di pseudo-call e numeri progressivi,\n\tprova a trasmetterli con il tuo tasto CW preferito senza errori.\nQualsiasi tasto per passare al successivo, ESC per terminare l'esercizio."))
    cont = 1
    while True:
        c = random.choices(list(MDL.keys()), weights=MDL.values(), k=1)
        qrz = Mkdqrz(c)
        pgr = random.randint(1, 9999)
        prompt = _('- {cont} {qrz} 5nn {pgr}').format(cont=cont, qrz=qrz, pgr=pgr)
        wait = key(prompt)
        print()
        if ord(wait) == 27:
            break
        cont += 1
    print(_('Ciao per ora. Torniamo al menu principale.'))
    return

def Count():
    global app_data
    print(_('Conteggio, SÌ o NO?\nBarra spaziatrice significa: gruppo ricevuto;\nQualsiasi altro tasto significa: gruppo perso;\nPremi ESC per tornare al menu principale.'))
    from GBUtils import Acusticator as Ac
    esnum = app_data['counting_stats'].get('exercise_number', 1)
    cont = 0
    corr = 0
    scelta = ''
    Ac([350, 0.2, 0, 0.5], sync=True)
    print(_('Esercizio numero {esnum}:').format(esnum=esnum))
    while True:
        if cont % 100 == 0:
            Ac([1600, 0.2, 0, 0.5], sync=True)
        elif cont % 50 == 0:
            Ac([1150, 0.08, 0, 0.5], sync=True)
        elif cont % 25 == 0:
            Ac([900, 0.06, 0, 0.5], sync=True)
        elif cont % 10 == 0:
            Ac([600, 0.04, 0, 0.5], sync=True)
        if corr > 0:
            prompt = _('T{cont}, {}%, C{corr}/N{}> ').format(corr * 100 / cont, cont - corr, cont=cont, corr=corr)
        else:
            prompt = 'T1, 0%> '
        scelta = key('\n' + prompt)
        if scelta == ' ':
            corr += 1
            Ac([1380, 0.015, 0, 0.5], sync=True)
        elif ord(scelta) == 27:
            break
        else:
            Ac([310, 0.025, 0, 0.5], sync=True)
        cont += 1
    cont -= 1
    if cont > 0:
        pde = 100 - corr * 100 / cont
    else:
        pde = 100
    print(_('\nTotale: {cont}, corrette: {corr}, errori(%): {pde:.2f}%.').format(cont=cont, corr=corr, pde=pde))
    if pde <= 6:
        print(_('Superato!'))
    else:
        print(_('Fallito: {difference:.2f}% oltre la soglia.').format(difference=pde - 6))
    if cont >= 100:
        with open(os.path.join(USER_DATA_PATH, 'CWapu_Diary.txt'), 'a', encoding='utf-8') as f:
            nota = input(_('\nNota su questo esercizio: '))
            print(_('Rapporto salvato su CW_Diary.txt'))
            date = _('{}/{}/{}').format(lt()[0], lt()[1], lt()[2])
            time = _('{}, {}').format(lt()[3], lt()[4])
            f.write(_('Esercizio di conteggio #{esnum} eseguito il {date} alle {time} minuti:\n').format(esnum=esnum, date=date, time=time))
            f.write(_('Totale: {cont}, corrette: {corr}, errori(%): {pde:.2f}%.\n').format(cont=cont, corr=corr, pde=pde))
            if pde <= 6:
                f.write(_('Superato!') + '\n')
            else:
                f.write(_('Fallito: {difference:.2f}% oltre la soglia.').format(difference=pde - 6) + '\n')
            if nota != '':
                f.write(_('Nota: {nota}\n***\n').format(nota=nota))
            else:
                f.write(_('Nota: nessuna') + '\n***\n')
    else:
        print(_('Gruppi ricevuti {cont} su 100: esercizio non salvato su disco.').format(cont=cont))
    esnum = app_data['counting_stats'].get('exercise_number', 1) + 1
    app_data['counting_stats']['exercise_number'] = esnum
    global overall_settings_changed
    overall_settings_changed = True
    print(_('Ciao per ora. Torniamo al menu principale.'))
    return

def MistakesCollectorInStrings(right, received):
    differences = []
    s = difflib.SequenceMatcher(None, right, received)
    for tag, i1, i2, j1, j2 in s.get_opcodes():
        if tag == 'replace' or tag == 'delete':
            differences.extend(right[i1:i2])
        elif tag == 'insert':
            differences.extend(received[j1:j2])
    return ''.join(differences)

def AlwaysRight(sent_items, error_counts_dict):
    letters_sent = set(''.join(sent_items))
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
    if seconds > 0 or not parts: # Show seconds if it's the only thing or > 0
        part = _("{count} secondi") if seconds != 1 else _("{count} secondo")
        parts.append(part.format(count=seconds))

    if len(parts) == 1:
        return parts[0]

    return ", ".join(parts[:-1]) + " " + _("e") + " " + parts[-1]

def RxingContest(menu_config_scelta):
    global overall_speed, overall_pitch, overall_dashes, overall_spaces, overall_dots, overall_volume, overall_ms, overall_fs, overall_wave, SAMPLE_RATES, MDL, app_data, overall_settings_changed

    print(_("\n=== MODALITÀ CONTEST ==="))
    print(_("Simulazione scambio rapido: Call + 5NN + Serial"))
    
    # Setup durata
    duration_type = menu(prompt=_("Scegli la durata:"), options=[_("Numero di QRZ"), _("Tempo (minuti)")])
    limit = 0
    if duration_type == 1:
        limit = dgt(prompt=_("Quanti QRZ? "), kind='i', imin=5, imax=500, default=50)
    else:
        limit = dgt(prompt=_("Quanti minuti? "), kind='i', imin=1, imax=60, default=10)

def RxingContest(menu_config_scelta):
    global overall_speed, overall_pitch, overall_dashes, overall_spaces, overall_dots, overall_volume, overall_ms, overall_fs, overall_wave, SAMPLE_RATES, MDL, app_data, overall_settings_changed

    print(_("\n=== MODALITÀ CONTEST ==="))
    print(_("Simulazione scambio rapido: Call + 5NN + Serial"))
    
    # Setup durata
    duration_type = menu(prompt=_("Scegli la durata:"), options=[_("Numero di QRZ"), _("Tempo (minuti)")])
    limit = 0
    if duration_type == 1:
        limit = dgt(prompt=_("Quanti QRZ? "), kind='i', imin=5, imax=500, default=50)
    else:
        limit = dgt(prompt=_("Quanti minuti? "), kind='i', imin=1, imax=60, default=10)

    print(_("Comandi rapidi: PgUp/PgDn (WPM), F5 (Call), F6 (Serial), F7 (Rpt), Alt+W (Wipe), ESC (Exit), Enter (Check)"))
    key(_("Premi un tasto per iniziare..."))

    start_time = dt.datetime.now()
    session_calls = 0
    correct_calls = 0
    
    # Stats trackers
    item_details = []
    sent_chars_detail_this_session = {}
    char_error_counts = {}
    total_mistakes_calculated = 0
    minwpm = 100
    maxwpm = 0
    sum_wpm = 0
    callssend = []
    callsget = []
    active_exerctime = dt.timedelta(0) # Approssimato
    
    import threading
    import queue
    
    input_queue = queue.Queue()
    stop_event = threading.Event()
    current_modifiers = set()

    def on_press(key):
        if stop_event.is_set():
            return False
        try:
            if key in {keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r}:
                current_modifiers.add('alt')
            input_queue.put(('press', key))
        except Exception:
            pass

    def on_release(key):
        try:
            if key in {keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r}:
                if 'alt' in current_modifiers:
                    current_modifiers.remove('alt')
        except Exception:
            pass

    listener = keyboard.Listener(on_press=on_press, on_release=on_release, suppress=True)
    listener.start()

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
            serial = int(round(1 + random.random() * (elapsed_minutes if elapsed_minutes > 0.1 else 0.1) * skill))
            
            # Messages
            msg_full = f"{qrz} 5NN {serial}"
            msg_call = qrz
            msg_serial = str(serial)
            
            callssend.append(msg_full)
            
            # Update sent chars stats
            for ch in msg_full:
                if ch.isalnum(): # Count only alphanumerics usually
                     sent_chars_detail_this_session[ch] = sent_chars_detail_this_session.get(ch, 0) + 1
            
            # Variations
            this_speed = overall_speed * (1 + random.uniform(-0.1, 0.1))
            this_pitch = random.randint(350, 950) # Random pitch per QSO

            # Track WPM
            if this_speed < minwpm: minwpm = this_speed
            if this_speed > maxwpm: maxwpm = this_speed
            sum_wpm += this_speed
            
            l, s, p = overall_dashes, overall_spaces, overall_dots
            if random.random() < 0.2:
                # Manual Keying Simulation
                l = int(l * random.uniform(0.8, 1.2))
                s = int(s * random.uniform(0.8, 1.2))
                p = int(p * random.uniform(0.8, 1.2))
            
            # Helper for playing CW
            def play_cw(msg_to_play):
                 threading.Thread(target=CWzator, kwargs={
                    'msg': msg_to_play, 'wpm': this_speed, 'l': l, 's': s, 'p': p, 
                    'pitch': this_pitch, 'vol': overall_volume, 'ms': overall_ms, 
                    'fs': SAMPLE_RATES[overall_fs], 'wv': overall_wave
                }).start()

            # Play initial full message
            play_cw(msg_full)
            
            # Input Loop
            item_done = False
            attempts = 5
            current_buffer = []
            print(f"\rRX #{session_calls+1}: ", end='', flush=True)
            
            item_start_time = dt.datetime.now()

            while not item_done and attempts > 0:
                try:
                    event_type, event_key = input_queue.get(timeout=0.1)
                    
                    if event_key == keyboard.Key.esc:
                        stop_event.set()
                        return

                    elif event_key == keyboard.Key.enter:
                        typed = "".join(current_buffer).upper().strip()
                        print() 
                        
                        target_call = qrz
                        target_serial = str(serial)
                        
                        # Parsing
                        tokens = typed.split()
                        user_call = ""
                        user_serial = ""
                        
                        if len(tokens) >= 2:
                            user_call = tokens[0] 
                            user_serial = tokens[-1] 
                        elif len(tokens) == 1:
                            if tokens[0].isdigit():
                                user_serial = tokens[0]
                            else:
                                user_call = tokens[0]
                        
                        # Check correctness
                        call_ok = (user_call == target_call)
                        serial_ok = (user_serial == target_serial)
                        
                        if call_ok and serial_ok:
                            # Correct
                            threading.Thread(target=CWzator, kwargs={'msg': "R", 'wpm': 35, 'pitch': 800, 'l':l, 's':s, 'p':p, 'vol':overall_volume, 'ms':overall_ms, 'fs':SAMPLE_RATES[overall_fs], 'wv':overall_wave}).start()
                            correct_calls += 1
                            callsget.append(msg_full)
                            item_details.append({'wpm': this_speed, 'correct': True})
                            item_done = True
                        else:
                            # Wrong
                            item_details.append({'wpm': this_speed, 'correct': False})
                            
                            # Track specific errors (simplified: diff of whole strings if both wrong, or specific parts)
                            # To be precise: accumulate mistakes chars
                            # Error Call
                            if not call_ok:
                                mistakes = MistakesCollectorInStrings(target_call, user_call)
                                for m in mistakes:
                                    char_error_counts[m] = char_error_counts.get(m, 0) + 1
                                    total_mistakes_calculated += 1
                            if not serial_ok:
                                mistakes = MistakesCollectorInStrings(target_serial, user_serial)
                                for m in mistakes:
                                    char_error_counts[m] = char_error_counts.get(m, 0) + 1
                                    total_mistakes_calculated += 1

                            attempts -= 1
                            if attempts == 0:
                                print(f" {msg_full}")
                                play_cw(msg_full)
                                item_done = True
                            else:
                                if not call_ok and not serial_ok:
                                     threading.Thread(target=CWzator, kwargs={'msg': "?", 'wpm': 35, 'pitch': 400, 'l':l, 's':s, 'p':p, 'vol':overall_volume, 'ms':overall_ms, 'fs':SAMPLE_RATES[overall_fs], 'wv':overall_wave}).start()
                                     print(f"\rRX #{session_calls+1} (Rpt {attempts}): ", end='', flush=True)
                                elif not call_ok:
                                     threading.Thread(target=CWzator, kwargs={'msg': "CALL?", 'wpm': 35, 'pitch': 400, 'l':l, 's':s, 'p':p, 'vol':overall_volume, 'ms':overall_ms, 'fs':SAMPLE_RATES[overall_fs], 'wv':overall_wave}).start()
                                     print(f"\rRX #{session_calls+1} (Call? {attempts}): {user_call if user_call else '_'} {target_serial}", end='', flush=True)
                                elif not serial_ok:
                                     threading.Thread(target=CWzator, kwargs={'msg': "NR?", 'wpm': 35, 'pitch': 400, 'l':l, 's':s, 'p':p, 'vol':overall_volume, 'ms':overall_ms, 'fs':SAMPLE_RATES[overall_fs], 'wv':overall_wave}).start()
                                     print(f"\rRX #{session_calls+1} (Nr? {attempts}): {target_call} {user_serial if user_serial else '_'}", end='', flush=True)

                        current_buffer = []

                    elif event_key == keyboard.Key.backspace:
                        if current_buffer:
                            current_buffer.pop()
                            print(f"\rRX #{session_calls+1}: {''.join(current_buffer)}  ", end=f"\rRX #{session_calls+1}: {''.join(current_buffer)}", flush=True)

                    elif event_key == keyboard.Key.page_up:
                        overall_speed += 2
                        print(f" [WPM: {overall_speed}] ", end='', flush=True)

                    elif event_key == keyboard.Key.page_down:
                        overall_speed = max(5, overall_speed - 2)
                        print(f" [WPM: {overall_speed}] ", end='', flush=True)
                        
                    elif event_key == keyboard.Key.f7:
                         play_cw(msg_full)
                    
                    elif event_key == keyboard.Key.f5: # Repeat Call
                         play_cw(msg_call)

                    elif event_key == keyboard.Key.f6: # Repeat Serial
                         play_cw(msg_serial)
                    
                    # Alt+W check
                    elif hasattr(event_key, 'char') and event_key.char == 'w' and 'alt' in current_modifiers:
                        current_buffer = []
                        print(f"\rRX #{session_calls+1}: {' '*20}", end=f"\rRX #{session_calls+1}: ", flush=True)

                    elif hasattr(event_key, 'char') and event_key.char:
                        if event_key.char.isalnum() or event_key.char == ' ':
                            current_buffer.append(event_key.char)
                            print(event_key.char, end='', flush=True)

                except queue.Empty:
                    pass
            
            active_exerctime += (dt.datetime.now() - item_start_time)
            session_calls += 1
            pass 

    finally:
        stop_event.set()
        listener.stop()
        
        # --- SALVATAGGIO STATISTICHE (Logica completa come in Rxing) ---
        elapsed_total = (dt.datetime.now() - start_time).total_seconds()
        wrong_calls = session_calls - correct_calls
        
        # 1. Update totali
        stats = app_data['rxing_stats_qrz']
        stats['sessions'] += 1
        stats['total_calls'] += session_calls
        stats['total_correct'] += correct_calls
        stats['total_wrong_items'] += wrong_calls
        stats['total_time_seconds'] += elapsed_total
        
        # 2. Dati storici dettagliati
        avg_wpm_calc = sum_wpm / session_calls if session_calls > 0 else 0
        send_char = sum(sent_chars_detail_this_session.values())
        
        session_data_for_history = {
            'timestamp_iso': start_time.isoformat(),
            'duration_seconds': active_exerctime.total_seconds(),
            'rwpm_min': minwpm if session_calls > 0 else 0,
            'rwpm_max': maxwpm,
            'rwpm_avg': avg_wpm_calc,
            'items_sent_session': session_calls,
            'items_correct_session': correct_calls,
            'item_details': item_details,
            'chars_sent_session': send_char,
            'errors_detail_session': char_error_counts,
            'total_errors_chars_session': total_mistakes_calculated,
            'sent_chars_detail_session': sent_chars_detail_this_session
        }

        # 3. Gestione log storico
        historical_data = app_data['historical_rx_data_qrz']
        historical_rx_log = historical_data.get('sessions_log', [])
        historical_rx_log.append(session_data_for_history)
        
        # Rotazione
        historical_settings = app_data['historical_rx_settings']
        g = historical_settings.get('max_sessions_to_keep', HISTORICAL_RX_MAX_SESSIONS_DEFAULT)
        while len(historical_rx_log) > g:
            historical_rx_log.pop(0)
            
        historical_data['sessions_log'] = historical_rx_log
        
        # Aggiornamento contatori report (semplificato)
        historical_data['chars_since_last_report'] = historical_data.get('chars_since_last_report', 0) + send_char
        
        overall_settings_changed = True

        print(_("\nSessione terminata. Corretti: {} su {}").format(correct_calls, session_calls))
        print(_("Dati salvati in statistiche QRZ (inclusi errori per carattere)."))
        key(_("Premi un tasto per tornare al menu..."))

def Rxing():
    global app_data, overall_settings_changed, overall_speed, words, customized_set
    print(_("\nE' il momento giusto per un bell'esercizio di ricezione? Ottimo, allora sei nel posto giusto.\nIniziamo!\n\tCarico lo stato dei tuoi progressi e controllo il database del dizionario..."))
    with open(resource_path('words.txt'), 'r', encoding='utf-8') as file:
        words = file.readlines()
        words = [line.strip() for line in words]
        print(_('Dizionario delle parole caricato con {word_count} parole.').format(word_count=len(words)))

    # Sposta la selezione della modalità qui, prima della visualizzazione delle statistiche
    menu_config_scelta = seleziona_modalita_rx()
    if not menu_config_scelta:
        return

    # Estrai i parametri della sessione dalla scelta dell'utente
    active_states = menu_config_scelta['active_switcher_states']

    if active_states.get('contest'):
        RxingContest(menu_config_scelta)
        return

    parole_filtrate_per_sessione = menu_config_scelta['parole_filtrate_list']
    custom_set_attivo_per_sessione = menu_config_scelta['custom_set_string_active']
    lunghezza_gruppo_per_generati = menu_config_scelta['group_length_for_generated']

    # Determina la categoria (words, chars, qrz)
    category_key = ""
    # La logica è che se le "parole" sono attive, è un esercizio di parole.
    # Altrimenti, se "qrz" è attivo, è un esercizio di qrz.
    # Altrimenti, è un esercizio di caratteri/misto.
    if active_states.get('parole'):
        category_key = "words"
    elif active_states.get('qrz'):
        category_key = "qrz"
    else: # Qualsiasi altra combinazione (lettere, numeri, simboli, custom, misto)
        category_key = "chars"

    # Seleziona i dizionari di statistiche e dati storici corretti per la sessione corrente
    current_rx_stats = app_data[f'rxing_stats_{category_key}']
    current_historical_data = app_data[f'historical_rx_data_{category_key}']
    historical_settings = app_data['historical_rx_settings'] # Le impostazioni sono condivise per tutte le categorie

    # Ora usa current_rx_stats e current_historical_data per il resto della funzione

    totalcalls = current_rx_stats.get('total_calls', 0)
    sessions = current_rx_stats.get('sessions', 0) # Inizializzato a 0 in DEFAULT_DATA
    totalget = current_rx_stats.get('total_correct', 0)
    totalwrong = current_rx_stats.get('total_wrong_items', 0)
    totaltime_seconds = current_rx_stats.get('total_time_seconds', 0.0)
    totaltime = dt.timedelta(seconds=totaltime_seconds)
    formatted_time = format_duration(totaltime)
    
    # Messaggio di benvenuto aggiornato
    print(_('Ho recuperato i tuoi dati dal disco per gli esercizi di {category_name}, quindi:\nLa tua attuale velocità WPM è {wpm} e hai svolto {sessions} sessioni.\nTi ho inviato {totalcalls} pseudo-call o gruppi e ne hai ricevuti correttamente {totalget}, mentre {totalwrong} li hai copiati male.\nIl tempo totale speso su questo esercizio è stato di {totaltime}.').format(
        category_name=_('parole') if category_key == 'words' else _('caratteri/misto') if category_key == 'chars' else 'QRZ',
        wpm=overall_speed, 
        sessions=sessions, # Non più sessions - 1, perché sessions conterà le sessioni completate
        totalcalls=totalcalls, 
        totalget=totalget, 
        totalwrong=totalwrong, 
        totaltime=formatted_time))
    
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
    max_sessions_to_keep = historical_settings.get('max_sessions_to_keep', HISTORICAL_RX_MAX_SESSIONS_DEFAULT)
    report_interval = historical_settings.get('report_interval', HISTORICAL_RX_REPORT_INTERVAL)

    overall_speed = dgt(prompt=_('Vuoi cambiare la velocità in WPM? Invio per accettare {wpm}> ').format(wpm=overall_speed), kind='i', imin=10, imax=85, default=overall_speed)
    rwpm = overall_speed
    _clear_screen_ansi()
    active_labels_for_display = []
    for item_cfg_ks in RX_SWITCHER_ITEMS:
        if active_states.get(item_cfg_ks['key_state']):
            active_labels_for_display.append(item_cfg_ks['key_state'].capitalize())
    if not active_labels_for_display:
        kindstring = 'N/A'
    elif len(active_labels_for_display) == 1:
        kindstring = active_labels_for_display[0]
    else:
        kindstring = _('Misto ({types})').format(types=', '.join(active_labels_for_display))
    how_many_calls = dgt(prompt=_('\nQuanti ne vuoi ricevere? (INVIO per infinito)> '), kind='i', imin=10, imax=1000, default=0)
    tmp_fix_speed = key(_('Vuoi che il cw rimanga alla stessa velocità?\t(y|n)> ')).lower()
    if tmp_fix_speed == 'y':
        fix_speed = True
    else:
        fix_speed = False
    print(_("Fai molta attenzione adesso.\n\tDigita il {kindstring} che ascolti.\nBattendo invio a vuoto (o aggiungendo un ?) avrai l'opportunità di un secondo tentativo\n\tPer terminare: digita semplicemente un '.' (punto) seguito da dal tasto invio.\n\t\tBUON DIVERTIMENTO!\n\tPremi un tasto quando sei pronto per iniziare.").format(kindstring=kindstring))
    attesa = key()
    print(_('Iniziamo la sessione {sessions}!').format(sessions=sessions + 1))
    starttime = dt.datetime.now()
    active_exerctime = dt.timedelta(0)
    total_pause_time = dt.timedelta(0)
    while True:
        total_wait_duration_for_item = dt.timedelta(0)
        if how_many_calls > 0 and len(callssend) >= how_many_calls:
            break
        qrz_to_send = genera_singolo_item_esercizio_misto(active_states, lunghezza_gruppo_per_generati, custom_set_attivo_per_sessione, parole_filtrate_per_sessione)
        if qrz_to_send is None or qrz_to_send == 'ERROR_NO_VALID_TYPES':
            print(_("Errore: Impossibile generare item per l'esercizio con le selezioni attuali. Controlla le impostazioni del menu Rx."))
            break
        pitch = random.randint(250, 1050)
        avg_wpm_display = average_rwpm / len(callsget) if len(callsget) else rwpm
        prompt = _('S{sessions}-#{calls} - WPM{rwpm:.2f}/{avg_wpm_display:.2f} - +{correct_count}/-{wrong_count}> ').format(avg_wpm_display=avg_wpm_display, correct_count=len(callsget), wrong_count=len(callswrong), sessions=sessions + 1, calls=calls, rwpm=rwpm)
        plo, rwpm = CWzator(msg=qrz_to_send, wpm=overall_speed, pitch=pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
        wait_start_1 = dt.datetime.now()
        guess = dgt(prompt=prompt, kind='s', smin=0, smax=64)
        wait_end_1 = dt.datetime.now()
        total_wait_duration_for_item += wait_end_1 - wait_start_1 
        if guess == '.':
            break
        needs_processing = True
        if guess == '' or guess.endswith('?'):
            repeatedflag = True
            partial_input = ''
            prompt_indicator = '% '
            if guess.endswith('?'):
                partial_input = guess[:-1]
                prompt_indicator = _('% {partial_input}').format(partial_input=partial_input)
            prompt = _('S{sessions}-#{calls} - WPM{rwpm:.2f}/{:.2f} - +{}/-{} - {prompt_indicator}').format(average_rwpm / len(callsget) if len(callsget) else rwpm, len(callsget), len(callswrong), sessions=sessions + 1, calls=calls, rwpm=rwpm, prompt_indicator=prompt_indicator)
            plo, rwpm = CWzator(msg=qrz_to_send, wpm=overall_speed, pitch=pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
            wait_start_2 = dt.datetime.now()
            new_guess = dgt(prompt=prompt, kind='s', smin=0, smax=64)
            wait_end_2 = dt.datetime.now()
            total_wait_duration_for_item += wait_end_2 - wait_start_2
            if new_guess == '.':
                needs_processing = False
                break
            else:
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
                tplo, trwpm = CWzator(msg='r _ _ ', wpm=overall_speed, pitch=pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave, sync=True)
                callsget.append(original_qrz)
                average_rwpm += rwpm
                item_details.append({'wpm': rwpm, 'correct': True})
                if repeatedflag:
                    callsrepeated += 1
                if not fix_speed and overall_speed < 100:
                    overall_speed += 1
            else:
                callswrong.append(original_qrz)
                item_details.append({'wpm': rwpm, 'correct': False})
                tplo, trwpm = CWzator(msg='? _ _ ', wpm=overall_speed, pitch=pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave, sync=True)
                diff = MistakesCollectorInStrings(original_qrz, guess)
                diff_ratio = (1 - difflib.SequenceMatcher(None, original_qrz, guess).ratio()) * 100
                print(_('TX: {} RX: {} <>: {} RT: {}').format(original_qrz.upper(), guess.upper(), diff.upper(), int(diff_ratio)))
                dz_mistakes[len(callssend)] = (original_qrz, guess)
                if not fix_speed and overall_speed > 15:
                    overall_speed -= 1
            calls += 1
            if rwpm > maxwpm:
                maxwpm = rwpm
            if rwpm < minwpm:
                minwpm = rwpm
            repeatedflag = False
    print(_('È finita! Ora vediamo cosa abbiamo ottenuto.'))
    if len(callssend) >= 10:
        send_char = sum((len(j) for j in callssend))
        sent_chars_detail_this_session = {}
        for item_str in callssend:
            for char_sent in item_str:
                sent_chars_detail_this_session[char_sent] = sent_chars_detail_this_session.get(char_sent, 0) + 1
        total_sent_processed = len(callssend)
        percentage_correct = len(callsget) * 100 / total_sent_processed if total_sent_processed > 0 else 0
        print(_('In questa sessione #{sessions}, ti ho inviato {calls} {kindstring} e ne hai ricevuti {callsget_len}: {percentage:.1f}%').format(sessions=sessions, calls=total_sent_processed, kindstring=kindstring, callsget_len=len(callsget), percentage=percentage_correct))
        first_shot_correct = len(callsget) - callsrepeated
        first_shot_percentage = first_shot_correct * 100 / len(callsget) if len(callsget) > 0 else 0
        repetitions_percentage = callsrepeated * 100 / len(callsget) if len(callsget) > 0 else 0
        print(_('\t{first_shot} di questi sono stati ricevuti al primo ascolto: {first_shot_percentage:.1f}%').format(first_shot=len(callsget) - callsrepeated, first_shot_percentage=(len(callsget) - callsrepeated) * 100 / len(callsget)))
        print(_('\tmentre {repetitions} {kindstring} al secondo tentativo: {repetitions_percentage:.1f}%.').format(repetitions=callsrepeated, kindstring=kindstring, repetitions_percentage=callsrepeated * 100 / len(callsget)))
        print(_('Durante la sessione, la tua velocità minima è stata {minwpm:.2f}, la massima di {maxwpm:.2f}: pari ad una variazione di {range_wpm:.2f} WPM.\n\tLa velocità media di ricezione è di: {average_wpm:.2f} WPM.').format(minwpm=minwpm, maxwpm=maxwpm, range_wpm=maxwpm - minwpm, average_wpm=average_rwpm / len(callsget)))
        avg_wpm_calc = average_rwpm / len(callsget) if len(callsget) > 0 else overall_speed
        char_error_counts = {}
        total_mistakes_calculated = 0
        for right_str, received_str in dz_mistakes.values():
            s = difflib.SequenceMatcher(None, right_str, received_str)
            for tag, i1, i2, j1, j2 in s.get_opcodes():
                if tag == 'replace':
                    for char in right_str[i1:i2]:
                        char_error_counts[char] = char_error_counts.get(char, 0) + 1
                        total_mistakes_calculated += 1
                elif tag == 'delete':
                    for char in right_str[i1:i2]:
                        char_error_counts[char] = char_error_counts.get(char, 0) + 1
                        total_mistakes_calculated += 1
                elif tag == 'insert':
                    for char in received_str[j1:j2]:
                        char_error_counts[char] = char_error_counts.get(char, 0) + 1
                        total_mistakes_calculated += 1
        print(_('Carattere: errori = Intervallo di Confidenza Errore (Wilson)'))
        if total_mistakes_calculated > 0:
            sorted_errors = sorted(char_error_counts.items(), key=lambda item: (-item[1], item[0]))
            for char, errori in sorted_errors:
                inviati = sent_chars_detail_this_session.get(char, 0)
                limite_inferiore = wilson_score_lower_bound(errori, inviati) * 100
                limite_superiore = wilson_score_upper_bound(errori, inviati) * 100
                print(_("    '{char_display}': {errori} errori su {inviati} invii. Tasso errore stimato: [{inf:.1f}% - {sup:.1f}%]").format(
                    char_display=char.upper(), 
                    errori=errori, 
                    inviati=inviati, 
                    inf=limite_inferiore, 
                    sup=limite_superiore
                ))
            mistake_percentage = total_mistakes_calculated * 100 / send_char if send_char > 0 else 0
            print(_('\nErrori totali: {global_mistakes} su {send_char} = {mistake_percentage:.2f}%').format(global_mistakes=total_mistakes_calculated, send_char=send_char, mistake_percentage=mistake_percentage))
            good_letters = AlwaysRight(callssend, char_error_counts)
            print(_('\nCaratteri mai sbagliati: {good_letters}').format(good_letters=' '.join(sorted(good_letters)).upper()))
        else:
            print(_('Nessun errore sui caratteri registrato in questa sessione.'))
        historical_rx_settings = app_data.get('historical_rx_settings', {})
        max_sessions_to_keep = historical_rx_settings.get('max_sessions_to_keep', HISTORICAL_RX_MAX_SESSIONS_DEFAULT)
        report_interval = historical_rx_settings.get('report_interval', HISTORICAL_RX_REPORT_INTERVAL)
        f = open('CWapu_Diary.txt', 'a', encoding='utf-8')
        print(_('Rapporto salvato su CW_Diary.txt'))
        date = _('{}/{}/{}').format(lt()[0], lt()[1], lt()[2])
        time = _('{}, {}').format(lt()[3], lt()[4])
        f.write(_('\nEsercizio di ricezione #{sessions} eseguito il {date} alle {time} minuti:\n').format(sessions=sessions, date=date, time=time))
        f.write(_('In questa sessione #{sessions}, ti ho inviato {calls} {kindstring} e ne hai ricevuti {callsget_len}: {percentage:.1f}%').format(sessions=sessions, calls=total_sent_processed, kindstring=kindstring, callsget_len=len(callsget), percentage=percentage_correct) + '\n')
        f.write(_('\t{first_shot} di questi sono stati ricevuti al primo ascolto: {first_shot_percentage:.1f}%').format(first_shot=first_shot_correct, first_shot_percentage=first_shot_percentage) + '\n')
        f.write(_('\tmentre {repetitions} {kindstring} al secondo tentativo: {repetitions_percentage:.1f}%.').format(repetitions=callsrepeated, kindstring=kindstring, repetitions_percentage=repetitions_percentage) + '\n')
        f.write(_('Durante la sessione, la tua velocità minima è stata {minwpm:.2f}, la massima di {maxwpm:.2f}: pari ad una variazione di {range_wpm:.2f} WPM.\n\tLa velocità media di ricezione è di: {average_wpm:.2f} WPM.').format(minwpm=minwpm, maxwpm=maxwpm, range_wpm=maxwpm - minwpm, average_wpm=avg_wpm_calc) + '\n')
        f.write(_('Carattere: errori = Intervallo di Confidenza Errore (Wilson)'))
        if total_mistakes_calculated > 0:
            sorted_errors = sorted(char_error_counts.items(), key=lambda item: (-item[1], item[0]))
            for char, errori in sorted_errors:
                inviati = sent_chars_detail_this_session.get(char, 0)
                limite_inferiore = wilson_score_lower_bound(errori, inviati) * 100
                limite_superiore = wilson_score_upper_bound(errori, inviati) * 100
                f.write(_("    '{char_display}': {errori} errori su {inviati} invii. Tasso errore stimato: [{inf:.1f}% - {sup:.1f}%]").format(
                    char_display=char.upper(), 
                    errori=errori, 
                    inviati=inviati, 
                    inf=limite_inferiore, 
                    sup=limite_superiore
                ))
            f.write('\n')
            f.write(_('\nErrori totali: {global_mistakes} su {send_char} = {mistake_percentage:.2f}%').format(global_mistakes=total_mistakes_calculated, send_char=send_char, mistake_percentage=mistake_percentage))
            f.write(_('\nCaratteri mai sbagliati: {good_letters}').format(good_letters=' '.join(sorted(good_letters)).upper()))
        else:
            f.write('\n' + _('Nessun errore sui caratteri registrato in questa sessione.') + '\n')
        f.write(_('\nElenco delle parole copiate male:'))
        for k, v in sorted(dz_mistakes.items()):
            rslt = MistakesCollectorInStrings(v[0], v[1])
            f.write(_('\n\t({k}) TX: {tx}, RX: {rx}, DIF: {dif};').format(k=k, tx=v[0].upper(), rx=v[1].upper(), dif=rslt.upper()))
        if report_interval > 0:
            chars_done = app_data[f'historical_rx_data_{category_key}'].get('chars_since_last_report', 0) + send_char
            chars_target = report_interval
            percentage_done = chars_done / chars_target * 100 if chars_target > 0 else 0.0
            chars_missing = chars_target - chars_done
            print(_('Completamento sezione corrente:\n+{s} -> ({x} / {y}) = {z}% (-{w}) alla prossima generazione.').format(s=send_char, x=chars_done, y=chars_target, z=f'{percentage_done:.2f}', w=chars_missing))
        else:
            print(_('La generazione automatica dei report è disabilitata.'))
        nota = dgt(prompt=_('\nNota su questo esercizio: '), kind='s', smin=0, smax=512)
        if nota != '':
            f.write(_('Nota: {nota}\n***\n').format(nota=nota))
        else:
            f.write('\n' + _('Nota: nessuna') + '\n***\n')
        f.close()
    else:
        print(_('Hai ricevuto troppo pochi {kindstring} per generare statistiche consistenti.').format(kindstring=kindstring))
    current_session_items = len(callssend)
    current_session_correct = len(callsget)
    current_session_wrong = len(dz_mistakes)

    new_totalcalls = current_rx_stats['total_calls'] + current_session_items
    new_totalget = current_rx_stats['total_correct'] + current_session_correct
    new_totalwrong = current_rx_stats['total_wrong_items'] + current_session_wrong
    new_totaltime = dt.timedelta(seconds=current_rx_stats['total_time_seconds']) + active_exerctime
    
    current_rx_stats.update({
        'total_calls': new_totalcalls,
        'sessions': current_rx_stats['sessions'] + 1,
        'total_correct': new_totalget,
        'total_wrong_items': new_totalwrong,
        'total_time_seconds': new_totaltime.total_seconds()
    })
    
    corrected_item_details = [{'rwpm': item['wpm'], 'correct': item['correct']} for item in item_details]
    session_data_for_history = {
        'timestamp_iso': starttime.isoformat(),
        'duration_seconds': active_exerctime.total_seconds(),
        'rwpm_min': minwpm,
        'rwpm_max': maxwpm,
        'rwpm_avg': avg_wpm_calc,
        'items_sent_session': len(callssend),
        'items_correct_session': len(callsget),
        'item_details': corrected_item_details,
        'chars_sent_session': send_char,
        'errors_detail_session': char_error_counts,
        'total_errors_chars_session': total_mistakes_calculated,
        'sent_chars_detail_session': sent_chars_detail_this_session
    }

    historical_rx_log = current_historical_data.get('sessions_log', [])
    historical_rx_log.append(session_data_for_history)

    x = len(historical_rx_log)
    g = historical_settings.get('max_sessions_to_keep', HISTORICAL_RX_MAX_SESSIONS_DEFAULT)
    
    while len(historical_rx_log) > g:
        sessione_eliminata = historical_rx_log.pop(0)
        data_sessione_str = sessione_eliminata.get('timestamp_iso', 'N/D')
        data_sessione_dt = dt.datetime.fromisoformat(data_sessione_str).strftime('%Y-%m-%d %H:%M')
        durata_sessione = int(sessione_eliminata.get('duration_seconds', 0))
        contenuto_sessione = sessione_eliminata.get('chars_sent_session', 0)
        print(_("Sessione del {data}, durata {durata}s, contenuto {contenuto} caratteri, eliminata dalla coda degli esercizi di {category_name}.").format(
            data=data_sessione_dt, 
            durata=durata_sessione, 
            contenuto=contenuto_sessione,
            category_name=_('parole') if category_key == 'words' else _('caratteri/misto') if category_key == 'chars' else 'QRZ'))

    current_historical_data['chars_since_last_report'] = current_historical_data.get('chars_since_last_report', 0) + send_char
    current_historical_data['sessions_log'] = historical_rx_log

    if report_interval > 0 and current_historical_data['chars_since_last_report'] >= report_interval:
        print(_('Generazione report storico in corso...'))
        sessions_log = current_historical_data.get('sessions_log', [])
        chars_to_account_for = current_historical_data['chars_since_last_report']
        sessions_for_this_report = []
        accumulated_chars = 0
        for session in reversed(sessions_log):
            sessions_for_this_report.insert(0, session)
            accumulated_chars += session.get('chars_sent_session', 0)
            if accumulated_chars >= chars_to_account_for:
                break
        new_report_aggregates = generate_historical_rx_report(sessions_for_this_report, category_key)
        if new_report_aggregates:
            historical_reports = current_historical_data.get('historical_reports', [])
            historical_reports.append(new_report_aggregates)
            current_historical_data['historical_reports'] = historical_reports
        chars_in_this_report = accumulated_chars
        overshoot = chars_in_this_report - report_interval
        current_historical_data['chars_since_last_report'] = max(0, overshoot)
    
    overall_settings_changed = True
    
    duration_str = str(active_exerctime).split('.')[0]
    print(_('\nSessione {session_number}, durata attiva: {duration} è stata salvata su disco.').format(session_number=current_rx_stats['sessions'], duration=duration_str))
    if total_pause_time.total_seconds() > 0:
        pause_str = str(total_pause_time).split('.')[0]
        print(_('\t(Tempo totale in pausa rilevato: {pause_time})').format(pause_time=pause_str))
    print(_("L'archivio ora contiene {x} sessioni salvate per gli esercizi di {category_name}, ancora {g_minus_x} al raggiungimento del limite stabilito.").format(
        x=x, g_minus_x=g - x, category_name=_('parole') if category_key == 'words' else _('caratteri/misto') if category_key == 'chars' else 'QRZ'))
    return

def _calculate_aggregates(session_list):
    """
	Calcola statistiche aggregate da una lista di dati di sessione.
	Restituisce un dizionario con le statistiche aggregate.
	"""
    if not session_list:
        return {'num_sessions_in_block': 0, 'total_duration_seconds': 0.0, 'wpm_min_overall': 0, 'wpm_max_overall': 0, 'wpm_avg_overall_cpm_based': 0.0, 'total_items_sent': 0, 'total_items_correct': 0, 'total_chars_sent_overall': 0, 'aggregated_errors_detail': {}, 'total_errors_chars_overall': 0}
    total_duration_seconds = sum((s.get('duration_seconds', 0) for s in session_list))
    total_chars_sent_overall = sum((s.get('chars_sent_session', 0) for s in session_list))
    aggregated_sent_chars_detail = {}
    for s in session_list:
        for char, count in s.get('sent_chars_detail_session', {}).items():
            aggregated_sent_chars_detail[char] = aggregated_sent_chars_detail.get(char, 0) + count
    valid_min_wpms = [s.get('rwpm_min', 0) for s in session_list if s.get('rwpm_min', 0) > 0 and s.get('rwpm_min', 0) != 100]
    valid_max_wpms = [s.get('rwpm_max', 0) for s in session_list if s.get('rwpm_max', 0) > 0]
    wpm_min_overall = min(valid_min_wpms) if valid_min_wpms else 0
    wpm_max_overall = max(valid_max_wpms) if valid_max_wpms else 0
    if session_list:
        sum_of_session_avg_wpms = sum((s.get('rwpm_avg', 0.0) for s in session_list))
        wpm_avg_of_session_avgs = sum_of_session_avg_wpms / len(session_list)
    else:
        wpm_avg_of_session_avgs = 0.0
    total_items_sent = sum((s.get('items_sent_session', 0) for s in session_list))
    total_items_correct = sum((s.get('items_correct_session', 0) for s in session_list))
    aggregated_errors_detail = {}
    total_errors_chars_overall = 0
    for s in session_list:
        total_errors_chars_overall += s.get('total_errors_chars_session', 0)
        for char, count in s.get('errors_detail_session', {}).items():
            aggregated_errors_detail[char] = aggregated_errors_detail.get(char, 0) + count
    return {'num_sessions_in_block': len(session_list), 'total_duration_seconds': total_duration_seconds, 'wpm_min_overall': wpm_min_overall, 'wpm_max_overall': wpm_max_overall, 'wpm_avg_of_session_avgs': wpm_avg_of_session_avgs, 'total_items_sent': total_items_sent, 'total_items_correct': total_items_correct, 'total_chars_sent_overall': total_chars_sent_overall, 'aggregated_errors_detail': aggregated_errors_detail, 'total_errors_chars_overall': total_errors_chars_overall, 'aggregated_sent_chars_detail': aggregated_sent_chars_detail}

def generate_historical_rx_report(sessions_for_current_report, category_key):
    """
	Genera i report (HTML e grafico) per il blocco di sessioni fornito,
	confrontandoli con l'ultimo report storico salvato.
	Restituisce i dati aggregati del report corrente per poterli salvare.
	"""
    global app_data, app_language
    if not sessions_for_current_report:
        print(_('Nessuna sessione nel blocco corrente da riportare.'))
        return None
    current_aggregates = _calculate_aggregates(sessions_for_current_report)
    num_sessions_in_current_report = current_aggregates['num_sessions_in_block']
    
    historical_data = app_data.get(f'historical_rx_data_{category_key}', {})
    historical_settings = app_data.get('historical_rx_settings', {})

    full_sessions_log = historical_data.get('sessions_log', [])
    num_sessions_in_current_block = len(sessions_for_current_report)
    previous_aggregates = None
    if len(full_sessions_log) > num_sessions_in_current_block:
        num_previous_sessions = len(full_sessions_log) - num_sessions_in_current_block
        previous_block_sessions = full_sessions_log[:num_previous_sessions]
        if previous_block_sessions:
            previous_aggregates = _calculate_aggregates(previous_block_sessions)
    
    g_value = historical_settings.get('max_sessions_to_keep', HISTORICAL_RX_MAX_SESSIONS_DEFAULT)
    x_value = historical_settings.get('report_interval', HISTORICAL_RX_REPORT_INTERVAL)
    
    cat_name_file = category_key.capitalize()
    report_filename_base = _('CWapu_Historical_Statistics_{cat}_G_{g_value}_X_{x_value}.html').format(cat=cat_name_file, g_value=g_value, x_value=x_value)
    report_filename_full_path = os.path.join(USER_DATA_PATH, report_filename_base)
    
    cat_display_name = _('parole') if category_key == 'words' else _('caratteri/misto') if category_key == 'chars' else 'QRZ'
    
    try:
        with open(report_filename_full_path, 'w', encoding='utf-8') as f:
            f.write('<!DOCTYPE html>\n')
            f.write('<html lang="{html_lang}">\n'.format(html_lang=app_language[:2]))
            f.write('<head>\n')
            f.write('    <meta charset="UTF-8">\n')
            f.write(_('    <title>Report Statistiche Storiche Esercizi Rx ({cat}) G{g_value} X{x_value}</title>\n').format(cat=cat_display_name, g_value=g_value, x_value=x_value))
            f.write('    <style>\n')
            f.write("        body { background-color: #282c34; color: #e0e0e0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; }\n")
            f.write('        .container { max-width: 1200px; margin: auto; background-color: #333740; padding: 20px; border-radius: 8px; box-shadow: 0 0 15px rgba(0,0,0,0.5); }\n')
            f.write('        h1, h2, h3 { color: #61afef; border-bottom: 2px solid #61afef; padding-bottom: 5px; margin-top: 30px; }\n')
            f.write('        h1 { text-align: center; font-size: 2em; margin-bottom: 10px; }\n')
            f.write('        .report-subtitle { text-align: center; font-size: 0.9em; color: #abb2bf; margin-bottom: 5px; }\n')
            f.write('        .report-generation-time { text-align: center; font-size: 0.8em; color: #888; margin-bottom: 30px; }\n')
            f.write('        table { border-collapse: collapse; width: 100%; margin-top: 15px; margin-bottom: 30px; box-shadow: 0 0 10px rgba(0,0,0,0.3); }\n')
            f.write('        th, td { border: 1px solid #4b5260; padding: 10px; text-align: left; font-size: 0.9em; }\n')
            f.write('        th { background-color: #3a3f4b; color: #98c379; font-weight: bold; }\n')
            f.write('        tr:nth-child(even) { background-color: #383c44; }\n')
            f.write('        tr:hover { background-color: #484e59; }\n')
            f.write('        .good { color: #98c379; font-weight: bold; } /* Verde per miglioramenti */\n')
            f.write('        .bad { color: #e06c75; font-weight: bold; } /* Rosso per peggioramenti */\n')
            f.write('        .neutral { color: #e5c07b; } /* Giallo/Arancio per neutrali o minimi */\n')
            f.write('        .char-emphasis { font-weight: bold; color: #c678dd; } /* Viola per il carattere in analisi */\n')
            f.write('        .details-label { font-style: italic; color: #abb2bf; font-size: 0.85em; }\n')
            f.write('    </style>\n')
            f.write('</head>\n')
            f.write('<body>\n')
            f.write('    <div class="container">\n')
            f.write(_('<h1>CWAPU - Report Statistiche Storiche Esercizi Rx ({cat})</h1>\n').format(cat=cat_display_name))
            f.write(_('<p class="report-subtitle">Statistiche basate su {count} esercizi (G={g_value}, X={x_value})</p>\n').format(count=num_sessions_in_current_report, g_value=g_value, x_value=x_value))
            timestamp_now = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(_('<p class="report-generation-time">Report generato il: {timestamp_now}</p>\n').format(timestamp_now=timestamp_now))
            def get_delta_class(delta_value, higher_is_better=True, tolerance=0.01):
                if higher_is_better:
                    if delta_value > tolerance:
                        return 'good'
                    if delta_value < -tolerance:
                        return 'bad'
                else:
                    if delta_value < -tolerance:
                        return 'good'
                    if delta_value > tolerance:
                        return 'bad'
                return 'neutral'
            f.write(_('<h2>Statistiche Velocità Complessive</h2>\n'))
            f.write('<table>\n')
            f.write(_('  <thead><tr><th>Metrica</th><th>Valore Attuale</th>'))
            if previous_aggregates:
                f.write(_('<th>Valore Precedente</th><th>Variazione</th>'))
            f.write('</tr></thead>\n')
            f.write('  <tbody>\n')
            f.write(_('    <tr><td>WPM Min</td><td>{} WPM</td>').format(current_aggregates['wpm_min_overall']))
            if previous_aggregates:
                prev_val = previous_aggregates.get('wpm_min_overall', 0)
                delta = current_aggregates['wpm_min_overall'] - prev_val
                delta_class = get_delta_class(delta, higher_is_better=True)
                perc_delta_str = _(' ({}%)').format(delta / prev_val * 100) if prev_val != 0 else ''
                f.write(_('<td>{prev_val} WPM</td><td class="{delta_class}">{delta} WPM{perc_delta_str}</td>').format(prev_val=prev_val, delta_class=delta_class, delta=delta, perc_delta_str=perc_delta_str))
            f.write('</tr>\n')
            f.write(_('    <tr><td>WPM Max</td><td>{} WPM</td>').format(current_aggregates['wpm_max_overall']))
            if previous_aggregates:
                prev_val = previous_aggregates.get('wpm_max_overall', 0)
                delta = current_aggregates['wpm_max_overall'] - prev_val
                delta_class = get_delta_class(delta, higher_is_better=True)
                perc_delta_str = _(' ({}%)').format(delta / prev_val * 100) if prev_val != 0 else ''
                f.write(_('<td>{prev_val} WPM</td><td class="{delta_class}">{delta} WPM{perc_delta_str}</td>').format(prev_val=prev_val, delta_class=delta_class, delta=delta, perc_delta_str=perc_delta_str))
            f.write('</tr>\n')
            f.write(_('    <tr><td>WPM Medio (media delle sessioni)</td><td>{} WPM</td>').format(current_aggregates['wpm_avg_of_session_avgs']))
            if previous_aggregates:
                prev_val = previous_aggregates.get('wpm_avg_of_session_avgs', 0)
                delta = current_aggregates['wpm_avg_of_session_avgs'] - prev_val
                delta_class = get_delta_class(delta, higher_is_better=True)
                perc_delta_str = _(' ({}%)').format(delta / prev_val * 100) if prev_val != 0 else ''
                f.write(_('<td>{prev_val} WPM</td><td class="{delta_class}">{delta} WPM{perc_delta_str}</td>').format(prev_val=prev_val, delta_class=delta_class, delta=delta, perc_delta_str=perc_delta_str))
            f.write('</tr>\n')
            f.write('  </tbody>\n</table>\n')
            f.write(_('<h2>Statistiche Errori Complessive</h2>\n'))
            f.write('<table>\n')
            f.write(_('  <thead><tr><th>Metrica</th><th>Valore Attuale</th>'))
            if previous_aggregates:
                f.write(_('<th>Valore Precedente</th><th>Variazione</th>'))
            f.write('</tr></thead>\n')
            f.write('  <tbody>\n')
            f.write(_('    <tr><td>Caratteri totali inviati (nel blocco)</td><td>{}</td>').format(current_aggregates['total_chars_sent_overall']))
            if previous_aggregates:
                prev_val = previous_aggregates.get('total_chars_sent_overall', 0)
                delta = current_aggregates['total_chars_sent_overall'] - prev_val
                perc_delta_str = _(' ({}%)').format(delta / prev_val * 100) if prev_val != 0 else ''
                f.write(_('<td>{prev_val}</td><td>{delta} {perc_delta_str}</td>').format(prev_val=prev_val, delta=delta, perc_delta_str=perc_delta_str))
            f.write('</tr>\n')
            total_chars_curr = current_aggregates['total_chars_sent_overall']
            total_errs_curr = current_aggregates['total_errors_chars_overall']
            overall_error_rate_curr = total_errs_curr / total_chars_curr * 100 if total_chars_curr > 0 else 0.0
            f.write(_('    <tr><td>Tasso errore generale</td><td>{total_errs_curr} / {total_chars_curr} ({overall_error_rate_curr}%)</td>').format(total_errs_curr=total_errs_curr, total_chars_curr=total_chars_curr, overall_error_rate_curr=overall_error_rate_curr))
            if previous_aggregates:
                total_chars_prev = previous_aggregates.get('total_chars_sent_overall', 0)
                total_errs_prev = previous_aggregates.get('total_errors_chars_overall', 0)
                overall_error_rate_prev = total_errs_prev / total_chars_prev * 100 if total_chars_prev > 0 else 0.0
                delta_rate = overall_error_rate_curr - overall_error_rate_prev
                delta_class = get_delta_class(delta_rate, higher_is_better=False)
                f.write(_('<td>{total_errs_prev} / {total_chars_prev} ({overall_error_rate_prev}%)</td><td class="{delta_class}">{delta_rate} punti %</td>').format(total_errs_prev=total_errs_prev, total_chars_prev=total_chars_prev, overall_error_rate_prev=overall_error_rate_prev, delta_class=delta_class, delta_rate=delta_rate))
            f.write('</tr>\n')
            f.write('  </tbody>\n</table>\n')
            if current_aggregates.get('aggregated_errors_detail', {}):
                f.write(_('<h2>Dettaglio errori per carattere</h2>\n'))
                f.write('<table>\n')
                f.write(_('  <thead><tr><th>Carattere</th><th>Errori / Inviati</th><th style="text-align: center;">Intervallo Confidenza Errore (Wilson)</th></tr></thead>\n'))
                f.write('  <tbody>\n')
                sorted_errors = sorted(current_aggregates['aggregated_errors_detail'].items(), key=lambda item: (-item[1], item[0]))
                for char, count in sorted_errors:
                    errori = count
                    inviati = current_aggregates.get('aggregated_sent_chars_detail', {}).get(char, 0)
                    limite_inferiore = wilson_score_lower_bound(errori, inviati) * 100
                    limite_superiore = wilson_score_upper_bound(errori, inviati) * 100
                    f.write(_('     <tr><td class="char-emphasis">\'{}\'</td><td>{} su {} inv.</td><td colspan="2" style="text-align:center;">[{:.1f}% - {:.1f}%]</td></tr>\n').format(
                        char.upper(), 
                        errori, 
                        inviati, 
                        limite_inferiore, 
                        limite_superiore
                    ))
                f.write('  </tbody>\n</table>\n')
            if previous_aggregates and previous_aggregates.get('num_sessions_in_block', 0) > 0:
                f.write(_('<h2>Variazioni Dettaglio Errori per Carattere</h2>\n'))
                f.write(_('<p class="report-subtitle">Variazioni rispetto al blocco di {count} esercizi precedente</p>\n').format(count=previous_aggregates['num_sessions_in_block']))
                f.write('<table>\n')
                f.write(_('  <thead><tr><th>Carattere</th><th>Err. Att.</th><th>%Tot Att.</th><th>%Spec Att.</th><th>Err. Prec.</th><th>%Tot Prec.</th><th>%Spec Prec.</th><th>Δ% Tot. Caratt.</th><th>Δ% Caratt. Spec.</th></tr></thead>\n'))
                f.write('  <tbody>\n')
                all_error_chars_set = set(current_aggregates.get('aggregated_errors_detail', {}).keys()) | set(previous_aggregates.get('aggregated_errors_detail', {}).keys())
                if not all_error_chars_set:
                    f.write(_('    <tr><td colspan="9" style="text-align:center;">Nessun errore registrato in nessuno dei due blocchi di riferimento.</td></tr>\n'))
                else:
                    sorted_chars_for_variation = sorted(list(all_error_chars_set), key=lambda char_key: (-current_aggregates.get('aggregated_errors_detail', {}).get(char_key, 0), char_key))
                    for char_err in sorted_chars_for_variation:
                        curr_count = current_aggregates.get('aggregated_errors_detail', {}).get(char_err, 0)
                        total_chars_curr_block = current_aggregates.get('total_chars_sent_overall', 1)
                        curr_rate_vs_total_chars = curr_count / total_chars_curr_block * 100 if total_chars_curr_block > 0 else 0.0
                        curr_total_sent_of_this_char = current_aggregates.get('aggregated_sent_chars_detail', {}).get(char_err, 0)
                        curr_rate_vs_specific_char = curr_count / curr_total_sent_of_this_char * 100 if curr_total_sent_of_this_char > 0 else 0.0
                        prev_count = previous_aggregates.get('aggregated_errors_detail', {}).get(char_err, 0)
                        total_chars_prev_block = previous_aggregates.get('total_chars_sent_overall', 1)
                        prev_rate_vs_total_chars = prev_count / total_chars_prev_block * 100 if total_chars_prev_block > 0 else 0.0
                        prev_total_sent_of_this_char = previous_aggregates.get('aggregated_sent_chars_detail', {}).get(char_err, 0)
                        prev_rate_vs_specific_char = prev_count / prev_total_sent_of_this_char * 100 if prev_total_sent_of_this_char > 0 else 0.0
                        delta_rate_vs_total_chars = curr_rate_vs_total_chars - prev_rate_vs_total_chars
                        delta_rate_vs_specific_char = curr_rate_vs_specific_char - prev_rate_vs_specific_char
                        delta_total_class = get_delta_class(delta_rate_vs_total_chars, higher_is_better=False)
                        delta_specific_class = get_delta_class(delta_rate_vs_specific_char, higher_is_better=False)
                        f.write(_('     <tr><td class="char-emphasis">\'{}\'</td><td>{curr_count}</td><td>{curr_rate_vs_total_chars:.2f}%</td><td>{curr_rate_vs_specific_char:.2f}% <span class="details-label">(su {curr_sent_count} inv.)</span></td><td>{prev_count}</td><td>{prev_rate_vs_total_chars:.2f}%</td><td>{prev_rate_vs_specific_char:.2f}% <span class="details-label">(su {prev_sent_count} inv.)</span></td><td class="{delta_total_class}">{delta_rate_vs_total_chars:+.2f} %</td><td class="{delta_specific_class}">{delta_rate_vs_specific_char:+.2f} %</td></tr>\n').format(
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
                                    delta_rate_vs_specific_char=delta_rate_vs_specific_char
                                ))
                        f.write('  </tbody>\n</table>\n')
            f.write('    </div>\n')
            f.write('</body>\n')
            f.write('</html>\n')
            print(_('Report storico salvato in: {filename}').format(filename=report_filename_full_path))
    except IOError as e:
        print(_('Errore durante il salvataggio del report storico {filename}: {e}').format(filename=report_filename_full_path, e=str(e)))
        return None
    except Exception as e:
        print(_("\n--- ERRORE DURANTE LA GENERAZIONE DEL REPORT ---"))
        print(_("Si è verificato un errore imprevisto. Dettagli:"))
        traceback.print_exc()
        print("-------------------------------------------------")
        return None
    try:
        base_report_filename, u1 = os.path.splitext(report_filename_base) # Usa il nome base
        graphic_report_filename_base = base_report_filename + '.svg'
        graphic_report_filename_full_path = os.path.join(USER_DATA_PATH, graphic_report_filename_base)
        crea_report_grafico(
            current_aggregates, 
            previous_aggregates, 
            g_value, 
            x_value, 
            num_sessions_in_current_report, 
            graphic_report_filename_full_path, 
            app_language
        )
        print(_('Report grafico salvato in: {filename}').format(filename=graphic_report_filename_full_path ))
    except Exception as e_graph:
        print(_('Errore durante la generazione del report grafico'))
    return current_aggregates

global MNMAIN, MNRX, MNRXKIND
app_data = load_settings()
app_data['app_info']['launch_count'] = app_data.get('app_info', {}).get('launch_count', 0) + 1
launch_count = app_data['app_info']['launch_count']
overall_settings = app_data['overall_settings']
MNMAIN = {'c': _('Risultati conteggio'), 'k': _('Tastiera ed impostazioni CW'), 'l': _('Ascolta gli appunti in CW'), 'm': _('Mostra Menu'), 'q': _('Per uscire da questa app'), 'r': _('Esercizio di ricezione'), 's': _("Statistiche sull'archivio  storico"), 't': _('Esercizio di trasmissione simulata'), 'w': _('Crea dizionario personalizzato')}
overall_speed = overall_settings.get('speed', 18)
overall_pitch = overall_settings.get('pitch', 550)
overall_dashes = overall_settings.get('dashes', 30)
overall_spaces = overall_settings.get('spaces', 50)
overall_dots = overall_settings.get('dots', 50)
overall_volume = overall_settings.get('volume', 0.5)
overall_ms = overall_settings.get('ms', 1)
overall_fs = overall_settings.get('fs_index', 5)
overall_wave = overall_settings.get('wave_index', 1)
session_speed = overall_speed
_clear_screen_ansi()
print(_("\nCWAPU - VERSIONE: {version} DI GABRY - IZ4APU.\n\t----UTILITÀ PER IL TUO CW----\n\t\tLancio app: {count}. Scrivi 'm' per il menu.").format(version=VERSION, count=launch_count))
print(_('\tWPM: {overall_speed}, Hz: {overall_pitch}, Volume: {}\n\tL/S/P: {overall_dashes}/{overall_spaces}/{overall_dots}, Wave: {}, MS:\t{overall_ms}, FS: {}.').format(int(overall_volume * 100), WAVE_TYPES[overall_wave - 1], SAMPLE_RATES[overall_fs], overall_speed=overall_speed, overall_pitch=overall_pitch, overall_dashes=overall_dashes, overall_spaces=overall_spaces, overall_dots=overall_dots, overall_ms=overall_ms))
while True:
    k = menu(d=MNMAIN, show=False, keyslist=True, ntf=_('Non è un comando!'))
    _clear_screen_ansi()
    if k == 'c':
        Count()
    elif k == 't':
        Txing()
    elif k == 'r':
        Rxing()
    elif k == 'k':
        KeyboardCW()
    elif k == 'l':
        ltc = pyperclip.paste()
        if ltc:
            ltc = StringCleaning(ltc)
            plo, rwpm = CWzator(msg=ltc, wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
        else:
            plo, rwpm = CWzator(msg=_('vuoti'), wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
    elif k == 'm':
        menu(d=MNMAIN, show_only=True)
    elif k == 'w':
        CreateDictionary()
    elif k == 's':
        _clear_screen_ansi()
        # Generazione dei report della timeline per ogni categoria
        category_mapping = {
            "words": _("parole"),
            "chars": _("caratteri/misto"),
            "qrz": "QRZ"
        }

        for category_key, category_name_translated in category_mapping.items():
            log_sessioni = app_data[f'historical_rx_data_{category_key}']['sessions_log']
            if log_sessioni: # Genera il report solo se ci sono sessioni
                print(_('\nGenerazione report timeline per gli esercizi di {category_name}...').format(category_name=category_name_translated))
                report_con_header = timeline.genera_report_temporale_completo(log_sessioni, _, app_language)
                
                timeline_filename = os.path.join(USER_DATA_PATH, f'CWapu_Historical_Statistics_Timeline_{category_key.capitalize()}.html')
                try:
                    with open(timeline_filename, 'w', encoding='utf-8') as f:
                        f.write(report_con_header)
                    print(_('Report timeline per {category_name} salvato su {filename}').format(category_name=category_name_translated, filename=timeline_filename))
                except IOError as e:
                    print(_('Errore durante il salvataggio del report timeline per {category_name}: {e}').format(category_name=category_name_translated, e=e))
            else:
                print(_('\nNessun dato di sessione per gli esercizi di {category_name}, salto la generazione del report timeline.').format(category_name=category_name_translated))
                continue
            riga_separatore = '-' * 75
            stringa_traducibile = _('--- Fine Report - Bye da CWAPU {version} ---')
            footer_formattato = stringa_traducibile.format(version=VERSION)
            footer = f"\n{riga_separatore}\n"
            footer += f"{footer_formattato.center(70)}\n"
            footer += f"{riga_separatore}\n"
            report_finale = report_con_header + footer
            print(report_finale)
            prompt_salvataggio = _('Vuoi salvare il report in un file di testo? (Invio per Sì / altro tasto per No): ')
            scelta = key(prompt=prompt_salvataggio).strip()
            if scelta == '':
                nome_file_report = "Cwapu_Historical_Statistics_Advanced_Report.txt"
                percorso_file_report = os.path.join(USER_DATA_PATH, nome_file_report)
                try:
                    with open(percorso_file_report, 'w', encoding='utf-8') as f:
                        f.write(report_finale)
                        print(_("\nReport salvato con successo in: {}").format(percorso_file_report))
                except IOError as e:
                    print(_("\nErrore durante il salvataggio del file: {}").format(e))
            else:
                print(_("\nSalvataggio annullato."))
            key(prompt=_("\nPremi un tasto per tornare al menu principale..."))
    elif k == 'q':
        break
app_data['overall_settings'].update({'speed': overall_speed, 'pitch': overall_pitch, 'dashes': overall_dashes, 'spaces': overall_spaces, 'dots': overall_dots, 'volume': overall_volume, 'ms': overall_ms, 'fs_index': overall_fs, 'wave_index': overall_wave})
save_settings(app_data)
print('hpe cuagn - 73 de I4APU - Gabe in Bologna, JN54pl.')
CWzator(msg='bk hpe cuagn - 73 de iz4apu tu e e', wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], sync=False, wv=overall_wave)
_clear_screen_ansi()
Donazione()
sys.exit()