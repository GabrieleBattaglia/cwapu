# CWAPU - Utility per il CW, di Gabry, IZ4APU
# Data concepimento 21/12/2022.
# GitHub publishing on july 2nd, 2024.

#QI
import sys, random, json, string, pyperclip, re, difflib, os
import datetime as dt
from GBUtils import key, dgt, menu, CWzator, Donazione
from time import localtime as lt
from translations import translations

def Trnsl(key, lang='en', **kwargs):
	value = translations.get(lang, {}).get(key, '')
	if isinstance(value, dict):
		return value
	return value.format(**kwargs)

#QConstants
VERSION="4.1.0, (2025-06-26)"
overall_settings_changed=False
SAMPLE_RATES = [8000, 11025, 16000, 22050, 32000, 44100, 48000, 88200, 96000, 176400, 192000, 384000]
WAVE_TYPES = ['sine', 'square', 'triangle', 'sawtooth']
SETTINGS_FILE = "cwapu_settings.json"
RX_SWITCHER_ITEMS = [
	{'id': '1', 'key_state': 'parole',  'label_key': 'menu_rx_switcher_parole', 'is_exclusive': False},
	{'id': '2', 'key_state': 'lettere', 'label_key': 'menu_rx_switcher_lettere', 'is_exclusive': False},
	{'id': '3', 'key_state': 'numeri',  'label_key': 'menu_rx_switcher_numeri', 'is_exclusive': False},
	{'id': '4', 'key_state': 'simboli', 'label_key': 'menu_rx_switcher_simboli', 'is_exclusive': False},
	{'id': '5', 'key_state': 'qrz',     'label_key': 'menu_rx_switcher_qrz', 'is_exclusive': False},
	{'id': '6', 'key_state': 'custom',  'label_key': 'menu_rx_switcher_custom', 'is_exclusive': True}]
HISTORICAL_RX_MAX_SESSIONS_DEFAULT = 100
HISTORICAL_RX_REPORT_INTERVAL = 2000
VALID_MORSE_CHARS_FOR_CUSTOM_SET = {k for k in CWzator(msg=-1) if k != " " and k.isprintable()}
LETTERE_MORSE_POOL = {k for k in VALID_MORSE_CHARS_FOR_CUSTOM_SET if k in set(string.ascii_lowercase)}
NUMERI_MORSE_POOL  = {k for k in VALID_MORSE_CHARS_FOR_CUSTOM_SET if k in set(string.digits)   }
SIMBOLI_MORSE_POOL = VALID_MORSE_CHARS_FOR_CUSTOM_SET - LETTERE_MORSE_POOL - NUMERI_MORSE_POOL
DEFAULT_DATA = {
    "app_info": {
        "launch_count": 0 
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
    "counting_stats": { # "counting_stats" termina qui
        "exercise_number": 1
    },
				"rx_menu_switcher_states": {
					"parole": True,
					"lettere": False,
					"numeri": False,
					"simboli": False,
					"qrz": False,
					"custom": False,
					"parole_filter_min": 1, 
					"parole_filter_max": 6,
					"custom_set_string": ""
				},
				"historical_rx_data": {
        "max_sessions_to_keep": HISTORICAL_RX_MAX_SESSIONS_DEFAULT,
        "report_interval": HISTORICAL_RX_REPORT_INTERVAL, 
        "chars_since_last_report": 0,
        "sessions_log": [] 
    }
} # Chiusura di DEFAULT_DATA
MNLANG={
	"en":"English",
	"it":"Italiano"}
MDL={'a0a':4,
					'a0aa':6,
					'a0aaa':15,
					'aa0a':6,
					'aa0aa':18,
					'aa0aaa':36,
					'0a0a':2,
					'0a0aa':2,
					'0a0aaa':2,
					'a00a':3,
					'a00aa':3,
					'a00aaa':4}
#QVariable
customized_set=''
words=[]
app_data = {}

#qf
def _clear_screen_ansi():
	"""Pulisce lo schermo usando ANSI e posiziona il cursore in alto a sinistra."""
	sys.stdout.write("\033[2J") # Comando ANSI per pulire l'intero schermo
	sys.stdout.write("\033[H")  # Comando ANSI per muovere il cursore a Home (riga 1, colonna 1)
	sys.stdout.flush()

def genera_singolo_item_esercizio_misto(active_switcher_states, group_length_for_generated, 
                                        custom_set_active_string, parole_filtrate_list):
	global overall_speed # Usato da GeneratingGroup
	# Le altre variabili globali come MDL, morse_map (per VALID_MORSE_CHARS_FOR_CUSTOM_SET), ecc.
	# sono usate dalle funzioni chiamate (Mkdqrz, GeneratingGroup)

	active_and_usable_kinds = []
	
	# Costruisci la lista dei tipi di item effettivamente utilizzabili
	if active_switcher_states.get('parole') and parole_filtrate_list: # Controlla anche che la lista non sia vuota
		active_and_usable_kinds.append('parole')
	if active_switcher_states.get('lettere'):
		active_and_usable_kinds.append('lettere')
	if active_switcher_states.get('numeri'):
		active_and_usable_kinds.append('numeri')
	if active_switcher_states.get('simboli'):
		# Per 'simboli', GeneratingGroup avrà bisogno di un pool di simboli.
		# Questo dipenderà da come definiamo SIMBOLI_MORSE_POOL.
		active_and_usable_kinds.append('simboli')
	if active_switcher_states.get('qrz'):
		active_and_usable_kinds.append('qrz')
	if active_switcher_states.get('custom') and custom_set_active_string and len(custom_set_active_string) >= 2:
		active_and_usable_kinds.append('custom')

	if not active_and_usable_kinds:
		return "ERROR_NO_VALID_TYPES" # Segnala che non ci sono tipi validi attivi

	chosen_kind = random.choice(active_and_usable_kinds)
	
	item_generato = ""
	if chosen_kind == 'parole':
		item_generato = random.choice(parole_filtrate_list)
	elif chosen_kind == 'qrz':
		# Logica per Mkdqrz come era in Rxing per call_or_groups == "1"
		# Mkdqrz si aspetta una lista con una singola chiave da MDL come argomento.
		random_mdl_key_list = random.choices(list(MDL.keys()), weights=list(MDL.values()), k=1)
		item_generato = Mkdqrz(random_mdl_key_list) 
	elif chosen_kind == 'custom':
		# NOTA: GeneratingGroup dovrà essere modificato per accettare 'customized_set_param'
		# e per usare 'group_length_for_generated' per il kind '4'.
		item_generato = GeneratingGroup(kind="4", length=group_length_for_generated, 
		                                wpm=overall_speed, customized_set_param=custom_set_active_string)
	elif chosen_kind == 'lettere':
		item_generato = GeneratingGroup(kind="1", length=group_length_for_generated, wpm=overall_speed)
	elif chosen_kind == 'numeri':
		item_generato = GeneratingGroup(kind="2", length=group_length_for_generated, wpm=overall_speed)
	elif chosen_kind == 'simboli':
		# NOTA: GeneratingGroup dovrà essere modificato per un nuovo 'kind' per i simboli,
		# ad esempio "S" o "7".
		item_generato = GeneratingGroup(kind="S", length=group_length_for_generated, wpm=overall_speed) 

	return item_generato.lower() # Restituisce sempre in minuscolo per coerenza

def seleziona_modalita_rx():
	global app_data, app_language, overall_settings_changed, words, overall_speed
	global overall_pitch, overall_dashes, overall_spaces, overall_dots, overall_volume, overall_ms, overall_fs, overall_wave 
	global SAMPLE_RATES, WAVE_TYPES 
	global HISTORICAL_RX_MAX_SESSIONS_DEFAULT, HISTORICAL_RX_REPORT_INTERVAL 
	global DEFAULT_DATA 
	global RX_SWITCHER_ITEMS # Assicurati sia globale
	global VALID_MORSE_CHARS_FOR_CUSTOM_SET # Assicurati sia globale

	switcher_settings_key = 'rx_menu_switcher_states'
	if switcher_settings_key not in app_data:
		app_data[switcher_settings_key] = DEFAULT_DATA[switcher_settings_key].copy()
	
	current_switcher_states = app_data[switcher_settings_key].copy()
	parole_filtrate_sessione = None
	custom_set_string_sessione = current_switcher_states.get('custom_set_string', "")

	if current_switcher_states.get('parole'):
		min_len = current_switcher_states.get('parole_filter_min', 0)
		max_len = current_switcher_states.get('parole_filter_max', 0)
		if min_len > 0 and max_len > 0 and min_len <= max_len:
			parole_filtrate_sessione = [w for w in words if len(w) >= min_len and len(w) <= max_len]
			if not parole_filtrate_sessione:
				current_switcher_states['parole'] = False 
		else:
			current_switcher_states['parole'] = False
	
	if current_switcher_states.get('custom') and not custom_set_string_sessione:
		current_switcher_states['custom'] = False

	MENU_BASE_ROW = 3 
	user_message_line_row = MENU_BASE_ROW + len(RX_SWITCHER_ITEMS) + 1 # Riga per messaggi utente
	prompt_actual_line_row = MENU_BASE_ROW + len(RX_SWITCHER_ITEMS) + 2 # Riga per il prompt effettivo <1>[2]...

	# Helper per singola riga switcher (invariato dalla tua ultima implementazione)
	def _display_single_switcher_line(index, is_on_state):
		item_config = RX_SWITCHER_ITEMS[index]
		riga_da_scrivere = MENU_BASE_ROW + index
		_move_cursor(riga_da_scrivere, 1)
		label_text_trans = Trnsl(item_config['label_key'], lang=app_language)
		status_marker = "<X>" if is_on_state else "< >"
		status_text_trans = Trnsl('switcher_status_on_label', lang=app_language) if is_on_state else Trnsl('switcher_status_off_label', lang=app_language)
		display_label_cased = label_text_trans.upper() if is_on_state else label_text_trans.lower()
		line_output = f"{item_config['id']}. {display_label_cased} {status_marker} {status_text_trans}"
		sys.stdout.write(line_output); _clear_line_from_cursor(); sys.stdout.flush()

	# Helper per disegnare l'interfaccia e restituire la stringa di prompt
	def _redraw_menu_interface_and_get_prompt_string(current_states_dict, message_for_user=""):
		_move_cursor(MENU_BASE_ROW - 1, 1) 
		sys.stdout.write(Trnsl('rx_switcher_menu_title', lang=app_language)); _clear_line_from_cursor(); print() # Titolo

		for idx_draw_menu, item_config_menu in enumerate(RX_SWITCHER_ITEMS):
			_display_single_switcher_line(idx_draw_menu, current_states_dict[item_config_menu['key_state']])

		# Riga per il messaggio utente (sopra il prompt degli switcher)
		_move_cursor(user_message_line_row, 1)
		if message_for_user:
			sys.stdout.write(message_for_user); _clear_line_from_cursor();
		else:
			_clear_line_from_cursor() # Pulisci se non ci sono messaggi

		# Costruisci la stringa di prompt con lo stato degli switcher
		_move_cursor(prompt_actual_line_row, 1) # Posiziona per dove key() stamperà il prompt
		status_display_parts = []
		for item_cfg_summary in RX_SWITCHER_ITEMS:
			is_on_summary = current_states_dict.get(item_cfg_summary['key_state'], False)
			status_display_parts.append(f"[{item_cfg_summary['id']}]" if is_on_summary else f"<{item_cfg_summary['id']}>")
		
		# La stringa di prompt che verrà passata a key()
		# key() stamperà questa stringa e poi attenderà l'input sulla stessa riga
		prompt_string_for_key_func = " ".join(status_display_parts) + ": " 
		sys.stdout.write(prompt_string_for_key_func) # Stampa il prompt
		_clear_line_from_cursor() # Pulisce il resto della riga
		sys.stdout.flush() # Assicura che sia visibile
		return prompt_string_for_key_func # Restituisci per key(), anche se già stampato.
                                          # O modifica key() per non stampare se prompt è None/vuoto
                                          # Oppure, se key() stampa sempre il suo prompt, questa funzione
                                          # non dovrebbe fare sys.stdout.write(prompt_string_for_key_func)
                                          # ma solo costruirla e restituirla.
                                          # Per ora, la stampo qui e la passo a key(),
                                          # sperando che key() non la ristampi o che la sovrascrittura sia ok.
                                          # L'IDEALE SAREBBE: key() prende il prompt e lo stampa.
                                          # Quindi questa funzione NON dovrebbe stampare l'ultima riga, ma solo restituirla.

	# Per un'esperienza utente migliore con key(), modifichiamo _redraw_menu_interface_and_get_prompt_string
	# per NON stampare l'ultima riga del prompt, ma solo costruirla e restituirla.
	# La funzione key() si occuperà di stamparla.

	def _redraw_menu_interface_for_key_prompt(current_states_dict, message_for_user=""):
		# Stampa titolo e righe switcher (come sopra)
		_move_cursor(MENU_BASE_ROW - 1, 1) 
		sys.stdout.write(Trnsl('rx_switcher_menu_title', lang=app_language)); _clear_line_from_cursor(); print()

		for idx_redraw, item_config_redraw in enumerate(RX_SWITCHER_ITEMS):
			_display_single_switcher_line(idx_redraw, current_states_dict[item_config_redraw['key_state']])

		# Riga per il messaggio utente
		_move_cursor(user_message_line_row, 1)
		if message_for_user:
			sys.stdout.write(message_for_user); _clear_line_from_cursor();
		else:
			_clear_line_from_cursor()
		
		# Costruisci la stringa prompt per key()
		status_display_parts = []
		for item_cfg_key_prompt in RX_SWITCHER_ITEMS:
			is_on_key_prompt = current_states_dict.get(item_cfg_key_prompt['key_state'], False)
			status_display_parts.append(f"[{item_cfg_key_prompt['id']}]" if is_on_key_prompt else f"<{item_cfg_key_prompt['id']}>")
		
		# La riga effettiva dove key() stamperà il suo prompt e attenderà input
		_move_cursor(prompt_actual_line_row, 1) 
		_clear_line_from_cursor() # Pulisci la riga del prompt prima che key() scriva
		sys.stdout.flush()
		return " ".join(status_display_parts) + ": " # Stringa da passare a key(prompt=...)
	user_message_content = "" 
	# Loop Principale del Menu
	while True:
		prompt_string = _redraw_menu_interface_for_key_prompt(current_switcher_states, user_message_content)
		user_message_content = "" # Resetta messaggio dopo averlo preparato per la visualizzazione
		scelta = key(prompt=prompt_string) 
		if not scelta or scelta == "\r": # INVIO (key() potrebbe restituire "" o "\r" per Invio)
			active_switches_final = [item['key_state'] for item in RX_SWITCHER_ITEMS if current_switcher_states.get(item['key_state'])]
			if not active_switches_final:
				user_message_content = Trnsl('rx_switcher_no_selection_error', lang=app_language)
				CWzator(msg="?", wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
				continue
			if current_switcher_states.get('parole') and not parole_filtrate_sessione:
				user_message_content = Trnsl('parole_filter_not_set_error', lang=app_language)
				CWzator(msg="?", wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
				continue
			if current_switcher_states.get('custom') and (not custom_set_string_sessione or len(custom_set_string_sessione) < 2):
				user_message_content = Trnsl('custom_set_invalid_or_empty_error', lang=app_language)
				CWzator(msg="?", wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
				continue
			group_len_val_final = 0
			# Determina se chiedere la lunghezza del gruppo
			ask_for_length = False
			if current_switcher_states.get('lettere') or \
			   current_switcher_states.get('numeri') or \
			   current_switcher_states.get('custom') or \
			   current_switcher_states.get('simboli'):
				ask_for_length = True
			if ask_for_length:
				_move_cursor(prompt_actual_line_row + 1, 1) 
				prompt_len_text_final = Trnsl('rx_switcher_group_length_prompt', lang=app_language)
				# Dobbiamo passare il prompt a key() o usare input() per la lunghezza
				# Usiamo input() per la lunghezza per semplicità, dato che key() è per singolo carattere
				sys.stdout.write(prompt_len_text_final); _clear_line_from_cursor(); sys.stdout.flush()
				_move_cursor(prompt_actual_line_row + 1, len(prompt_len_text_final) + 1)
				len_str_final = input()
				if len_str_final.isdigit() and 1 <= int(len_str_final) <= 7:
					group_len_val_final = int(len_str_final)
				else:
					user_message_content = Trnsl('rx_switcher_invalid_length_error', lang=app_language)
					CWzator(msg="?", wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
					continue
			app_data[switcher_settings_key].update(current_switcher_states) 
			overall_settings_changed = True
			for i_clean_final in range(len(RX_SWITCHER_ITEMS) + 4): 
				_move_cursor(MENU_BASE_ROW - 1 + i_clean_final, 1)
				_clear_line_from_cursor()
			_move_cursor(MENU_BASE_ROW, 1)
			return {
				"active_switcher_states": current_switcher_states,
				"parole_filtrate_list": parole_filtrate_sessione if current_switcher_states.get('parole') else None,
				"custom_set_string_active": custom_set_string_sessione if current_switcher_states.get('custom') else None,
				"group_length_for_generated": group_len_val_final 
			}

		elif scelta.isdigit() and '1' <= scelta <= str(len(RX_SWITCHER_ITEMS)):
			chosen_idx = int(scelta) - 1
			item_key_toggle_loop = RX_SWITCHER_ITEMS[chosen_idx]['key_state']
			
			current_switcher_states[item_key_toggle_loop] = not current_switcher_states[item_key_toggle_loop]
			# Non impostare overall_settings_changed qui, ma solo all'uscita con Invio
			
			if current_switcher_states[item_key_toggle_loop]: # Se è stato appena ATTIVATO
				if item_key_toggle_loop == 'parole':
					min_len_saved_loop = current_switcher_states.get('parole_filter_min', 0)
					max_len_saved_loop = current_switcher_states.get('parole_filter_max', 0)
					if not (min_len_saved_loop > 0 and max_len_saved_loop > 0 and min_len_saved_loop <= max_len_saved_loop):
						user_message_content = Trnsl('parole_filter_use_dot_command', lang=app_language)
						current_switcher_states['parole'] = False 
						parole_filtrate_sessione = None
					else:
						parole_filtrate_sessione = [w for w in words if len(w) >= min_len_saved_loop and len(w) <= max_len_saved_loop]
						if not parole_filtrate_sessione:
							user_message_content = Trnsl('parole_filter_no_results_with_saved', lang=app_language)
							current_switcher_states['parole'] = False
						else:
							user_message_content = Trnsl('parole_filter_applied_from_settings', lang=app_language, count=len(parole_filtrate_sessione))
				
				elif item_key_toggle_loop == 'custom':
					if not custom_set_string_sessione or len(custom_set_string_sessione) < 2:
						# Pulisci l'area del menu prima di chiamare CustomSet
						for i_clean_cs in range(len(RX_SWITCHER_ITEMS) + 4): _move_cursor(MENU_BASE_ROW -1 + i_clean_cs, 1); _clear_line_from_cursor()
						_move_cursor(1,1); sys.stdout.write(Trnsl('custom_set_invoking', lang=app_language) + "\n\n"); sys.stdout.flush()
						
						custom_set_string_nuovo = CustomSet(overall_speed) # CustomSet ora usa \n nel suo prompt
						
						# Dopo CustomSet, è necessario ridisegnare il menu switcher,
						# quindi non stampiamo messaggi qui che verrebbero sovrascritti.
						# Il loop principale ridisegnerà tutto.
						if len(custom_set_string_nuovo) >= 2:
							custom_set_string_sessione = custom_set_string_nuovo
							current_switcher_states['custom_set_string'] = custom_set_string_nuovo 
						else:
							user_message_content = Trnsl('custom_set_not_created_deactivating', lang=app_language)
							current_switcher_states['custom'] = False
							custom_set_string_sessione = ""
							current_switcher_states['custom_set_string'] = ""
					else: 
						user_message_content = Trnsl('custom_set_loaded_from_settings', lang=app_language, set_string=custom_set_string_sessione) 
			
			# Aggiornamento visivo immediato solo per la riga dello switcher toccato
			# (il summary e il prompt verranno ridisegnati dal ciclo principale)
			# Questo non è necessario se _redraw_menu_interface_for_key_prompt ridisegna tutto ogni volta.
			# _display_single_switcher_line(chosen_idx, current_switcher_states[item_key_toggle_loop])
			# E la riga summary andrebbe aggiornata.
			# Per semplicità, il loop principale che chiama _redraw_menu_interface_for_key_prompt gestirà il ridisegno completo.
			pass # L'intero menu verrà ridisegnato all'inizio del prossimo ciclo.

		else: # Input non valido (non Invio, non 1-6)
			user_message_content = Trnsl('invalid_menu_choice', lang=app_language)
			CWzator(msg="?", wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
			# Non c'è bisogno di time.sleep(0.5) qui perché il loop ridisegnerà il menu
			# e il messaggio, e attenderà il prossimo input.

	return None # Non dovrebbe essere raggiunto

def _move_cursor(riga, colonna):
	"""Muove il cursore alla riga e colonna specificata (1-based)."""
	sys.stdout.write(f"\033[{riga};{colonna}H")

def _clear_line_from_cursor():
	"""Pulisce la linea dalla posizione attuale del cursore fino alla fine."""
	sys.stdout.write("\033[K")

def crea_report_grafico(current_aggregates, previous_aggregates, 
                        g_val, x_val, num_sessions_in_report, 
                        output_filename, lang='en'):
	"""
	Crea un report grafico delle statistiche storiche e lo salva come immagine.
	"""
	try:
		import matplotlib
		matplotlib.use('Agg') # Imposta il backend non interattivo PRIMA di importare pyplot
		import matplotlib.pyplot as plt
		import numpy as np
	except ImportError:
		print(Trnsl('matplotlib_not_found_error', lang=lang))
		return
	except Exception as e_import:
		print(Trnsl('error_importing_matplotlib', lang=lang, error=str(e_import)))
		return

	# Impostazioni preliminari
	plt.style.use('dark_background')
	fig_width_inches = 10 
	fig_height_inches = 16 # Altezza generosa per contenuti futuri e scorrimento

	text_color = 'white'
	color_error_very_high = '#B22222' # Firebrick, un rosso cupo
	color_error_high = '#FF4136' # Rosso
	color_warning = '#FF851B'
	color_neutral = '#FFDC00'    # Giallo
	color_good = '#2ECC40'       # Verde
	color_excellent = '#7FDBFF'  # Azzurro Chiaro
	fig = plt.figure(figsize=(fig_width_inches, fig_height_inches))
	fig.patch.set_facecolor('#222222')

	# --- COORDINATE E LAYOUT ---
	# Useremo coordinate relative alla figura per posizionare testo e assi
	# (0,0) è in basso a sinistra, (1,1) in alto a destra della figura.
	
	y_cursor = 0.98    # Cursore Y corrente, parte dall'alto
	line_height_fig = 0.030 # Altezza di una riga di testo in coordinate della figura
	section_spacing_fig = 0.04 # Spazio tra sezioni in coordinate della figura

	# --- INTESTAZIONE DEL REPORT (Testo) ---
	title_text = f"{Trnsl('report_header_appname', lang=lang)} - {Trnsl('historical_stats_report_title', lang=lang)}"
	fig.text(0.5, y_cursor, title_text, color=text_color, ha='center', va='top', fontsize=16, weight='bold')
	y_cursor -= line_height_fig * 1.5

	subtitle_text = Trnsl('stats_based_on_exercises', lang=lang, count=num_sessions_in_report) + \
	                f" (G={g_val}, X={x_val})"
	fig.text(0.5, y_cursor, subtitle_text, color=text_color, ha='center', va='top', fontsize=12)
	y_cursor -= line_height_fig

	generation_time_text = f"{Trnsl('report_generated_on', lang=lang)}: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
	fig.text(0.5, y_cursor, generation_time_text, color=text_color, ha='center', va='top', fontsize=10, style='italic')
	y_cursor -= section_spacing_fig * 1.5 # Più spazio prima del primo pannello grafico

	# Funzione helper per i colori delle variazioni
	def get_delta_color_and_symbol(delta_value, higher_is_better=True, tolerance=0.01):
		symbol = ""
		color_to_use = color_neutral # Default a neutral
		if higher_is_better:
			if delta_value > tolerance: color_to_use = color_good; symbol = "▲"
			elif delta_value < -tolerance: color_to_use = color_error_high; symbol = "▼"
			else: symbol = "~" # neutro
		else: # Lower is better
			if delta_value < -tolerance: color_to_use = color_good; symbol = "▼"
			elif delta_value > tolerance: color_to_use = color_error_high; symbol = "▲"
			else: symbol = "~" # neutro
		return color_to_use, symbol
	# --- PANNELLO STATISTICHE WPM (Grafico a Barre Orizzontali) ---
	fig.text(0.5, y_cursor, Trnsl('overall_speed_stats', lang=lang), color=color_excellent, ha='center', va='top', fontsize=14, weight='bold')
	y_cursor -= line_height_fig * 2.0 # Spazio doppio dopo il titolo della sezione
	wpm_metrics_data = [ # Rinomino per chiarezza, contiene i dati
		{'label_key': 'min_wpm', 'curr': current_aggregates['wpm_min_overall'], 
		 'prev': previous_aggregates['wpm_min_overall'] if previous_aggregates else None, 'higher_better': True},
		{'label_key': 'avg_wpm_of_session_avgs_label', 'curr': current_aggregates['wpm_avg_of_session_avgs'], 
		 'prev': previous_aggregates['wpm_avg_of_session_avgs'] if previous_aggregates else None, 'higher_better': True},
		{'label_key': 'max_wpm', 'curr': current_aggregates['wpm_max_overall'], 
		 'prev': previous_aggregates['wpm_max_overall'] if previous_aggregates else None, 'higher_better': True}
	]
	
	num_wpm_metrics = len(wpm_metrics_data)

	# Altezza per ogni gruppo di metriche WPM (Min, Avg, Max) in coordinate della figura.
	# Ogni gruppo conterrà una barra per il corrente, una per il precedente (se esiste), e testo.
	# AUMENTIAMO SIGNIFICATIVAMENTE QUESTI VALORI per dare più spazio
	height_per_wpm_metric_group_fig = 0.07  # Es. 7% dell'altezza della figura per ogni metrica (Min, Avg, Max)
	ax_wpm_needed_height_fig = height_per_wpm_metric_group_fig * num_wpm_metrics
	
	# Posizionamento dell'area grafici WPM
	ax_wpm_left = 0.20  # Spostato a destra per fare spazio alle etichette Y
	ax_wpm_width = 0.55 # Larghezza dell'area delle barre
	ax_wpm_bottom = y_cursor - ax_wpm_needed_height_fig 
	ax_variation_text_left = ax_wpm_left + ax_wpm_width + 0.03 # Dove inizia il testo delle variazioni

	ax_wpm = fig.add_axes([ax_wpm_left, ax_wpm_bottom, ax_wpm_width, ax_wpm_needed_height_fig])
	ax_wpm.set_facecolor('#383c44') # Sfondo per questa specifica area
	wpm_scale_min = 0
	wpm_scale_max = 100
	ax_wpm.set_xlim(wpm_scale_min, wpm_scale_max)
	ax_wpm.set_xlabel("WPM", color=text_color, fontsize=10)
	ax_wpm.tick_params(axis='x', colors=text_color, labelsize=9)
	ax_wpm.spines['bottom'].set_color(text_color)
	ax_wpm.spines['top'].set_visible(False)
	ax_wpm.spines['right'].set_visible(False)
	ax_wpm.spines['left'].set_visible(False) # Nascondiamo la spina sinistra perché le etichette y fungeranno da guida

	# Impostazione delle etichette Y per le metriche WPM
	# Le posizioni y per le etichette (e i centri dei gruppi di barre) saranno 0, 1, 2... N-1
	# Matplotlib le piazzerà uniformemente. Le disegneremo dall'alto verso il basso.
	y_tick_positions = np.arange(num_wpm_metrics) 
	metric_labels = [Trnsl(m['label_key'], lang=lang) for m in wpm_metrics_data]
	
	ax_wpm.set_yticks(y_tick_positions)
	ax_wpm.set_yticklabels(metric_labels[::-1]) # Inverti le etichette per l'ordine dall'alto verso il basso
	ax_wpm.tick_params(axis='y', colors=text_color, labelsize=10, length=0) # length=0 per nascondere i trattini
	ax_wpm.invert_yaxis() # L'etichetta superiore (Min WPM) sarà in alto

	bar_draw_height = 0.35 # Altezza di una singola barra (es. corrente o precedente) in coordinate dati dell'asse Y di ax_wpm
	                       # (0.35 significa che ogni barra occupa il 35% dello spazio verticale allocato alla sua metrica)
	for i, metric in enumerate(wpm_metrics_data):
		y_group_center = y_tick_positions[i] # Il centro del gruppo di barre per questa metrica (0, 1, 2)
		ax_wpm.barh(y_group_center, wpm_scale_max - wpm_scale_min, height=bar_draw_height * 2.2, left=wpm_scale_min, 
					color='#555555', edgecolor=text_color, linewidth=0.5, zorder=1, alpha=0.5)
		y_curr_bar_pos = y_group_center - bar_draw_height / 2.1 # MODIFICATO: ora ha il '-' per andare più in alto
		ax_wpm.barh(y_curr_bar_pos, metric['curr'] - wpm_scale_min, height=bar_draw_height, left=wpm_scale_min, 
					color=color_good, zorder=3, edgecolor=text_color, linewidth=0.5)
		ax_wpm.text(metric['curr'] + 0.015 * wpm_scale_max, y_curr_bar_pos, f"{metric['curr']:.2f}", 
					color=text_color, ha='left', va='center', fontsize=9, weight='bold')
		y_prev_bar_pos = y_group_center + bar_draw_height / 2.1 # MODIFICATO: ora ha il '+' per andare più in basso
		if metric['prev'] is not None:
			ax_wpm.barh(y_prev_bar_pos, metric['prev'] - wpm_scale_min, height=bar_draw_height, left=wpm_scale_min, 
						color=color_neutral, zorder=2, alpha=0.8, edgecolor=text_color, linewidth=0.5)
			ax_wpm.text(metric['prev'] + 0.015 * wpm_scale_max, y_prev_bar_pos, f"{metric['prev']:.2f}", 
						color=text_color, ha='left', va='center', fontsize=9)
		if metric['prev'] is not None:
			delta = metric['curr'] - metric['prev']
			color_txt, symbol = get_delta_color_and_symbol(delta, higher_is_better=metric['higher_better'], tolerance=0.05)
			perc_delta_str = f" ({(delta / metric['prev'] * 100):+.2f}%)" if metric['prev'] != 0 else ""
			norm_y_in_ax = (y_group_center + 0.5) / num_wpm_metrics 
			y_fig_coord_for_text = ax_wpm_bottom + (1 - norm_y_in_ax) * ax_wpm_needed_height_fig 
			fig.text(ax_variation_text_left, y_fig_coord_for_text, 
					 f"{symbol} {delta:+.2f}{perc_delta_str}", color=color_txt, 
					 ha='left', va='center', fontsize=10)
	# Aggiungi una legenda solo se ci sono dati precedenti da mostrare
	if any(metric['prev'] is not None for metric in wpm_metrics_data):
		legend_elements = [
			plt.Rectangle((0, 0), 1, 1, color=color_good, label=Trnsl('current_value', lang=lang)),
			plt.Rectangle((0, 0), 1, 1, color=color_neutral, alpha=0.8, label=Trnsl('previous_value', lang=lang))
		]
		# Posiziona la legenda sopra e a destra dell'area dei grafici WPM
		fig.legend(handles=legend_elements, 
		           loc='upper left', # Posizionamento relativo a bbox_to_anchor
		           bbox_to_anchor=(ax_wpm_left + ax_wpm_width + 0.01, ax_wpm_bottom + ax_wpm_needed_height_fig + 0.03), # A destra e leggermente sopra ax_wpm
		           fontsize=8, 
		           ncol=1, # Una colonna per la legenda
		           facecolor='#444444', 
		           edgecolor=text_color,
		           labelcolor=text_color) # Colore del testo della legenda
	
	y_cursor = ax_wpm_bottom - section_spacing_fig # Aggiorna y_cursor globale per il pannello successivo
	fig.text(0.5, y_cursor, Trnsl('overall_error_stats', lang=lang), color=color_excellent, ha='center', va='top', fontsize=14, weight='bold')
	y_cursor -= line_height_fig * 1.2
	# ... (Logica per stampare testualmente Total Chars Sent e Overall Error Rate come fatto prima, usando fig.text e y_cursor)
	x_text_start = 0.1
	label_overall_err = Trnsl('total_chars_sent_in_block', lang=lang)
	value_overall_err_str = f"{current_aggregates['total_chars_sent_overall']}"
	fig.text(x_text_start, y_cursor, f"{label_overall_err}: {value_overall_err_str}", color=text_color, ha='left', va='top', fontsize=11)
	if previous_aggregates:
		prev_val = previous_aggregates['total_chars_sent_overall']
		delta = current_aggregates['total_chars_sent_overall'] - prev_val
		perc_delta_str = f" ({(delta / prev_val * 100):+.2f}%)" if prev_val != 0 else ""
		fig.text(x_text_start + 0.4, y_cursor, f"{Trnsl('vs', lang=lang)} {prev_val} ({delta:+}{perc_delta_str})", color=color_neutral, ha='left', va='top', fontsize=10, style='italic')
	y_cursor -= line_height_fig

	total_chars_curr = current_aggregates['total_chars_sent_overall']
	total_errs_curr = current_aggregates['total_errors_chars_overall']
	overall_error_rate_curr = (total_errs_curr / total_chars_curr * 100) if total_chars_curr > 0 else 0.0
	label_overall_err = Trnsl('overall_error_rate', lang=lang)
	value_overall_err_str = f"{overall_error_rate_curr:.2f}% ({total_errs_curr}/{total_chars_curr})"
	fig.text(x_text_start, y_cursor, f"{label_overall_err}: {value_overall_err_str}", color=text_color, ha='left', va='top', fontsize=11)
	if previous_aggregates:
		total_chars_prev = previous_aggregates['total_chars_sent_overall']
		total_errs_prev = previous_aggregates['total_errors_chars_overall']
		overall_error_rate_prev = (total_errs_prev / total_chars_prev * 100) if total_chars_prev > 0 else 0.0
		delta_rate = overall_error_rate_curr - overall_error_rate_prev
		color, symbol = get_delta_color_and_symbol(delta_rate, higher_is_better=False)
		fig.text(x_text_start + 0.4, y_cursor, f"{Trnsl('vs', lang=lang)} {overall_error_rate_prev:.2f}% ({symbol} {delta_rate:+.2f} punti %)", color=color, ha='left', va='top', fontsize=10, style='italic')
	y_cursor -= section_spacing_fig
	# --- SEZIONE DETTAGLIO ERRORI PER CARATTERE (BLOCCO CORRENTE) ---
	fig.text(0.5, y_cursor, Trnsl('error_details_by_char', lang=lang), color=color_excellent, ha='center', va='top', fontsize=14, weight='bold')
	y_cursor -= line_height_fig * 0.06
	top_n_errors_to_display = 10 

	if current_aggregates['aggregated_errors_detail']:
		sorted_char_errors = sorted(
			current_aggregates['aggregated_errors_detail'].items(), 
			key=lambda item: (-item[1], item[0])
		)[:top_n_errors_to_display]

		error_chars = [item[0].upper() for item in sorted_char_errors]
		error_counts = [item[1] for item in sorted_char_errors]
		
		if error_counts:
			height_per_error_bar_fig = 0.035 # Aumentata leggermente per più spazio
			ax_err_needed_height_fig = height_per_error_bar_fig * len(error_chars) + 0.03
			
			ax_err_left = 0.10 # Lasciamo spazio a sinistra
			ax_err_width = 0.80 # Più largo per accomodare barre e testo
			ax_err_bottom = y_cursor - ax_err_needed_height_fig
			
			ax_char_err = fig.add_axes([ax_err_left, ax_err_bottom, ax_err_width, ax_err_needed_height_fig])
			ax_char_err.set_facecolor('#383c44')

			y_positions = np.arange(len(error_chars))
			bar_draw_visual_height = 0.6 # Altezza visiva della barra nelle coordinate y_positions

			# Scala X: da 0 al massimo errore + buffer
			max_error_val = max(error_counts) if error_counts else 1
			# Larghezza effettiva dell'asse X per il plottaggio. Le barre saranno centrate in questo spazio.
			# Questo determina anche la posizione delle linee verticali di riferimento.
			plot_area_width = max_error_val * 1.1 
			ax_char_err.set_xlim(0, plot_area_width) 

			# Calcola i left offset per centrare ogni barra
			left_offsets = [(plot_area_width - count) / 2 for count in error_counts]

			# Colori per le barre (logica già implementata)
			bar_colors_list = []
			for i in range(len(sorted_char_errors)):
				if i < 3: bar_colors_list.append(color_error_high)
				elif i < 7: bar_colors_list.append(color_neutral)
				else: bar_colors_list.append(color_good)
			
			bars = ax_char_err.barh(y_positions, error_counts, height=bar_draw_visual_height, 
			                        left=left_offsets, # Applica i left offset per centrare
			                        color=bar_colors_list,
			                        edgecolor=text_color, linewidth=0.5, zorder=2)
			
			ax_char_err.set_yticks(y_positions)
			ax_char_err.set_yticklabels(error_chars, color=text_color, fontsize=9, weight='bold')
			ax_char_err.invert_yaxis() 
			ax_char_err.tick_params(axis='y', length=0) # Nasconde i trattini delle y-ticks

			# Rimuovi etichette e linea dell'asse X dato che le barre sono centrate
			ax_char_err.set_xticks([]) # Nasconde i numeri sull'asse X
			ax_char_err.set_xlabel("") # Rimuove l'etichetta "Numero Errori"
			ax_char_err.spines['bottom'].set_visible(False) # Nasconde la linea dell'asse X
			ax_char_err.spines['top'].set_visible(False)
			ax_char_err.spines['right'].set_visible(False)
			ax_char_err.spines['left'].set_visible(False)

			# Linee di riferimento verticali basate sulla barra più lunga (la prima)
			if error_counts:
				longest_bar_width = error_counts[0]
				left_longest_bar = left_offsets[0]
				right_longest_bar = left_offsets[0] + longest_bar_width
				
				# Estensione verticale delle linee: dal bordo superiore della prima barra (in alto)
				# al bordo inferiore dell'ultima barra (in basso)
				y_top_line = y_positions[0] + bar_draw_visual_height / 2
				y_bottom_line = y_positions[-1] - bar_draw_visual_height / 2

				ax_char_err.vlines(x=left_longest_bar, ymin=y_bottom_line, ymax=y_top_line,
				                   color='white', linestyle='--', linewidth=0.75, alpha=0.7, zorder=1)
				ax_char_err.vlines(x=right_longest_bar, ymin=y_bottom_line, ymax=y_top_line,
				                   color='white', linestyle='--', linewidth=0.75, alpha=0.7, zorder=1)

			# Aggiungi annotazioni testuali (conteggio e percentuali)
			total_chars_in_block_for_perc = current_aggregates['total_chars_sent_overall']
			aggregated_sent_chars_for_perc = current_aggregates.get('aggregated_sent_chars_detail', {})

			for i, bar_patch in enumerate(bars): # bar_patch è l'oggetto Rectangle della barra
				char_l = error_chars[i].lower() # Carattere per lookup
				count = error_counts[i]
				
				perc_vs_total = (count / total_chars_in_block_for_perc * 100) if total_chars_in_block_for_perc > 0 else 0.0
				sent_of_this_char = aggregated_sent_chars_for_perc.get(char_l, 0)
				perc_vs_specific = (count / sent_of_this_char * 100) if sent_of_this_char > 0 else 0.0
				
				annotation_text = f" {count} " \
				                  f"({perc_vs_total:.1f}% {Trnsl('of_total_chars', lang=lang)}, " \
				                  f"{perc_vs_specific:.1f}% {Trnsl('of_specific_char_sent', lang=lang, char_upper=error_chars[i])})"
				
				# Posiziona il testo a destra della barra
				text_x_pos = bar_patch.get_x() + bar_patch.get_width() + plot_area_width * 0.01
				ax_char_err.text(text_x_pos, bar_patch.get_y() + bar_patch.get_height() / 2,
				                 annotation_text, va='center', ha='left', color=text_color, fontsize=8)
			y_cursor = ax_err_bottom - section_spacing_fig
		else: # Non ci sono errori di dettaglio da plottare
			no_detail_errors_text = Trnsl('no_detailed_errors_to_display', lang=lang)
			fig.text(0.5, y_cursor - line_height_fig, no_detail_errors_text, color=text_color, 
			         ha='center', va='top', fontsize=10, style='italic')
			y_cursor -= (line_height_fig * 2 + section_spacing_fig) # Spazio per il messaggio
	else: # current_aggregates['aggregated_errors_detail'] è vuoto o non esiste
		no_errors_text = Trnsl('no_errors_recorded_for_block', lang=lang) # Crea traduzione
		fig.text(0.5, y_cursor - line_height_fig, no_errors_text, color=text_color, 
		         ha='center', va='top', fontsize=10, style='italic')
		y_cursor -= (line_height_fig * 2 + section_spacing_fig)

	# --- SEZIONE VARIAZIONI ERRORI PER CARATTERE ---
	if previous_aggregates and previous_aggregates["num_sessions_in_block"] > 0:
		fig.text(0.5, y_cursor, Trnsl('error_details_variations', lang=lang), color=color_excellent, ha='center', va='top', fontsize=14, weight='bold')
		y_cursor -= line_height_fig * 0.06 # Spazio dopo il titolo

		# Prepara i dati: caratteri con errori attuali (fino a top_n) per cui esiste un delta
		# La lista 'sorted_char_errors' (caratteri ordinati per errore attuale) è definita nel pannello precedente.
		# Se non lo è, o se vuoi un ordinamento diverso per questo grafico (es. per magnitudine del delta),
		# dovresti ricalcolare la lista di caratteri qui.
		# Per coerenza, usiamo i caratteri dal grafico precedente (top N errori attuali)
		# e filtriamo quelli per cui si può calcolare una variazione.
		
		# Se sorted_char_errors non è definito in questo scope, prendilo da current_aggregates:
		# (Assumendo che top_n_errors_to_display sia definito globalmente nella funzione)
		if 'sorted_char_errors' not in locals() and 'error_chars' not in locals(): # Se il grafico precedente non è stato disegnato
			 # Fallback: prendi tutti i caratteri con errori attuali o precedenti
			_potential_chars = list(set(current_aggregates['aggregated_errors_detail'].keys()) | set(previous_aggregates['aggregated_errors_detail'].keys()))
			_sorted_potential_chars = sorted(
			    _potential_chars,
			    key=lambda char_key: (-current_aggregates['aggregated_errors_detail'].get(char_key, 0), char_key)
			)
			chars_for_variation_plot = [item.lower() for item in _sorted_potential_chars][:top_n_errors_to_display]
		elif 'error_chars' in locals():
			chars_for_variation_plot = [char.lower() for char in error_chars] # Usa gli stessi caratteri, in minuscolo per lookup
		else:
			chars_for_variation_plot = []
		variation_data_list = []
		for char_lcase in chars_for_variation_plot:
			curr_count = current_aggregates['aggregated_errors_detail'].get(char_lcase, 0)
			prev_count = previous_aggregates['aggregated_errors_detail'].get(char_lcase, 0)

			curr_total_sent = current_aggregates.get('aggregated_sent_chars_detail', {}).get(char_lcase, 0)
			prev_total_sent = previous_aggregates.get('aggregated_sent_chars_detail', {}).get(char_lcase, 0)

			# Calcola delta solo se il carattere era presente in modo significativo per il calcolo del tasso
			if curr_total_sent > 0 or prev_total_sent > 0: # Deve essere stato inviato almeno una volta
				curr_rate_spec = (curr_count / curr_total_sent * 100) if curr_total_sent > 0 else 0.0
				prev_rate_spec = (prev_count / prev_total_sent * 100) if prev_total_sent > 0 else 0.0
				# Se un carattere non è stato inviato nel periodo precedente, ma ora sì con errori,
				# il suo prev_rate_spec è 0, quindi il delta sarà curr_rate_spec.
				# Se è stato inviato prima ma ora non più, curr_rate_spec è 0, delta è -prev_rate_spec.
				delta = curr_rate_spec - prev_rate_spec
				variation_data_list.append({'char': char_lcase.upper(), 'delta': delta})
		
		if variation_data_list:
			# Ordina per magnitudine del delta (decrescente) se vuoi evidenziare i maggiori cambiamenti
			# Oppure mantieni l'ordine per errore corrente per coerenza con il grafico sopra.
			# Per ora, manteniamo l'ordine dato da chars_for_variation_plot.

			deltas_values = [item['delta'] for item in variation_data_list]
			
			# Scala colori dinamica a 5 livelli
			bar_colors_variation = []
			# Soglie per Giallo (stabilità/minimo cambiamento)
			stable_threshold_abs = 1.0 # Es. +/- 1.0 punto percentuale è considerato "stabile" (Giallo)

			# Filtra i delta significativi per definire le altre categorie
			significant_improvements = sorted([d for d in deltas_values if d < -stable_threshold_abs]) # Es. [-10, -5, -2]
			significant_worsenings = sorted([d for d in deltas_values if d > stable_threshold_abs])  # Es. [2, 5, 10]

			# Soglie per Verde/Azzurro (miglioramenti)
			split_azzurro_verde = np.median(significant_improvements) if significant_improvements else -stable_threshold_abs
			
			# Soglie per Arancione/RossoCupo (peggioramenti)
			split_arancione_rossocupo = np.median(significant_worsenings) if significant_worsenings else stable_threshold_abs

			for d_val in deltas_values:
				if d_val < -stable_threshold_abs: # Miglioramento significativo
					if d_val <= split_azzurro_verde and significant_improvements: bar_colors_variation.append(color_excellent) # Azzurro
					else: bar_colors_variation.append(color_good) # Verde
				elif d_val > stable_threshold_abs: # Peggioramento significativo
					if d_val >= split_arancione_rossocupo and significant_worsenings: bar_colors_variation.append(color_error_very_high) # Rosso Cupo
					else: bar_colors_variation.append(color_warning) # Arancione
				else: # Stabile/Minimo cambiamento
					bar_colors_variation.append(color_neutral) # Giallo
			
			# Creazione Assi per questo grafico
			height_per_var_bar_fig = 0.035 
			ax_var_needed_height_fig = height_per_var_bar_fig * len(variation_data_list) + 0.05 # Un po' di padding
			
			ax_var_left = 0.15
			ax_var_width = 0.70 
			ax_var_bottom = y_cursor - ax_var_needed_height_fig

			ax_err_var = fig.add_axes([ax_var_left, ax_var_bottom, ax_var_width, ax_var_needed_height_fig])
			ax_err_var.set_facecolor('#383c44')

			plot_chars = [item['char'] for item in variation_data_list]
			plot_deltas = [item['delta'] for item in variation_data_list]
			
			y_var_positions = np.arange(len(plot_chars))
			
			max_abs_delta_val = max(abs(d) for d in plot_deltas) if plot_deltas else 1.0
			axis_plot_limit = max_abs_delta_val * 1.15 
			ax_err_var.set_xlim(-axis_plot_limit, axis_plot_limit)
			
			ax_err_var.axvline(0, color='white', linestyle=':', linewidth=0.7, alpha=0.7, zorder=1)
			ax_err_var.axvline(-max_abs_delta_val, color='white', linestyle='--', linewidth=0.75, alpha=0.5, zorder=1)
			ax_err_var.axvline(max_abs_delta_val, color='white', linestyle='--', linewidth=0.75, alpha=0.5, zorder=1)

			for i in range(len(plot_chars)):
				delta_val = plot_deltas[i]
				bar_w = abs(delta_val)
				bar_l = delta_val if delta_val < 0 else 0
				ax_err_var.barh(y_var_positions[i], bar_w, left=bar_l, 
				                color=bar_colors_variation[i], height=0.5, 
				                edgecolor=text_color, linewidth=0.5, zorder=2)
				
				text_x_offset = axis_plot_limit * 0.02 # Piccolo offset dal bordo della barra
				ha_val = 'right' if delta_val < 0 else 'left'
				text_x = delta_val - text_x_offset if delta_val < 0 else delta_val + text_x_offset
				ax_err_var.text(text_x, y_var_positions[i], f"{delta_val:+.1f}%", 
				                va='center', ha=ha_val, color=text_color, fontsize=8)

			ax_err_var.set_yticks(y_var_positions)
			ax_err_var.set_yticklabels(plot_chars, color=text_color, fontsize=9)
			ax_err_var.invert_yaxis()
			ax_err_var.tick_params(axis='y', length=0)
			
			ax_err_var.set_xlabel(Trnsl('delta_rate_specific_label_short', lang=lang), color=text_color, fontsize=10)
			ax_err_var.tick_params(axis='x', colors=text_color, labelsize=9)
			ax_err_var.spines['bottom'].set_color(text_color)
			ax_err_var.spines['top'].set_visible(False)
			ax_err_var.spines['right'].set_visible(False)
			ax_err_var.spines['left'].set_visible(False)

			y_cursor = ax_var_bottom - section_spacing_fig
		else:
			fig.text(0.5, y_cursor - line_height_fig, Trnsl('no_error_variations_to_display', lang=lang), 
			         color=text_color, ha='center', va='top', fontsize=10, style='italic')
			y_cursor -= (line_height_fig * 2 + section_spacing_fig)
	else: 
		fig.text(0.5, y_cursor - line_height_fig, Trnsl('no_previous_data_for_variations', lang=lang), 
		         color=text_color, ha='center', va='top', fontsize=10, style='italic')
		y_cursor -= (line_height_fig * 2 + section_spacing_fig)
	try:
		plt.savefig(output_filename, 
		            format='svg', # Specifica il formato SVG
		            bbox_inches='tight', 
		            pad_inches=0.3, 
		            facecolor=fig.get_facecolor())
		plt.close(fig) 
	except Exception as e_save:
		if 'fig' in locals() and fig: 
			plt.close(fig)
		print(Trnsl('error_saving_graphical_file', lang=lang, filename=output_filename, error=str(e_save))) # output_filename qui si riferisce al target originale

def load_settings():
	"""Carica le impostazioni dal file JSON o restituisce i default."""
	global overall_settings_changed # Flag per indicare se le impostazioni devono essere salvate all'uscita

	if os.path.exists(SETTINGS_FILE):
		try:
			with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
				loaded_data = json.load(f) # Carica i dati dal file JSON
			
			merged_data = {} # Dizionario che conterrà le impostazioni finali
			
			# Itera su ogni sezione definita in DEFAULT_DATA
			for main_key, default_values in DEFAULT_DATA.items():
				# Estrae la sezione corrispondente dai dati caricati; usa un dizionario vuoto se la sezione non c'è nel file
				loaded_section = loaded_data.get(main_key, {})
				
				# Inizia con una copia dei valori di default per la sezione corrente
				# Questo assicura che tutte le chiavi previste esistano
				if isinstance(default_values, dict):
					merged_section = default_values.copy()
				else: # Se il valore di default non è un dizionario (improbabile per le sezioni principali, ma per sicurezza)
					merged_section = default_values 


				# Logica di unione specifica per la sezione 'historical_rx_data'
				if main_key == "historical_rx_data":
					if isinstance(merged_section, dict): # Assicura che merged_section sia un dizionario
						# max_sessions_to_keep: usa il valore caricato se esiste e valido, altrimenti default
						if "max_sessions_to_keep" in loaded_section and isinstance(loaded_section["max_sessions_to_keep"], int):
							merged_section["max_sessions_to_keep"] = loaded_section["max_sessions_to_keep"]
						# else: il valore di default da default_values.copy() è già in merged_section
						
						# report_interval: usa il valore caricato se esiste e valido, altrimenti default
						if "report_interval" in loaded_section and isinstance(loaded_section["report_interval"], int):
							merged_section["report_interval"] = loaded_section["report_interval"]
						# else: il valore di default è già in merged_section

						# sessions_log: usa il valore caricato se esiste ed è una lista, altrimenti default (lista vuota)
						if "sessions_log" in loaded_section and isinstance(loaded_section["sessions_log"], list):
							merged_section["sessions_log"] = loaded_section["sessions_log"]
						# else: il valore di default (lista vuota) è già in merged_section
				
				# Logica di unione per tutte le altre sezioni (es. app_info, overall_settings)
				# Esegue l'update solo se sia merged_section (dai default) sia loaded_section (dal file) sono dizionari
				elif isinstance(merged_section, dict) and isinstance(loaded_section, dict):
					merged_section.update(loaded_section)
				# Se loaded_section non è un dizionario (es. era null nel JSON e .get ha restituito {} o il valore non-dict stesso),
				# merged_section manterrà i valori di default (o il valore non-dict di default).
				# Questo previene errori se il file JSON ha una struttura inattesa per una sezione.

				# Assegna la sezione processata (unita o di default) a merged_data
				merged_data[main_key] = merged_section
			
			# Determina la lingua per i messaggi di sistema, con fallback robusti
			overall_settings_default = DEFAULT_DATA.get('overall_settings', {})
			app_language_default = overall_settings_default.get('app_language', 'en')
			
			loaded_overall_settings = merged_data.get('overall_settings', overall_settings_default)
			current_app_language = loaded_overall_settings.get('app_language', app_language_default)
			
			print(Trnsl('o_set_loaded', lang=current_app_language))
			return merged_data

		except (json.JSONDecodeError, IOError, TypeError) as e:
			# Se c'è un errore nel caricare, leggere o processare il file, usa i valori di default completi
			print(f"{Trnsl('error_loading_settings_file', lang=DEFAULT_DATA.get('overall_settings', {}).get('app_language', 'en'))} {SETTINGS_FILE}: {e}. {Trnsl('using_default_values', lang=DEFAULT_DATA.get('overall_settings', {}).get('app_language', 'en'))}")
			overall_settings_changed = True # Forza il salvataggio delle impostazioni di default all'uscita
			# Restituisce una copia "profonda" dei default per evitare modifiche accidentali a DEFAULT_DATA
			return {k: (v.copy() if isinstance(v, dict) else v) for k, v in DEFAULT_DATA.items()}

	else: # Il file SETTINGS_FILE non esiste
		# Determina la lingua di default per il messaggio di creazione
		overall_settings_default = DEFAULT_DATA.get('overall_settings', {})
		app_language_default = overall_settings_default.get('app_language', 'en')

		print(Trnsl('o_set_created', lang=app_language_default))
		overall_settings_changed = True # Le impostazioni di default devono essere salvate all'uscita
		return {k: (v.copy() if isinstance(v, dict) else v) for k, v in DEFAULT_DATA.items()}

def save_settings(data):
	"""Salva le impostazioni correnti nel file JSON."""
	global app_language # Necessario per Trnsl qui sotto
	try:
		data_to_save = data.copy()
		if "rxing_stats" in data_to_save and isinstance(data_to_save["rxing_stats"].get("total_time"), dt.timedelta):
			data_to_save["rxing_stats"]["total_time_seconds"] = data_to_save["rxing_stats"]["total_time"].total_seconds()
			data_to_save["rxing_stats"].pop("total_time", None) # Rimuovi il timedelta
		elif "rxing_stats" in data_to_save and "total_time" in data_to_save["rxing_stats"]:
			data_to_save["rxing_stats"].pop("total_time", None)
		with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
			json.dump(data_to_save, f, indent=4, ensure_ascii=False) # indent=4 per leggibilità, ensure_ascii=False per caratteri speciali
		print(Trnsl('o_set_saved', lang=app_language))
	except IOError as e:
		print(f"Errore nel salvare {SETTINGS_FILE}: {e}")
	except TypeError as e:
		print(f"Errore di tipo durante la preparazione dei dati per JSON: {e} - Dati: {data_to_save}")

def ItemChooser(items):
	for i, item in enumerate(items, start=1):
		print(f"{i}. {item}")
	while True:
		try:
			choice = dgt	(prompt="N.? > ", kind="i", imin=1, imax=len(items), default=6)
			if 1 <= choice <= len(items):
				return choice - 1
		except ValueError:
			print("Inserisci un numero valido.")
def KeyboardCW():
	'''Settings for CW and tx with keyboard'''
	global overall_speed, overall_pitch, overall_dashes, overall_spaces, overall_dots, overall_volume, overall_settings_changed, overall_ms, overall_fs, overall_wave
	global app_data 

	# Non è più necessario caricare qui current_max_sessions_g e current_report_interval_x per il prompt,
	# ma verranno letti da app_data quando servono per i comandi.

	print("\n"+Trnsl("h_keyboard",lang=app_language)) # La tua stringa di aiuto principale da translations.py
	
	tosave=False
	rwpm=overall_speed

	while True:
		# Preparazione del prompt (solo WPM/RWPM come da tua preferenza)
		if rwpm is not None and overall_speed != rwpm :
			current_prompt = f"RWPM: {rwpm:.2f}"
		else:
			current_prompt = f"WPM: {overall_speed}"
		
		if tosave:
			print(current_prompt + " SV>", end="", flush=True)
			tosave = False
		else:
			print(current_prompt + "> ", end="", flush=True)
		
		msg_input = sys.stdin.readline()
		if not msg_input: 
			break
		msg = msg_input[:-1] + " " 
		msg_for_cw = msg # Di default, ciò che l'utente scrive viene inviato a CW

		# Gestione comandi base
		if msg == " ": 
			plo, rwpm_temp = CWzator(msg="73", wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
			if rwpm_temp is not None: rwpm = rwpm_temp
			break
		elif msg == "? ":
			print("\n"+Trnsl("h_keyboard",lang=app_language))
			msg_for_cw = "" 
		elif msg == "?? ":
			current_max_sessions_g_val = app_data.get('historical_rx_data', {}).get('max_sessions_to_keep', HISTORICAL_RX_MAX_SESSIONS_DEFAULT)
			current_report_interval_x_val = app_data.get('historical_rx_data', {}).get('report_interval', HISTORICAL_RX_REPORT_INTERVAL)
			switcher_states_config = app_data.get('rx_menu_switcher_states', {})
			parole_min = switcher_states_config.get('parole_filter_min', 0)
			parole_max = switcher_states_config.get('parole_filter_max', 0)
			custom_set_str = switcher_states_config.get('custom_set_string', "")
			t_filter_display = f"{parole_min}-{parole_max}" if parole_min > 0 and parole_max > 0 else Trnsl('filter_not_set_label', lang=app_language)
			y_custom_set_display = f"\"{custom_set_str}\"" if custom_set_str else Trnsl('set_empty_label', lang=app_language)
			base_settings_line1 = f"\n\tWPM: {overall_speed}, Hz: {overall_pitch}, Volume: {int(overall_volume*100)}"
			base_settings_line2 = f"\tL/S/P: {overall_dashes}/{overall_spaces}/{overall_dots}, Wave: {WAVE_TYPES[overall_wave-1]}, MS: {overall_ms}, FS: {SAMPLE_RATES[overall_fs]}."
			history_settings_line = f"\tMax Exercises History (g): {current_max_sessions_g_val}, Report size (x): {current_report_interval_x_val}."
			new_filter_settings_line = f"\tWord Filter (T): {t_filter_display}, Custom Set (Y): {y_custom_set_display}"
			print(base_settings_line1)
			print(base_settings_line2)
			print(history_settings_line)
			print(new_filter_settings_line)
			msg_for_cw = "bk r parameters are bk" 
		elif msg == ".sr ":
			new_fs_index = ItemChooser(SAMPLE_RATES)
			if new_fs_index != overall_fs : 
				overall_fs = new_fs_index
				overall_settings_changed = True
			plo,rwpm_temp=CWzator(msg=f"bk fs is {SAMPLE_RATES[overall_fs]} bk", wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
			if rwpm_temp is not None: rwpm = rwpm_temp
			msg_for_cw = "" 
		elif msg == ".rs ":
			if not (overall_dashes == 30 and overall_spaces == 50 and overall_dots == 50):
				overall_dashes, overall_spaces, overall_dots = 30, 50, 50
				overall_settings_changed = True
			plo,rwpm_temp=CWzator(msg="bk reset ok bk", wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
			if rwpm_temp is not None: rwpm = rwpm_temp
			msg_for_cw = "" 
		elif msg.startswith(".sv "):
			msg_for_cw = msg[4:] 
			tosave = True
		elif msg.startswith("."):
			command_candidate_str = msg[1:].strip() # Es. "y", "t2-5", "w20"
			cmd_letter_parsed = ""
			value_int_parsed = None
			value_str_parsed = "" # Per formati come L-M
			is_value_numeric_type = False # Se value_int_parsed è stato impostato
			is_value_special_format = False # Se value_str_parsed è stato impostato (per L-M)
			match_val_num = re.match(r'([a-zA-Z])(\d+)', command_candidate_str)
			if match_val_num and command_candidate_str == match_val_num.group(0): # Match completo
				cmd_letter_parsed = match_val_num.group(1).lower()
				value_int_parsed = int(match_val_num.group(2))
				is_value_numeric_type = True
			else:
				parts = command_candidate_str.split(maxsplit=1) # Non serve più maxsplit=1 se gestiamo solo cmd e cmdVAL
				cmd_letter_parsed = parts[0].lower() # La prima parte è sempre la lettera del comando
				if len(parts) > 1:
					value_str_parsed = parts[1] # Il resto è il valore stringa (es. "2-5" per .t)
					is_value_special_format = True # Non è numerico, ma potrebbe essere un formato speciale
			command_processed_internally = False
			feedback_cw = ""
			if cmd_letter_parsed == 'y':
				if command_candidate_str == 'y': # Assicura che fosse solo '.y'
					print(Trnsl('invoking_custom_set_editor', lang=app_language))
					custom_string_result = CustomSet(overall_speed)
					current_saved_set = app_data['rx_menu_switcher_states'].get('custom_set_string', "")
					if current_saved_set != custom_string_result:
						app_data['rx_menu_switcher_states']['custom_set_string'] = custom_string_result
						overall_settings_changed = True
					if custom_string_result:
						feedback_cw = Trnsl('custom_set_updated_short_feedback', lang=app_language, num_chars=len(custom_string_result))
					else:
						feedback_cw = "bk r custom set empty bk"
					command_processed_internally = True
					print("\n" + Trnsl("h_keyboard", lang=app_language))
				else:
					feedback_cw = "?"
					command_processed_internally = True # Gestito come errore, non inviare come CW
			elif cmd_letter_parsed == 't':
				if is_value_special_format and '-' in value_str_parsed:
					min_max_parts = value_str_parsed.split('-')
					if len(min_max_parts) == 2 and min_max_parts[0].isdigit() and min_max_parts[1].isdigit():
						p_min = int(min_max_parts[0])
						p_max = int(min_max_parts[1])
						p_min_validated = max(1, min(10, p_min))
						p_max_validated = max(3, min(35, p_max))
						if p_min_validated > p_max_validated: p_min_validated = p_max_validated
						if (app_data['rx_menu_switcher_states'].get('parole_filter_min') != p_min_validated or
							app_data['rx_menu_switcher_states'].get('parole_filter_max') != p_max_validated):
							app_data['rx_menu_switcher_states']['parole_filter_min'] = p_min_validated
							app_data['rx_menu_switcher_states']['parole_filter_max'] = p_max_validated
							overall_settings_changed = True
						feedback_cw = f"bk r word filter is {p_min_validated} {p_max_validated} bk"
						command_processed_internally = True
					else: # Formato L-M non corretto dopo .t
						feedback_cw = "?"
						command_processed_internally = True 
				else:
					feedback_cw = "?"
					command_processed_internally = True
			elif is_value_numeric_type and value_int_parsed is not None:
				if cmd_letter_parsed == "g":
					min_val_g, max_val_g = 20, 5000
					actual_val_g = app_data.get('historical_rx_data', {}).get('max_sessions_to_keep', HISTORICAL_RX_MAX_SESSIONS_DEFAULT)
					new_val_g = max(min_val_g, min(max_val_g, value_int_parsed)) # Usa value_int_parsed
					if actual_val_g != new_val_g:
						app_data['historical_rx_data']['max_sessions_to_keep'] = new_val_g
						sessions_log = app_data['historical_rx_data'].get('sessions_log', [])
						if len(sessions_log) > new_val_g: 
							app_data['historical_rx_data']['sessions_log'] = sessions_log[-new_val_g:]
						overall_settings_changed = True
					feedback_cw = f"bk r max exercises is {new_val_g} bk"
					command_processed_internally = True
				elif cmd_letter_parsed == "x":
					min_val_x, max_val_x = 500, 15000
					actual_val_x = app_data.get('historical_rx_data', {}).get('report_interval', HISTORICAL_RX_REPORT_INTERVAL)
					new_val_x = max(min_val_x, min(max_val_x, value_int_parsed)) # Usa value_int_parsed
					if actual_val_x != new_val_x:
						app_data['historical_rx_data']['report_interval'] = new_val_x
						overall_settings_changed = True
					feedback_cw = f"bk r report size is {new_val_x} bk"
					command_processed_internally = True
				elif cmd_letter_parsed=="w":
					if overall_speed != value_int_parsed:
						new_speed = max(5, min(99, value_int_parsed))
						if overall_speed != new_speed:
							overall_speed = new_speed
							overall_settings_changed=True
					feedback_cw = f"bk r w is {overall_speed} bk"
					command_processed_internally = True
				elif cmd_letter_parsed=="m":
					if overall_ms != value_int_parsed:
						new_ms = max(1, min(30, value_int_parsed))
						if overall_ms != new_ms:
							overall_ms = new_ms
							overall_settings_changed=True
					feedback_cw = f"bk r ms is {overall_ms} bk"
					command_processed_internally = True
				elif cmd_letter_parsed=="f": 
					new_wave_idx_user = max(1, min(len(WAVE_TYPES), value_int_parsed))
					if overall_wave != new_wave_idx_user: 
						overall_wave = new_wave_idx_user
						overall_settings_changed=True
					feedback_cw = f"bk r wave is {WAVE_TYPES[overall_wave-1]} bk" # Usa overall_wave-1 per indice 0-based
					command_processed_internally = True
				elif cmd_letter_parsed=="h":
					if overall_pitch != value_int_parsed:
						new_pitch = max(130, min(2700, value_int_parsed))
						if overall_pitch != new_pitch:
							overall_pitch = new_pitch
							overall_settings_changed=True
					feedback_cw = f"bk r h is {overall_pitch} bk"
					command_processed_internally = True
				elif cmd_letter_parsed=="l":
					if overall_dashes != value_int_parsed:
						new_dashes = max(1, min(99, value_int_parsed))
						if overall_dashes != new_dashes:
							overall_dashes = new_dashes
							overall_settings_changed=True
					feedback_cw = f"bk r l is {overall_dashes} bk"
					command_processed_internally = True
				elif cmd_letter_parsed=="s":
					if overall_spaces != value_int_parsed:
						new_spaces = max(3, min(99, value_int_parsed))
						if overall_spaces != new_spaces:
							overall_spaces = new_spaces
							overall_settings_changed=True
					feedback_cw = f"bk r s is {overall_spaces} bk"
					command_processed_internally = True
				elif cmd_letter_parsed=="p":
					if overall_dots != value_int_parsed:
						new_dots = max(1, min(99, value_int_parsed))
						if overall_dots != new_dots:
							overall_dots = new_dots
							overall_settings_changed=True
					feedback_cw = f"bk r p is {overall_dots} bk"
					command_processed_internally = True
				elif cmd_letter_parsed=="v":
					new_volume_percent = max(0, min(100, value_int_parsed))
					if abs(overall_volume * 100 - new_volume_percent) > 0.01 : 
						overall_volume = new_volume_percent / 100.0
						overall_settings_changed=True
					feedback_cw = f"bk r v is {new_volume_percent} bk"
					command_processed_internally = True
			if command_processed_internally:
				if feedback_cw: # Solo se un comando ha specificato un feedback
					plo,rwpm_temp=CWzator(msg=feedback_cw, wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
					if rwpm_temp is not None: rwpm = rwpm_temp
				msg_for_cw = ""
		if msg_for_cw.strip(): 
			plo,rwpm_temp=CWzator(msg=msg_for_cw, wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave, file=tosave)
			if rwpm_temp is not None: 
				rwpm = rwpm_temp
			elif msg_for_cw.strip() : # Se c'era testo ma CWzator ha fallito (es. carattere non valido in msg_for_cw)
				rwpm = overall_speed # Resetta rwpm per evitare None nel prompt
			if tosave: tosave = False 
	print(Trnsl('bye_message', lang=app_language) + "\n") 
	return

def LangSelector():
	print("\n" + Trnsl('select_language', lang=app_language) + "\n")
	return menu(MNLANG, ntf=Trnsl('not_a_valid_language', lang=app_language), show=True, keyslist=True)
def StringCleaning(stringa):
	stringa = stringa.strip()
	stringa = stringa.lower()
	cleaned = re.sub(r"[^a-z0-9\sàèéìòù@.,;:!?\'\"()-=]", "", stringa)
	cleaned = re.sub(r"\s+", " ", cleaned)
	return cleaned
def CreateDictionary():
	print(Trnsl('attention_message', lang=app_language))
	import Words_Creator
	Words_Creator.Start()
	return
def FilterWord(w):
	print(Trnsl('filter_words_prompt', lang=app_language))
	ex=False
	while True:
		while True:
			mnmx=input(Trnsl('insert_min_max', lang=app_language))
			if mnmx=="":
				ex=True
				break
			elif "." in mnmx:
				x=mnmx.split(".")
				mn,mx=x[0],x[1]
				if mn.isdigit() and mx.isdigit(): break
				else: print(Trnsl('not_numbers', lang=app_language))
			else: print(Trnsl('try_again', lang=app_language))
		if ex: break
		mn=int(mn); mx=int(mx)
		if mn<1: mn=1
		elif mn>10: mn=10
		if mx<3: mx=3
		elif mx>35: mx=35
		print(Trnsl('filtering_range', lang=app_language, mn=mn, mx=mx))
		w1=[l for l in w if len(l)>=mn and len(l)<=mx]
		scelta=key(prompt=Trnsl('confirm_word_count', lang=app_language, word_count=len(w1))).lower()
		if scelta=="y": break
	if ex: return w
	else: return w1

def CustomSet(overall_speed):
	global app_data, app_language # Per accedere al log storico e alle traduzioni
	cs = set() # Il set che conterrà i caratteri scelti dall'utente
	prefill_prompt_text = Trnsl('custom_set_use_prefill_prompt', lang=app_language)
	yes_char = Trnsl('yes_key_default', lang=app_language)
	no_char = Trnsl('no_key_default', lang=app_language)
	use_prefill_choice = key(prompt=f"{prefill_prompt_text} [{yes_char}/{no_char}]: ").lower()
	if use_prefill_choice == yes_char:
		prefilled_chars_list = []
		sessions_log = app_data.get('historical_rx_data', {}).get('sessions_log', [])
		if sessions_log:
			aggregated_session_errors = {}
			for session_data in sessions_log:
				for char, count in session_data.get('errors_detail_session', {}).items():
					if isinstance(char, str) and len(char) == 1 and char.lower() in VALID_MORSE_CHARS_FOR_CUSTOM_SET:
						aggregated_session_errors[char.lower()] = aggregated_session_errors.get(char.lower(), 0) + count
			if aggregated_session_errors:
				sorted_errors_from_log = sorted(aggregated_session_errors.items(), key=lambda item: (-item[1], item[0]))
				prefilled_chars_list = [char for char, count in sorted_errors_from_log[:10]]
		if prefilled_chars_list:
			print(Trnsl('custom_set_prefilled_with_errors', lang=app_language, chars=", ".join(c.upper() for c in prefilled_chars_list)))
			for char_err in prefilled_chars_list:
				cs.add(char_err) # Aggiunti già in minuscolo
		else:
			random_chars_pool = list(VALID_MORSE_CHARS_FOR_CUSTOM_SET)
			if random_chars_pool:
				num_to_add = min(10, len(random_chars_pool))
				cs.update(random.sample(random_chars_pool, num_to_add))
				if cs:
					print(Trnsl('custom_set_prefilled_with_random', lang=app_language, chars=", ".join(sorted(c.upper() for c in cs))))
				else: # Improbabile se random_chars_pool non è vuoto, ma per sicurezza
					print(Trnsl('custom_set_prefill_failed_no_chars', lang=app_language))
			else: # Se VALID_MORSE_CHARS_FOR_CUSTOM_SET fosse vuoto (improbabile)
				print(Trnsl('custom_set_prefill_failed_no_chars', lang=app_language))
	print(Trnsl('custom_set_modify_prompt_intro', lang=app_language))
	while True:
		current_set_display = "".join(sorted(list(cs))) # Mostra i caratteri ordinati
		user_input_char = key(prompt="\n"+current_set_display)
		if user_input_char == "\r":  # Tasto Invio
			if len(cs) >= 2:
				break # Esce dal loop per iniziare l'esercizio
			else:
				CWzator(msg="?", wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
				continue # Continua il loop per permettere all'utente di aggiungere caratteri
		# Se l'input è un singolo carattere stampabile (la funzione key() dovrebbe restituire solo questo o tasti speciali)
		if len(user_input_char) == 1 and user_input_char.isprintable():
			char_typed_lower = user_input_char.lower()
			if char_typed_lower not in VALID_MORSE_CHARS_FOR_CUSTOM_SET:
				CWzator(msg="?", wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
				continue
			if char_typed_lower in cs:
				cs.remove(char_typed_lower)
			else:
				cs.add(char_typed_lower)
				CWzator(msg=char_typed_lower, wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
		elif user_input_char != "\r": # Evita il '?' se era solo un input non valido ma non Invio
			CWzator(msg="?", wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
	return "".join(sorted(list(cs))) # Restituisce una stringa ordinata dei caratteri nel set

def GeneratingGroup(kind, length, wpm, customized_set_param=None): # Aggiunto customized_set_param
	if kind == "1": # Lettere
		if not LETTERE_MORSE_POOL: return "ERR_LP" # Errore: Pool Lettere Vuoto
		pool = list(LETTERE_MORSE_POOL)
		return ''.join(random.choices(pool, k=length))
	elif kind == "2": # Numeri
		if not NUMERI_MORSE_POOL: return "ERR_NP" # Errore: Pool Numeri Vuoto
		pool = list(NUMERI_MORSE_POOL)
		return ''.join(random.choices(pool, k=length))
	elif kind == "3": # Alfanumerici (Lettere + Numeri)
		pool_alfanum = list(LETTERE_MORSE_POOL | NUMERI_MORSE_POOL) # Unione dei due set
		if not pool_alfanum: return "ERR_AP" # Errore: Pool Alfanumerici Vuoto
		return ''.join(random.choices(pool_alfanum, k=length))
	elif kind == "4": # Custom Set
		# Usa il parametro se fornito e valido, altrimenti tenta il globale (meno ideale), poi errore.
		set_da_usare = None
		if customized_set_param and len(customized_set_param) >= 1: # Lunghezza minima 1 per custom se kind 4 è scelto
			set_da_usare = customized_set_param
		elif customized_set and len(customized_set) >= 1: # Fallback al globale (considera di rimuoverlo)
			set_da_usare = customized_set 
		
		if not set_da_usare:
			return "ERR_CS" # Errore: Custom Set non valido o non fornito
		# customized_set_param (o customized_set) è già una stringa di caratteri unici
		return ''.join(random.choices(list(set_da_usare), k=length)) # random.choices su lista di caratteri del set
	elif kind == "5": # Parole dal dizionario
		if not words: return "ERR_WD" # Errore: Lista Parole Vuota
		return random.choice(words)
	elif kind == "S": # NUOVO: Simboli
		if not SIMBOLI_MORSE_POOL: return "ERR_SP" # Errore: Pool Simboli Vuoto
		pool = list(SIMBOLI_MORSE_POOL)
		return ''.join(random.choices(pool, k=length))
	
	# Fallback se il 'kind' non è riconosciuto
	return "ERR_KD" # Errore: Kind non Definito

def Mkdqrz(c):
	#Sub of Txing
	q=''
	c=c[0]
	for j in str(c):
		if j.isdigit():
			q+=random.choice(string.digits)
		else:
			q+=random.choice(string.ascii_uppercase)
	return q
def Txing():
	# QRZ - Programma che crea calls inventati e numeri progressivi, da usare negli esercizi CW
	# Data concepimento 30/9/2022 by IZ4APU.
	# Now part of CWAPU, dec 22nd, 2022.
	print(Trnsl('transmitting_exercise', lang=app_language))
	cont=1
	while True:
		c=random.choices(list(MDL.keys()), weights=MDL.values(), k=1)
		qrz=Mkdqrz(c)
		pgr=random.randint(1,9999)
		prompt=f"- {cont:0>3} {qrz} 5nn {pgr:0>4}"
		wait=key(prompt)
		print()
		if ord(wait)==27: break
		cont+=1
	print(Trnsl('bye_message', lang=app_language))
	return
def Count():
	global app_data 
	print(Trnsl('counting_prompt', lang=app_language))
	from	GBUtils import Acusticator as Ac
	esnum = app_data['counting_stats'].get('exercise_number', 1) 
	cont = 0
	corr = 0
	scelta = ""
	Ac([350,.2,0,.5],sync=True)
	print(Trnsl('exercise_number', lang=app_language, esnum=esnum))
	while True:
		if cont % 100 == 0: Ac([1600, .2,0,.5],sync=True)
		elif cont % 50 == 0: Ac([1150, .080,0,.5],sync=True)
		elif cont % 25 == 0: Ac([900, .060,0,.5],sync=True)
		elif cont % 10 == 0: Ac([600, .040,0,.5],sync=True)
		if corr > 0:
			prompt = f"T{cont}, {corr*100/cont:.2f}%, C{corr}/N{cont-corr}> "
		else:
			prompt = "T1, 0%> "
		scelta=key("\n"+prompt)
		if scelta == " ":
			corr += 1
			Ac([1380,.015,0,.5],sync=True)
		elif ord(scelta) == 27: break
		else:
			Ac([310,.025,0,.5],sync=True)
		cont+=1
	cont-=1
	if cont > 0:
		pde=100-corr*100/cont
	else:
		pde=100
	print(Trnsl('total_correct', lang=app_language, cont=cont, corr=corr, pde=pde))
	if pde<=6:
		print(Trnsl('passed', lang=app_language))
	else:
		print(Trnsl('failed', lang=app_language, difference=pde-6))
	if cont >= 100:
		with open("CWapu_Diary.txt", "a", encoding='utf-8') as f:
			nota=input(Trnsl('note_on_exercise', lang=app_language))
			print(Trnsl('report_saved', lang=app_language))
			date = f"{lt()[0]}/{lt()[1]}/{lt()[2]}"
			time = f"{lt()[3]}, {lt()[4]}"
			f.write(Trnsl('counting_exercise_report', lang=app_language, esnum=esnum, date=date, time=time))
			f.write(Trnsl('total_correct_report', lang=app_language, cont=cont, corr=corr, pde=pde))
			if pde<=6:
				f.write(Trnsl('passed', lang=app_language) + "\n")
			else:
				f.write(Trnsl('failed', lang=app_language, difference=pde-6) + "\n")
			if nota != "":
				f.write(Trnsl('note_with_text', lang=app_language, nota=nota))
			else:
				f.write(Trnsl('empty_note', lang=app_language) + "\n***\n")
	else:
		print(Trnsl('groups_received_few', lang=app_language, cont=cont))
	esnum = app_data['counting_stats'].get('exercise_number', 1) + 1 
	app_data['counting_stats']['exercise_number'] = esnum
	global overall_settings_changed
	overall_settings_changed = True # Segnala che i dati sono cambiati	
	print(Trnsl('bye_message', lang=app_language))
	return
def MistakesCollectorInStrings(right, received):
	differences = []
	# Usa SequenceMatcher per individuare le differenze con precisione
	s = difflib.SequenceMatcher(None, right, received)
	for tag, i1, i2, j1, j2 in s.get_opcodes():
		if tag == 'replace' or tag == 'delete':
			differences.extend(right[i1:i2])
		elif tag == 'insert':
			differences.extend(received[j1:j2])
	return ''.join(differences)
def AlwaysRight(sent_items, error_counts_dict):
	letters_sent = set("".join(sent_items))
	letters_misspelled = set(error_counts_dict.keys())
	return letters_sent - letters_misspelled
def Rxing():
	# receiving exercise
	global app_data, overall_settings_changed, overall_speed, words, customized_set
	print(Trnsl('time_to_receive', lang=app_language))
	try:
		with open('words.txt', 'r', encoding='utf-8') as file:
			words = file.readlines()
			words = [line.strip() for line in words]
			print(Trnsl('dictionary_loaded', lang=app_language, word_count=len(words)))
	except FileNotFoundError:
		print(Trnsl('file_not_found', lang=app_language))
		del MNRXKIND["5"]
	rx_stats = app_data['rxing_stats']
	totalcalls = rx_stats.get('total_calls', 0)
	sessions = rx_stats.get('sessions', 1)
	totalget = rx_stats.get('total_correct', 0) 
	totalwrong = rx_stats.get('total_wrong_items', 0) 
	totaltime_seconds = rx_stats.get('total_time_seconds', 0.0)
	totaltime = dt.timedelta(seconds=totaltime_seconds) 
	print(Trnsl('got_data', lang=app_language, wpm=overall_speed, sessions=sessions-1,
                totalcalls=totalcalls, totalget=totalget, totalwrong=totalwrong,
                totaltime=str(totaltime).split('.')[0]))	
	callssend=[]; average_rwpm=0.0 
	dz_mistakes={}
	calls = 1
	callsget = []
	callswrong = []
	callsrepeated = 0
	minwpm = 100
	maxwpm = 0
	repeatedflag = False  # Flag per indicare se l'ultimo item è stato ripetuto
	# Carica le impostazioni per la cronologia all'inizio della sessione Rxing
	historical_rx_settings = app_data.get('historical_rx_data', {})
	max_sessions_to_keep = historical_rx_settings.get('max_sessions_to_keep', HISTORICAL_RX_MAX_SESSIONS_DEFAULT)
	report_interval = historical_rx_settings.get('report_interval', HISTORICAL_RX_REPORT_INTERVAL)
	overall_speed = dgt(prompt=Trnsl('set_wpm', lang=app_language, wpm=overall_speed),kind="i",imin=10,imax=85,default=overall_speed)
	rwpm = overall_speed # rwpm per la sessione corrente
	menu_config_scelta = seleziona_modalita_rx()
	if not menu_config_scelta:
		return
	active_states = menu_config_scelta['active_switcher_states']
	parole_filtrate_per_sessione = menu_config_scelta['parole_filtrate_list']
	custom_set_attivo_per_sessione = menu_config_scelta['custom_set_string_active']
	lunghezza_gruppo_per_generati = menu_config_scelta['group_length_for_generated']
	_clear_screen_ansi()
	active_labels_for_display = []
	for item_cfg_ks in RX_SWITCHER_ITEMS:
		if active_states.get(item_cfg_ks['key_state']):
			active_labels_for_display.append(Trnsl(item_cfg_ks['label_key'], lang=app_language).capitalize())
	if not active_labels_for_display:
		kindstring = "N/A" # Non dovrebbe succedere
	elif len(active_labels_for_display) == 1:
		kindstring = active_labels_for_display[0]
	else:
		kindstring = Trnsl('mixed_exercise_types_label', lang=app_language, types=", ".join(active_labels_for_display))
	how_many_calls=dgt(prompt=Trnsl('how_many', lang=app_language),kind="i",imin=10,imax=1000,default=0)
	tmp_fix_speed=key(Trnsl('fix_yes', lang=app_language)).lower()
	if tmp_fix_speed=="y":
		fix_speed=True
	else:
		fix_speed=False
	print(Trnsl('careful_type', lang=app_language, kindstring=kindstring))
	attesa=key()
	print(Trnsl('begin_session', lang=app_language, sessions=sessions))
	starttime=dt.datetime.now()
	while True:
		if how_many_calls > 0 and len(callssend) >= how_many_calls:
			break
		qrz_to_send = genera_singolo_item_esercizio_misto(active_states, lunghezza_gruppo_per_generati, custom_set_attivo_per_sessione, parole_filtrate_per_sessione)
		if qrz_to_send is None or qrz_to_send == "ERROR_NO_VALID_TYPES":
			print(Trnsl('error_no_item_generated_rx', lang=app_language))
			break # Interrompe il loop dell'esercizio Rxing
		pitch=random.randint(250, 1050)
		prompt = f"S{sessions}-#{calls} - WPM{rwpm:.0f}/{(average_rwpm / len(callsget) if len(callsget) else rwpm):.2f} - +{len(callsget)}/-{len(callswrong)}> "
		plo,rwpm=CWzator(msg=qrz_to_send, wpm=overall_speed, pitch=pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
		guess=dgt(prompt=prompt, kind="s", smin=0, smax=64)
		if guess==".":
			break
		needs_processing = True
		if guess == "" or guess.endswith("?"):
			repeatedflag=True
			partial_input = ""
			prompt_indicator = "% "
			if guess.endswith("?"):
				partial_input = guess[:-1]
				prompt_indicator = f"% {partial_input}"
			prompt = f"S{sessions}-#{calls} - WPM{rwpm:.0f}/{(average_rwpm / len(callsget) if len(callsget) else rwpm):.2f} - +{len(callsget)}/-{len(callswrong)} - {prompt_indicator}"
			plo,rwpm=CWzator(msg=qrz_to_send, wpm=overall_speed, pitch=pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume,	ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
			new_guess = dgt(prompt=prompt, kind="s", smin=0, smax=64) 
			if new_guess == ".":
				needs_processing = False
				break
			else:
				guess = partial_input + new_guess
		if needs_processing:
			original_qrz = qrz_to_send
			callssend.append(original_qrz)
			guess = guess.lower()
			if original_qrz == guess:
				tplo,trwpm=CWzator(msg="r _ _ ", wpm=overall_speed, pitch=pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume,	ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave,sync=True)
				callsget.append(original_qrz)
				average_rwpm+=rwpm
				if repeatedflag: callsrepeated+=1
				if not fix_speed and overall_speed<100: overall_speed+=1
			else:
				callswrong.append(original_qrz)
				tplo,trwpm=CWzator(msg="? _ _ ", wpm=overall_speed, pitch=pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume,	ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave,sync=True)
				diff=MistakesCollectorInStrings(original_qrz, guess)
				diff_ratio=(1 - difflib.SequenceMatcher(None, original_qrz, guess).ratio()) * 100
				print(f"TX: {original_qrz.upper()} RX: {guess.upper()} <>: {diff.upper()} RT: {int(diff_ratio):d}")
				dz_mistakes[len(callssend)] = (original_qrz, guess)
				if not fix_speed and overall_speed > 15: overall_speed -= 1
			calls += 1
			if overall_speed > maxwpm: maxwpm = overall_speed
			if overall_speed < minwpm: minwpm = overall_speed
			repeatedflag = False
	exerctime=dt.datetime.now()-starttime
	print(Trnsl('over_check', lang=app_language))
	if len(callssend) >= 10: 
		send_char = sum(len(j) for j in callssend) 
		sent_chars_detail_this_session = {}
		for item_str in callssend: # 'callssend' contiene gli item della sessione corrente
			for char_sent in item_str:
				sent_chars_detail_this_session[char_sent] = sent_chars_detail_this_session.get(char_sent, 0) + 1		
		total_sent_processed = len(callssend)
		percentage_correct = (len(callsget) * 100 / total_sent_processed) if total_sent_processed > 0 else 0
		print(Trnsl('session_summary', lang=app_language,
            sessions=sessions,
            calls=total_sent_processed,        # <--- MODIFICA QUI: usa il conteggio reale
            kindstring=kindstring,
            callsget_len=len(callsget),
            percentage=percentage_correct)) # <--- MODIFICA QUI: usa la percentuale corretta		
		first_shot_correct = len(callsget) - callsrepeated
		first_shot_percentage = (first_shot_correct * 100 / len(callsget)) if len(callsget) > 0 else 0
		repetitions_percentage = (callsrepeated * 100 / len(callsget)) if len(callsget) > 0 else 0		
		print(Trnsl('first_shot', lang=app_language, first_shot=len(callsget)-callsrepeated, first_shot_percentage=(len(callsget)-callsrepeated)*100/len(callsget)))
		print(Trnsl('with_repetition', lang=app_language, repetitions=callsrepeated, kindstring=kindstring, repetitions_percentage=callsrepeated*100/len(callsget)))
		print(Trnsl('speed_summary', lang=app_language, minwpm=minwpm, maxwpm=maxwpm, range_wpm=maxwpm-minwpm, average_wpm=average_rwpm/len(callsget)))
		avg_wpm_calc = (average_rwpm / len(callsget)) if len(callsget) > 0 else overall_speed # Usa overall_speed se non ci sono risposte corrette
		char_error_counts = {} # Dizionario per accumulare gli errori: {'carattere': conteggio}
		total_mistakes_calculated = 0 # Contatore separato per il totale errori		print(Trnsl('character_mistakes', lang=app_language))
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
		print(Trnsl('character_mistakes', lang=app_language))
		if total_mistakes_calculated > 0:
			sorted_errors = sorted(char_error_counts.items(), key=lambda item: (-item[1], item[0]))
			for char, count in sorted_errors:
				percentage_vs_total_session_chars = (count / send_char * 100) if send_char > 0 else 0.0
				total_sent_of_this_char_session = sent_chars_detail_this_session.get(char, 0)
				percentage_vs_this_char_sent_session = (count / total_sent_of_this_char_session * 100) if total_sent_of_this_char_session > 0 else 0.0
				print(f"    '{char.upper()}': {count} ({percentage_vs_total_session_chars:.2f}% {Trnsl('of_total_chars', lang=app_language)}, " \
			 	     f"{percentage_vs_this_char_sent_session:.2f}% {Trnsl('of_specific_char_sent', lang=app_language, char_upper=char.upper())})")
			mistake_percentage = (total_mistakes_calculated * 100 / send_char) if send_char > 0 else 0
			print(Trnsl('total_mistakes', lang=app_language, global_mistakes=total_mistakes_calculated, send_char=send_char, mistake_percentage=mistake_percentage))
			good_letters = AlwaysRight(callssend, char_error_counts) # Passa il dizionario degli errori
			print(Trnsl('never_misspelled', lang=app_language, good_letters=" ".join(sorted(good_letters)).upper()))
		else:
			print(Trnsl('no_mistakes_recorded', lang=app_language)) # Aggiungi una traduzione per questo caso
		# Logica per salvare i dati storici della sessione
		historical_rx_settings = app_data.get('historical_rx_data', {})
		max_sessions_to_keep = historical_rx_settings.get('max_sessions_to_keep', HISTORICAL_RX_MAX_SESSIONS_DEFAULT)
		report_interval = historical_rx_settings.get('report_interval', HISTORICAL_RX_REPORT_INTERVAL)
		# 'callssend' è la lista degli item (stringhe) originali inviati, già in minuscolo.
		session_data_for_history = {
			"timestamp_iso": starttime.isoformat(),
			"duration_seconds": exerctime.total_seconds(),
			"wpm_min": minwpm,
			"wpm_max": maxwpm,
			"wpm_avg": avg_wpm_calc,
			"items_sent_session": len(callssend),
			"items_correct_session": len(callsget),
			"chars_sent_session": send_char,
			"errors_detail_session": char_error_counts,
			"total_errors_chars_session": total_mistakes_calculated,
			"sent_chars_detail_session": sent_chars_detail_this_session}
		historical_rx_log = app_data.get('historical_rx_data', {}).get('sessions_log', [])
		historical_rx_log.append(session_data_for_history)
		while len(historical_rx_log) > max_sessions_to_keep:
			historical_rx_log.pop(0)
		if 'historical_rx_data' not in app_data: 
			app_data['historical_rx_data'] = DEFAULT_DATA['historical_rx_data'].copy()
		app_data['historical_rx_data']['chars_since_last_report'] = app_data['historical_rx_data'].get('chars_since_last_report', 0) + send_char
		app_data['historical_rx_data']['sessions_log'] = historical_rx_log
		overall_settings_changed = True
		if report_interval > 0 and app_data['historical_rx_data']['chars_since_last_report'] >= report_interval:
			print(Trnsl('generating_historical_report', lang=app_language)) 
			generate_historical_rx_report()
			app_data['historical_rx_data']['chars_since_last_report'] = 0
		f=open("CWapu_Diary.txt", "a", encoding='utf-8')
		print(Trnsl('report_saved', lang=app_language))
		date = f"{lt()[0]}/{lt()[1]}/{lt()[2]}"
		time = f"{lt()[3]}, {lt()[4]}"
		f.write(Trnsl('receiving_exercise_report', lang=app_language, sessions=sessions, date=date, time=time))
		f.write(Trnsl('session_summary', lang=app_language,
              sessions=sessions,
              calls=total_sent_processed, # <-- Stessa modifica qui
              kindstring=kindstring,
              callsget_len=len(callsget),
              percentage=percentage_correct) + "\n") # <-- Stessa modifica qui
		f.write(Trnsl('first_shot', lang=app_language, first_shot=first_shot_correct, first_shot_percentage=first_shot_percentage) + "\n")
		f.write(Trnsl('with_repetition', lang=app_language, repetitions=callsrepeated, kindstring=kindstring, repetitions_percentage=repetitions_percentage) + "\n")
		f.write(Trnsl('speed_summary', lang=app_language, minwpm=minwpm, maxwpm=maxwpm, range_wpm=maxwpm-minwpm, average_wpm=avg_wpm_calc) + "\n")
		f.write(Trnsl('character_mistakes', lang=app_language))
		if total_mistakes_calculated > 0:
			for char, count in sorted_errors:
				percentage_vs_total_session_chars = (count / send_char * 100) if send_char > 0 else 0.0
				total_sent_of_this_char_session = sent_chars_detail_this_session.get(char, 0)
				percentage_vs_this_char_sent_session = (count / total_sent_of_this_char_session * 100) if total_sent_of_this_char_session > 0 else 0.0
				f.write(f"\n    '{char.upper()}': {count} ({percentage_vs_total_session_chars:.2f}% {Trnsl('of_total_chars', lang=app_language)}, " \
				        f"{percentage_vs_this_char_sent_session:.2f}% {Trnsl('of_specific_char_sent', lang=app_language, char_upper=char.upper())})")
			f.write("\n") # Aggiungi newline dopo la lista
			f.write(Trnsl('total_mistakes', lang=app_language, global_mistakes=total_mistakes_calculated, send_char=send_char, mistake_percentage=mistake_percentage))
			f.write(Trnsl('never_misspelled', lang=app_language, good_letters=" ".join(sorted(good_letters)).upper()))
		else:
			f.write("\n" + Trnsl('no_mistakes_recorded', lang=app_language) + "\n")
		f.write(Trnsl('list_of_wrong_words', lang=app_language))
		# Ordina dz_mistakes per chiave (numero progressivo) prima di scrivere
		for k, v in sorted(dz_mistakes.items()):
			rslt = MistakesCollectorInStrings(v[0], v[1]) # Questa funzione può rimanere per il dettaglio
			f.write(Trnsl('wrong_word_entry', lang=app_language, k=k, tx=v[0].upper(), rx=v[1].upper(), dif=rslt.upper()))
		if report_interval > 0:
			chars_done = app_data['historical_rx_data'].get('chars_since_last_report', 0)
			chars_target = report_interval
			percentage_done = (chars_done / chars_target * 100) if chars_target > 0 else 0.0
			chars_missing = chars_target - chars_done
			print(Trnsl('chars_to_next_report_progress', lang=app_language, 
						x=chars_done, 
						y=chars_target, 
						z=f"{percentage_done:.2f}", 
						w=chars_missing))
		else:
			print(Trnsl('reports_disabled', lang=app_language))
		nota=dgt(prompt=Trnsl('note_on_exercise', lang=app_language), kind="s", smin=0, smax=512)
		if nota != "":
			f.write(Trnsl('note_with_text', lang=app_language, nota=nota))
		else:
			f.write("\n" + Trnsl('empty_note', lang=app_language) + "\n***\n")
		f.close()	
	else:
		print(Trnsl('received_too_few', lang=app_language, kindstring=kindstring)) # Usa len(callssend)?		
	current_session_items = len(callssend)
	current_session_correct = len(callsget)
	current_session_wrong = len(dz_mistakes)
	new_totalcalls = totalcalls + current_session_items
	new_totalget = totalget + current_session_correct
	new_totalwrong = totalwrong + current_session_wrong
	new_totaltime = totaltime + exerctime # Somma di timedelta
	app_data['rxing_stats'].update({
		"total_calls": new_totalcalls,
		"sessions": sessions + 1, # Incrementa il numero di sessione per il prossimo avvio
		"total_correct": new_totalget,
		"total_wrong_items": new_totalwrong,
		"total_time_seconds": new_totaltime.total_seconds() # Salva come secondi totali
	})
	overall_settings_changed = True # Segnala che i dati globali sono cambiati e vanno salvati
	print(Trnsl('session_saved', lang=app_language, session_number=sessions, duration=str(exerctime).split('.')[0]))
	return

def _calculate_aggregates(session_list):
	"""
	Calcola statistiche aggregate da una lista di dati di sessione.
	Restituisce un dizionario con le statistiche aggregate.
	"""
	if not session_list:
		return {
			"num_sessions_in_block": 0, "total_duration_seconds": 0.0,
			"wpm_min_overall": 0, "wpm_max_overall": 0, "wpm_avg_overall_cpm_based": 0.0,
			"total_items_sent": 0, "total_items_correct": 0,
			"total_chars_sent_overall": 0, "aggregated_errors_detail": {},
			"total_errors_chars_overall": 0
		}
	total_duration_seconds = sum(s.get("duration_seconds", 0) for s in session_list)
	total_chars_sent_overall = sum(s.get("chars_sent_session", 0) for s in session_list)
	aggregated_sent_chars_detail = {}
	for s in session_list:
		for char, count in s.get("sent_chars_detail_session", {}).items():
			aggregated_sent_chars_detail[char] = aggregated_sent_chars_detail.get(char, 0) + count	
	# WPM min e max complessivi
	# Filtra i valori non significativi (es. 0 se non impostato, o 100 per minwpm iniziale)
	valid_min_wpms = [s.get("wpm_min", 0) for s in session_list if s.get("wpm_min", 0) > 0 and s.get("wpm_min", 0) != 100]
	valid_max_wpms = [s.get("wpm_max", 0) for s in session_list if s.get("wpm_max", 0) > 0]
	wpm_min_overall = min(valid_min_wpms) if valid_min_wpms else 0
	wpm_max_overall = max(valid_max_wpms) if valid_max_wpms else 0
	if session_list:
		sum_of_session_avg_wpms = sum(s.get("wpm_avg", 0.0) for s in session_list) # Usa 0.0 come default se 'wpm_avg' manca
		wpm_avg_of_session_avgs = sum_of_session_avg_wpms / len(session_list)
	else:
		wpm_avg_of_session_avgs = 0.0
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
		"aggregated_errors_detail": aggregated_errors_detail, # Errori commessi
		"total_errors_chars_overall": total_errors_chars_overall,
		"aggregated_sent_chars_detail": aggregated_sent_chars_detail # <-- NUOVA CHIAVE AGGIUNTA (Caratteri inviati)
	}

def generate_historical_rx_report():
	global app_data, app_language # Necessario per Trnsl e accedere ai dati
	historical_data = app_data.get('historical_rx_data', {})
	sessions_log = historical_data.get('sessions_log', [])
	# max_sessions_to_keep determina il 'target' N per il report
	max_sessions_for_report_config = historical_data.get('max_sessions_to_keep', HISTORICAL_RX_MAX_SESSIONS_DEFAULT)
	# report_interval è ogni quante sessioni si genera il report (e quindi per il delta)
	report_gen_interval = historical_data.get('report_interval', HISTORICAL_RX_REPORT_INTERVAL)
	if not sessions_log:
		print(Trnsl('no_historical_data_to_report', lang=app_language)) # Crea traduzione
		return
	# Determina il blocco corrente di sessioni per il report
	# Prende le ultime 'max_sessions_for_report_config' sessioni, o meno se non ce ne sono abbastanza
	num_to_take_current = min(len(sessions_log), max_sessions_for_report_config)
	current_block_sessions = sessions_log[-num_to_take_current:] if num_to_take_current > 0 else []
	if not current_block_sessions:
		print(Trnsl('no_sessions_in_current_block_for_report', lang=app_language)) # Crea traduzione
		return
	current_aggregates = _calculate_aggregates(current_block_sessions)
	num_sessions_in_current_report = current_aggregates["num_sessions_in_block"]
	g_value = historical_data.get('max_sessions_to_keep', HISTORICAL_RX_MAX_SESSIONS_DEFAULT)
	x_value = historical_data.get('report_interval', HISTORICAL_RX_REPORT_INTERVAL)
	report_filename = f"CWapu_Historical_Statistics_G_{g_value}_X_{x_value}.html"
	# Determina il blocco precedente per il calcolo delle variazioni
	previous_aggregates = None
	if len(sessions_log) >= report_gen_interval: # Deve esserci almeno un intervallo di sessioni passate
		end_index_prev_block = len(sessions_log) - report_gen_interval
		if end_index_prev_block > 0:
			# Il blocco precedente ha la stessa logica di lunghezza del blocco corrente
			num_to_take_previous = min(end_index_prev_block, max_sessions_for_report_config)
			start_index_prev_block = max(0, end_index_prev_block - num_to_take_previous)
			previous_block_sessions = sessions_log[start_index_prev_block:end_index_prev_block]
			if previous_block_sessions:
				previous_aggregates = _calculate_aggregates(previous_block_sessions)
	try:
		with open(report_filename, "w", encoding="utf-8") as f:
			# --- INIZIO DOCUMENTO HTML ---
			f.write("<!DOCTYPE html>\n")
			f.write("<html lang=\"{html_lang}\">\n".format(html_lang=app_language[:2])) # Usa solo la parte 'it' o 'en'
			f.write("<head>\n")
			f.write("    <meta charset=\"UTF-8\">\n")
			f.write(f"    <title>{Trnsl('historical_stats_report_title', lang=app_language)} G{g_value} X{x_value}</title>\n")
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
			f.write("    <div class=\"container\">\n")
			# --- INTESTAZIONE GENERALE DEL REPORT ---
			f.write(f"<h1>{Trnsl('report_header_appname', lang=app_language)} - {Trnsl('historical_stats_report_title', lang=app_language)}</h1>\n")
			f.write(f"<p class=\"report-subtitle\">{Trnsl('stats_based_on_exercises', lang=app_language, count=num_sessions_in_current_report)} (G={g_value}, X={x_value})</p>\n")
			timestamp_now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
			f.write(f"<p class=\"report-generation-time\">{Trnsl('report_generated_on', lang=app_language)}: {timestamp_now}</p>\n")
			# Helper function per i colori delle variazioni (puoi definirla all'inizio di generate_historical_rx_report o globalmente se serve altrove)
			def get_delta_class(delta_value, higher_is_better=True, tolerance=0.01):
				if higher_is_better:
					if delta_value > tolerance: return "good"
					if delta_value < -tolerance: return "bad"
				else: # Lower is better (es. per tassi di errore)
					if delta_value < -tolerance: return "good"
					if delta_value > tolerance: return "bad"
				return "neutral"
			# --- SEZIONE STATISTICHE VELOCITÀ ---
			f.write(f"<h2>{Trnsl('overall_speed_stats', lang=app_language)}</h2>\n")
			f.write("<table>\n")
			f.write(f"  <thead><tr><th>{Trnsl('metric', lang=app_language)}</th><th>{Trnsl('current_value', lang=app_language)}</th>") # Crea trad: 'metric', 'current_value'
			if previous_aggregates:
				f.write(f"<th>{Trnsl('previous_value', lang=app_language)}</th><th>{Trnsl('change', lang=app_language)}</th>") # Crea trad: 'previous_value'
			f.write("</tr></thead>\n")
			f.write("  <tbody>\n")
			# Min WPM
			f.write(f"    <tr><td>{Trnsl('min_wpm', lang=app_language)}</td><td>{current_aggregates['wpm_min_overall']:.2f} WPM</td>")
			if previous_aggregates:
				prev_val = previous_aggregates['wpm_min_overall']
				delta = current_aggregates['wpm_min_overall'] - prev_val
				delta_class = get_delta_class(delta, higher_is_better=True) # Più alto è meglio per min WPM (se >0)
				perc_delta_str = f" ({(delta / prev_val * 100):+.2f}%)" if prev_val != 0 else ""
				f.write(f"<td>{prev_val:.2f} WPM</td><td class=\"{delta_class}\">{delta:+.2f} WPM{perc_delta_str}</td>")
			f.write("</tr>\n")
			# Max WPM
			f.write(f"    <tr><td>{Trnsl('max_wpm', lang=app_language)}</td><td>{current_aggregates['wpm_max_overall']:.2f} WPM</td>")
			if previous_aggregates:
				prev_val = previous_aggregates['wpm_max_overall']
				delta = current_aggregates['wpm_max_overall'] - prev_val
				delta_class = get_delta_class(delta, higher_is_better=True)
				perc_delta_str = f" ({(delta / prev_val * 100):+.2f}%)" if prev_val != 0 else ""
				f.write(f"<td>{prev_val:.2f} WPM</td><td class=\"{delta_class}\">{delta:+.2f} WPM{perc_delta_str}</td>")
			f.write("</tr>\n")
			# Avg WPM
			f.write(f"    <tr><td>{Trnsl('avg_wpm_of_session_avgs_label', lang=app_language)}</td><td>{current_aggregates['wpm_avg_of_session_avgs']:.2f} WPM</td>")
			if previous_aggregates:
				prev_val = previous_aggregates['wpm_avg_of_session_avgs']
				delta = current_aggregates['wpm_avg_of_session_avgs'] - prev_val
				delta_class = get_delta_class(delta, higher_is_better=True)
				perc_delta_str = f" ({(delta / prev_val * 100):+.2f}%)" if prev_val != 0 else ""
				f.write(f"<td>{prev_val:.2f} WPM</td><td class=\"{delta_class}\">{delta:+.2f} WPM{perc_delta_str}</td>")
			f.write("</tr>\n")
			f.write("  </tbody>\n</table>\n")
			# --- SEZIONE STATISTICHE ERRORI COMPLESSIVE ---
			f.write(f"<h2>{Trnsl('overall_error_stats', lang=app_language)}</h2>\n")
			f.write("<table>\n")
			f.write(f"  <thead><tr><th>{Trnsl('metric', lang=app_language)}</th><th>{Trnsl('current_value', lang=app_language)}</th>")
			if previous_aggregates:
				f.write(f"<th>{Trnsl('previous_value', lang=app_language)}</th><th>{Trnsl('change', lang=app_language)}</th>")
			f.write("</tr></thead>\n")
			f.write("  <tbody>\n")
			# Total Chars Sent
			f.write(f"    <tr><td>{Trnsl('total_chars_sent_in_block', lang=app_language)}</td><td>{current_aggregates['total_chars_sent_overall']}</td>")
			if previous_aggregates:
				prev_val = previous_aggregates['total_chars_sent_overall']
				delta = current_aggregates['total_chars_sent_overall'] - prev_val
				# Per i caratteri inviati, la variazione è solo informativa, non "buona" o "cattiva" di per sé
				perc_delta_str = f" ({(delta / prev_val * 100):+.2f}%)" if prev_val != 0 else ""
				f.write(f"<td>{prev_val}</td><td>{delta:+} {perc_delta_str}</td>")
			f.write("</tr>\n")
			# Total Errors & Overall Error Rate
			total_chars_curr = current_aggregates['total_chars_sent_overall']
			total_errs_curr = current_aggregates['total_errors_chars_overall']
			overall_error_rate_curr = (total_errs_curr / total_chars_curr * 100) if total_chars_curr > 0 else 0.0
			f.write(f"    <tr><td>{Trnsl('overall_error_rate', lang=app_language)}</td><td>{total_errs_curr} / {total_chars_curr} ({overall_error_rate_curr:.2f}%)</td>")
			if previous_aggregates:
				total_chars_prev = previous_aggregates['total_chars_sent_overall']
				total_errs_prev = previous_aggregates['total_errors_chars_overall']
				overall_error_rate_prev = (total_errs_prev / total_chars_prev * 100) if total_chars_prev > 0 else 0.0
				delta_rate = overall_error_rate_curr - overall_error_rate_prev
				delta_class = get_delta_class(delta_rate, higher_is_better=False) # Più basso è meglio per il tasso di errore
				f.write(f"<td>{total_errs_prev} / {total_chars_prev} ({overall_error_rate_prev:.2f}%)</td><td class=\"{delta_class}\">{delta_rate:+.2f} punti %</td>")
			f.write("</tr>\n")
			f.write("  </tbody>\n</table>\n")
			# --- SEZIONE DETTAGLIO ERRORI PER CARATTERE (BLOCCO CORRENTE) ---
			if current_aggregates['aggregated_errors_detail']:
				f.write(f"<h2>{Trnsl('error_details_by_char', lang=app_language)}</h2>\n")
				f.write("<table>\n")
				# Crea trad: 'char_header', 'error_count_header', 'perc_vs_total_chars_header', 'perc_vs_spec_char_header'
				f.write(f"  <thead><tr><th>{Trnsl('char_header', lang=app_language)}</th>" \
				        f"<th>{Trnsl('error_count_header', lang=app_language)}</th>" \
				        f"<th>{Trnsl('perc_vs_total_chars_header', lang=app_language)}</th>" \
				        f"<th>{Trnsl('perc_vs_spec_char_header', lang=app_language)}</th></tr></thead>\n")
				f.write("  <tbody>\n")
				sorted_errors = sorted(current_aggregates['aggregated_errors_detail'].items(), key=lambda item: (-item[1], item[0]))
				for char, count in sorted_errors:
					percentage_vs_total_block_chars = (count / total_chars_curr * 100) if total_chars_curr > 0 else 0.0
					total_sent_of_this_char = current_aggregates.get('aggregated_sent_chars_detail', {}).get(char, 0)
					percentage_vs_this_char_sent = (count / total_sent_of_this_char * 100) if total_sent_of_this_char > 0 else 0.0
					f.write(f"    <tr><td class=\"char-emphasis\">'{char.upper()}'</td><td>{count}</td><td>{percentage_vs_total_block_chars:.2f}%</td>" \
					        f"<td>{percentage_vs_this_char_sent:.2f}% <span class=\"details-label\">({Trnsl('of_specific_char_sent_count', lang=app_language, char_upper=char.upper(), count=total_sent_of_this_char)})</span></td></tr>\n") # Crea trad: 'of_specific_char_sent_count'
				f.write("  </tbody>\n</table>\n")
			# --- SEZIONE VARIAZIONI ERRORI PER CARATTERE (se dati precedenti esistono) ---
			if previous_aggregates and previous_aggregates["num_sessions_in_block"] > 0:
				f.write(f"<h2>{Trnsl('error_details_variations', lang=app_language)}</h2>\n")
				f.write(f"<p class=\"report-subtitle\">{Trnsl('variations_vs_block_of', lang=app_language, count=previous_aggregates['num_sessions_in_block'])}</p>\n") # Crea trad: 'variations_vs_block_of'
				f.write("<table>\n")
				f.write(f"  <thead><tr><th>{Trnsl('char_header', lang=app_language)}</th>" \
				        f"<th>{Trnsl('curr_error_count_header', lang=app_language)}</th><th>{Trnsl('curr_perc_vs_total_header', lang=app_language)}</th><th>{Trnsl('curr_perc_vs_spec_header', lang=app_language)}</th>" \
				        f"<th>{Trnsl('prev_error_count_header', lang=app_language)}</th><th>{Trnsl('prev_perc_vs_total_header', lang=app_language)}</th><th>{Trnsl('prev_perc_vs_spec_header', lang=app_language)}</th>" \
				        f"<th>{Trnsl('delta_rate_total_header', lang=app_language)}</th><th>{Trnsl('delta_rate_spec_header', lang=app_language)}</th></tr></thead>\n")
				f.write("  <tbody>\n")
				all_error_chars_set = set(current_aggregates['aggregated_errors_detail'].keys()) | set(previous_aggregates['aggregated_errors_detail'].keys())
				if not all_error_chars_set:
					f.write(f"    <tr><td colspan=\"9\" style=\"text-align:center;\">{Trnsl('no_errors_in_either_block', lang=app_language)}</td></tr>\n")
				else:
					sorted_chars_for_variation = sorted(
						list(all_error_chars_set),
						key=lambda char_key: (-current_aggregates['aggregated_errors_detail'].get(char_key, 0), char_key)
					)
					for char_err in sorted_chars_for_variation:
						curr_count = current_aggregates['aggregated_errors_detail'].get(char_err, 0)
						prev_count = previous_aggregates['aggregated_errors_detail'].get(char_err, 0)
						total_chars_curr_block = current_aggregates['total_chars_sent_overall'] # alias total_chars
						total_chars_prev_block = previous_aggregates['total_chars_sent_overall']
						curr_rate_vs_total_chars = (curr_count / total_chars_curr_block * 100) if total_chars_curr_block > 0 else 0.0
						curr_total_sent_of_this_char = current_aggregates.get('aggregated_sent_chars_detail', {}).get(char_err, 0)
						curr_rate_vs_specific_char = (curr_count / curr_total_sent_of_this_char * 100) if curr_total_sent_of_this_char > 0 else 0.0
						prev_rate_vs_total_chars = (prev_count / total_chars_prev_block * 100) if total_chars_prev_block > 0 else 0.0
						prev_total_sent_of_this_char = previous_aggregates.get('aggregated_sent_chars_detail', {}).get(char_err, 0)
						prev_rate_vs_specific_char = (prev_count / prev_total_sent_of_this_char * 100) if prev_total_sent_of_this_char > 0 else 0.0
						delta_rate_vs_total_chars = curr_rate_vs_total_chars - prev_rate_vs_total_chars
						delta_rate_vs_specific_char = curr_rate_vs_specific_char - prev_rate_vs_specific_char
						delta_total_class = get_delta_class(delta_rate_vs_total_chars, higher_is_better=False)
						delta_specific_class = get_delta_class(delta_rate_vs_specific_char, higher_is_better=False)

						f.write(f"    <tr><td class=\"char-emphasis\">'{char_err.upper()}'</td>" \
						        f"<td>{curr_count}</td><td>{curr_rate_vs_total_chars:.2f}%</td><td>{curr_rate_vs_specific_char:.2f}% <span class=\"details-label\">({Trnsl('of_n_sent', lang=app_language, count=curr_total_sent_of_this_char)})</span></td>" \
						        f"<td>{prev_count}</td><td>{prev_rate_vs_total_chars:.2f}%</td><td>{prev_rate_vs_specific_char:.2f}% <span class=\"details-label\">({Trnsl('of_n_sent', lang=app_language, count=prev_total_sent_of_this_char)})</span></td>" \
						        f"<td class=\"{delta_total_class}\">{delta_rate_vs_total_chars:+.2f} %</td><td class=\"{delta_specific_class}\">{delta_rate_vs_specific_char:+.2f} %</td></tr>\n") # Crea trad 'of_n_sent'
				f.write("  </tbody>\n</table>\n")

			# --- FINE DOCUMENTO HTML ---
			f.write("    </div>\n") # Chiudi container
			f.write("</body>\n")
			f.write("</html>\n")
			
			print(Trnsl('historical_report_saved_to', lang=app_language, filename=report_filename))
	
	except IOError as e:
		print(Trnsl('error_saving_historical_report', lang=app_language, filename=report_filename, e=str(e)))
	except Exception as e:
		print(Trnsl('unexpected_error_generating_report', lang=app_language, e=str(e)))

	# Genera anche il report grafico
	try:
		base_report_filename, _ = os.path.splitext(report_filename)
		graphic_report_filename = base_report_filename + ".svg"
		# Passiamo i dati necessari alla funzione di creazione del grafico
		crea_report_grafico(
			current_aggregates,
			previous_aggregates, # Può essere None
			g_value,             # Già definito in questa funzione
			x_value,             # Già definito in questa funzione
			num_sessions_in_current_report, # Già definito
			graphic_report_filename,
			app_language
		)
		print(Trnsl('graphical_report_saved_to', lang=app_language, filename=graphic_report_filename)) # Crea traduzione
	except Exception as e_graph:
		print(Trnsl('error_generating_graphical_report', lang=app_language, error=str(e_graph)))

#main
global MNMAIN, MNRX, MNRXKIND 
app_data = load_settings()
app_data['app_info']['launch_count'] = app_data.get('app_info', {}).get('launch_count', 0) + 1
launch_count = app_data['app_info']['launch_count'] 
overall_settings = app_data['overall_settings']
app_language = overall_settings.get('app_language', 'en') # Usa .get per sicurezza
MNMAIN = Trnsl('menu_main', lang=app_language)
MNRX = Trnsl('menu_rx', lang=app_language)
MNRXKIND = Trnsl('menu_rx_kind', lang=app_language)
overall_speed = overall_settings.get('speed', 18)
overall_pitch = overall_settings.get('pitch', 550)
overall_dashes = overall_settings.get('dashes', 30)
overall_spaces = overall_settings.get('spaces', 50)
overall_dots = overall_settings.get('dots', 50)
overall_volume = overall_settings.get('volume', 0.5)
overall_ms = overall_settings.get('ms', 1)
overall_fs = overall_settings.get('fs_index', 5)
overall_wave = overall_settings.get('wave_index', 1)
session_speed = overall_speed # Imposta session_speed iniziale
_clear_screen_ansi()
print(Trnsl('welcome_message', lang=app_language, version=VERSION, count=launch_count)) # Aggiunto count=launch_count
print(f"\tWPM: {overall_speed}, Hz: {overall_pitch}, Volume: {int(overall_volume*100)}\n\tL/S/P: {overall_dashes}/{overall_spaces}/{overall_dots}, Wave: {WAVE_TYPES[overall_wave-1]}, MS:	{overall_ms}, FS: {SAMPLE_RATES[overall_fs]}.")

while True:
	k=menu(d=MNMAIN,show=False,keyslist=True,full_keyslist=False, ntf=Trnsl('not_a_command', lang=app_language))
	_clear_screen_ansi()
	if k=="c": Count()
	elif k=="t": Txing()
	elif k=="r": Rxing()
	elif k=="k": KeyboardCW()
	elif k=="z":
		app_language=LangSelector()
		overall_settings_changed=True
		print(Trnsl("l_set",lang=app_language))
	elif k=="l":
		ltc=pyperclip.paste()
		if ltc:
			ltc=StringCleaning(ltc)
			plo,rwpm=CWzator(msg=ltc, wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
		else: plo,rwpm=CWzator(msg=Trnsl('empty_clipboard', lang=app_language), wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
	elif k=="m": menu(d=Trnsl('menu_main', lang=app_language),show_only=True)
	elif k=="w": CreateDictionary()
	elif k=="q": break
app_data['overall_settings'].update({
    "app_language": app_language,
    "speed": overall_speed,
    "pitch": overall_pitch,
    "dashes": overall_dashes,
    "spaces": overall_spaces,
    "dots": overall_dots,
    "volume": overall_volume,
    "ms": overall_ms,
    "fs_index": overall_fs, # Salva l'indice numerico
    "wave_index": overall_wave # Salva l'indice numerico
})
save_settings(app_data)
print("hpe cuagn - 73 de I4APU - Gabe in Bologna, JN54pl.")
CWzator(msg="bk hpe cuagn - 73 de iz4apu tu e e", wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], sync=False, wv=overall_wave)
_clear_screen_ansi()
Donazione()
sys.exit()