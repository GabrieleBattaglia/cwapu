# CWAPU - Utility per il CW, di Gabry, IZ4APU
# Data concepimento 21/12/2022.
# GitHub publishing on july 2nd, 2024.

#QI
import sys, random, json, string, pyperclip, re, difflib, os
import datetime as dt
from GBUtils import key, dgt, menu, CWzator
from time import localtime as lt
from translations import translations

def Trnsl(key, lang='en', **kwargs):
	value = translations.get(lang, {}).get(key, '')
	if isinstance(value, dict):
		return value
	return value.format(**kwargs)

overall_settings_changed=False
SAMPLE_RATES = [8000, 11025, 16000, 22050, 32000, 44100, 48000, 88200, 96000, 176400, 192000, 384000]
WAVE_TYPES = ['sine', 'square', 'triangle', 'sawtooth']
#QConstants
VERS="3.1.0, (2025-05-15"
SETTINGS_FILE = "cwapu_settings.json"
HISTORICAL_RX_MAX_SESSIONS_DEFAULT = 100
HISTORICAL_RX_REPORT_INTERVAL = 10 # Ogni quanti esercizi generare il report
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
    }, # Aggiungi una virgola qui per separarlo dalla nuova sezione
    "historical_rx_data": { # <-- "historical_rx_data" è ora una CHIAVE DI PRIMO LIVELLO
        "max_sessions_to_keep": HISTORICAL_RX_MAX_SESSIONS_DEFAULT,
        "report_interval": HISTORICAL_RX_REPORT_INTERVAL, 
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
		print(Trnsl('o_set_saved', lang=app_language)) # Usa la lingua corrente dell'app
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
			print(f"WPM: {overall_speed}, Hz: {overall_pitch}, Volume: {int(overall_volume*100)}\n\tL/S/P: {overall_dashes}/{overall_spaces}/{overall_dots}, Wave: {WAVE_TYPES[overall_wave]}, MS: {overall_ms}, FS: {SAMPLE_RATES[overall_fs]}.")
			print(f"\tMax Exercises History (g): {current_max_sessions_g_val}, Report Interval (x): {current_report_interval_x_val}") # Visualizza i valori qui
			msg_for_cw = "" 
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
		
		# Logica per comandi che iniziano con "." (es. .w20, .g 100, .g100)
		elif msg.startswith("."):
			command_candidate_str = msg[1:].strip() # Rimuove "." e spazi extra
			
			cmd_letter = ""
			value_int = None
			parsed_as_command_with_value = False # True se l'input matcha un formato comando+valore

			# Tentativo 1: Formato ".cmd VALORE" (es. ".g 100")
			parts = command_candidate_str.split(maxsplit=1)
			if len(parts) == 2 and parts[1].isdigit():
				cmd_letter = parts[0].lower()
				value_int = int(parts[1])
				parsed_as_command_with_value = True
			
			# Tentativo 2: Formato ".cmdVALORE" (es. ".g100"), solo se il Tentativo 1 non ha prodotto 2 parti
			# o se il primo tentativo non era un comando riconosciuto (parsed_as_command_with_value rimarrebbe False per il cmd specifico)
			# In realtà, se il tentativo 1 non ha prodotto due parti (es. .g100 -> parts = ["g100"]), allora proviamo il re.match.
			if not parsed_as_command_with_value or (len(parts) == 1 and not parts[0].isdigit()): # len(parts)==1 per ".g100"
				# Se parts[0] è solo un numero (es. ".123"), non è un comando compatto cmd+valore
				candidate_for_compact = parts[0] if len(parts) == 1 else command_candidate_str
				match_compact = re.match(r'([a-zA-Z]+)(\d+)', candidate_for_compact)
				if match_compact:
					# Se l'input originale era solo ".cmdVAL" (es. ".g100", command_candidate_str=="g100")
					# E non ".cmdVAL altro testo"
					if candidate_for_compact == match_compact.group(0): # Assicura che l'intero candidato sia stato consumato dal match
						cmd_letter = match_compact.group(1).lower()
						value_int = int(match_compact.group(2))
						parsed_as_command_with_value = True # Ora sappiamo che è un comando con valore

			command_processed_internally = False # Flag per indicare se il comando è stato gestito dalla logica qui sotto
			feedback_cw = ""

			if parsed_as_command_with_value and cmd_letter and value_int is not None:
				# Blocco unico per gestire TUTTI i comandi che hanno una lettera e un valore intero
				if cmd_letter == "g":
					min_val_g, max_val_g = 20, 5000 # Limiti per .g
					actual_val_g = app_data.get('historical_rx_data', {}).get('max_sessions_to_keep', HISTORICAL_RX_MAX_SESSIONS_DEFAULT)
					new_val_g = max(min_val_g, min(max_val_g, value_int))
					if actual_val_g != new_val_g:
						app_data['historical_rx_data']['max_sessions_to_keep'] = new_val_g
						sessions_log = app_data['historical_rx_data'].get('sessions_log', [])
						if len(sessions_log) > new_val_g: 
							app_data['historical_rx_data']['sessions_log'] = sessions_log[-new_val_g:]
						overall_settings_changed = True
					feedback_cw = f"bk max exercises {new_val_g} bk"
					command_processed_internally = True
				
				elif cmd_letter == "x":
					min_val_x, max_val_x = 3, 30 # Limiti per .x
					actual_val_x = app_data.get('historical_rx_data', {}).get('report_interval', HISTORICAL_RX_REPORT_INTERVAL)
					new_val_x = max(min_val_x, min(max_val_x, value_int))
					if actual_val_x != new_val_x:
						app_data['historical_rx_data']['report_interval'] = new_val_x
						overall_settings_changed = True
					feedback_cw = f"bk report interval {new_val_x} bk"
					command_processed_internally = True

				# Comandi CW esistenti
				elif cmd_letter=="w":
					if overall_speed != value_int: # Controlla prima di limitare per il feedback corretto
						new_speed = max(5, min(99, value_int))
						if overall_speed != new_speed:
							overall_speed = new_speed
							overall_settings_changed=True
					feedback_cw = f"bk r w is {overall_speed} bk"
					command_processed_internally = True
				elif cmd_letter=="m":
					if overall_ms != value_int:
						new_ms = max(1, min(30, value_int))
						if overall_ms != new_ms:
							overall_ms = new_ms
							overall_settings_changed=True
					feedback_cw = f"bk r ms is {overall_ms} bk"
					command_processed_internally = True
				elif cmd_letter=="f": 
					new_wave_idx_user = max(1, min(len(WAVE_TYPES), value_int)) # Utente input 1-4
					new_wave_idx_0based = new_wave_idx_user - 1 # Converti in indice 0-based
					if overall_wave != new_wave_idx_0based: 
						overall_wave = new_wave_idx_0based
						overall_settings_changed=True
					feedback_cw = f"bk r wave is {WAVE_TYPES[overall_wave]} bk"
					command_processed_internally = True
				elif cmd_letter=="h":
					if overall_pitch != value_int:
						new_pitch = max(130, min(2700, value_int))
						if overall_pitch != new_pitch:
							overall_pitch = new_pitch
							overall_settings_changed=True
					feedback_cw = f"bk r h is {overall_pitch} bk"
					command_processed_internally = True
				elif cmd_letter=="l":
					if overall_dashes != value_int:
						new_dashes = max(1, min(99, value_int))
						if overall_dashes != new_dashes:
							overall_dashes = new_dashes
							overall_settings_changed=True
					feedback_cw = f"bk r l is {overall_dashes} bk"
					command_processed_internally = True
				elif cmd_letter=="s":
					if overall_spaces != value_int:
						new_spaces = max(3, min(99, value_int))
						if overall_spaces != new_spaces:
							overall_spaces = new_spaces
							overall_settings_changed=True
					feedback_cw = f"bk r s is {overall_spaces} bk"
					command_processed_internally = True
				elif cmd_letter=="p":
					if overall_dots != value_int:
						new_dots = max(1, min(99, value_int))
						if overall_dots != new_dots:
							overall_dots = new_dots
							overall_settings_changed=True
					feedback_cw = f"bk r p is {overall_dots} bk"
					command_processed_internally = True
				elif cmd_letter=="v":
					new_volume_percent = max(0, min(100, value_int))
					if abs(overall_volume * 100 - new_volume_percent) > 0.01 : 
						overall_volume = new_volume_percent / 100.0
						overall_settings_changed=True
					feedback_cw = f"bk r v is {new_volume_percent} bk"
					command_processed_internally = True
				
				# Se un comando è stato processato e c'è un messaggio di feedback CW
				if command_processed_internally and feedback_cw:
					plo,rwpm_temp=CWzator(msg=feedback_cw, wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
					if rwpm_temp is not None: rwpm = rwpm_temp
			
			# Se il comando è stato processato internamente (cambio di settaggio), non inviare l'input originale a CW.
			if command_processed_internally:
				msg_for_cw = "" 
			# Altrimenti, se l'input iniziava con "." ma non era un comando riconosciuto (es. ".testo"),
			# msg_for_cw manterrà l'input originale e verrà inviato a CWzator sotto.
		
		# Invio finale a CWzator se msg_for_cw non è stato svuotato
		if msg_for_cw.strip(): 
			plo,rwpm_temp=CWzator(msg=msg_for_cw, wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave, file=tosave)
			if rwpm_temp is not None: 
				rwpm = rwpm_temp
			elif msg_for_cw.strip() : # Se c'era testo ma CWzator ha fallito (es. carattere non valido in msg_for_cw)
				rwpm = overall_speed # Resetta rwpm per evitare None nel prompt
			if tosave: tosave = False 
	
	# Uscita dal loop while
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
	cs=set(); prompt=""
	print(Trnsl('custom_set_prompt', lang=app_language))
	while True:
		prompt=''.join(sorted(cs))
		scelta = key(prompt="\n"+prompt)
		if scelta=="\r" and len(cs)>=2:
			scelta=""
			break
		elif scelta not in cs and scelta!="\r":
			cs.add(scelta)
			plo,rwpm=CWzator(msg=scelta, wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
		else: plo,rwpm=CWzator(msg="?", wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
	return "".join(cs)
def GeneratingGroup(kind, length, wpm):
	if kind == "1":
		return ''.join(random.choice(string.ascii_letters) for _ in range(length))
	elif kind == "2":
		return ''.join(random.choice(string.digits) for _ in range(length))
	elif kind == "3":
		return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))
	elif kind == "4":
		return ''.join(random.choice(customized_set) for _ in range(length))
	elif kind == "5":
		return random.choice(words)
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
	global app_data, overall_settings_changed, overall_speed, words
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
	calls = 1             # Contatore progressivo per la sessione corrente (mostrato nel prompt)
	callsget = []         # Lista dei qrz/gruppi indovinati CORRETTAMENTE in questa sessione
	callswrong = []       # Lista dei qrz/gruppi ORIGINALI che sono stati sbagliati in questa sessione
	callsrepeated = 0     # Contatore di quanti item corretti sono stati indovinati dopo una ripetizione
	minwpm = 100          # WPM minimo raggiunto in questa sessione (inizializzato alto)
	maxwpm = 0            # WPM massimo raggiunto in questa sessione (inizializzato basso)
	repeatedflag = False  # Flag per indicare se l'ultimo item è stato ripetuto
	# Carica le impostazioni per la cronologia all'inizio della sessione Rxing
	historical_rx_settings = app_data.get('historical_rx_data', {})
	max_sessions_to_keep = historical_rx_settings.get('max_sessions_to_keep', HISTORICAL_RX_MAX_SESSIONS_DEFAULT)
	report_interval = historical_rx_settings.get('report_interval', HISTORICAL_RX_REPORT_INTERVAL)
	overall_speed=dgt(prompt=Trnsl('set_wpm', lang=app_language, wpm=overall_speed),kind="i",imin=10,imax=85,default=overall_speed)
	rwpm=overall_speed
	print(Trnsl('select_exercise', lang=app_language))
	call_or_groups=menu(d=MNRX,show=True,keyslist=True,ntf=Trnsl('please_just_1_or_2', lang=app_language))
	if call_or_groups == "2":
		kind=menu(d=MNRXKIND,show=True,keyslist=True,ntf=Trnsl('choose_a_number', lang=app_language))
		kindstring="Group"
		if kind=="4":
			customized_set=CustomSet(overall_speed)
			length=dgt(prompt=Trnsl('give_length', lang=app_language), kind="i", imin=1, imax=7)
		elif kind=="5":
			words=FilterWord(words)
			length=0
			kindstring="words"
		else:
			length=dgt(prompt=Trnsl('give_length', lang=app_language),kind="i",imin=1,imax=7)
	else: kindstring="Call-like"
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
		if call_or_groups == "1":
			c=random.choices(list(MDL.keys()), weights=MDL.values(), k=1)
			qrz=Mkdqrz(c)
		else:
			qrz=GeneratingGroup(kind=kind, length=length, wpm=overall_speed)
		pitch=random.randint(250, 1050)
		prompt = f"S{sessions}-#{calls} - WPM{rwpm:.0f}/{(average_rwpm / len(callsget) if len(callsget) else rwpm):.2f} - +{len(callsget)}/-{len(callswrong)} - > "
		plo,rwpm=CWzator(msg=qrz, wpm=overall_speed, pitch=pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume,	ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
		guess=dgt(prompt=prompt, kind="s", smin=0, smax=64)
		if guess==".":
			break
		needs_processing = True
		if guess == "" or guess.endswith("?"):
			repeatedflag=True
			partial_input = ""
			prompt_indicator = "%" 
			if guess.endswith("?"):
				partial_input = guess[:-1]
				prompt_indicator = f"% {partial_input}"
			prompt = f"S{sessions}-#{calls} - WPM{rwpm:.0f}/{(average_rwpm / len(callsget) if len(callsget) else rwpm):.2f} - +{len(callsget)}/-{len(callswrong)} - {prompt_indicator}"
			plo,rwpm=CWzator(msg=qrz, wpm=overall_speed, pitch=pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume,	ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
			new_guess = dgt(prompt=prompt, kind="s", smin=0, smax=64) 
			if new_guess == ".":
				needs_processing = False
				break
			else:
				guess = partial_input + new_guess
		if needs_processing:
			original_qrz = qrz.lower()
			callssend.append(original_qrz)
			guess = guess.lower()
			if original_qrz == guess:
				callsget.append(original_qrz)
				average_rwpm+=rwpm
				if repeatedflag: callsrepeated+=1
				if not fix_speed and overall_speed<100: overall_speed+=1
			else:
				callswrong.append(original_qrz)
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
				percentage = round(count / total_mistakes_calculated * 100, 2)
				print(f"{char.upper()}: {count} = {percentage}%") # Stampa diretta
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
		session_data_for_history = {
			"timestamp_iso": starttime.isoformat(), # 'starttime' è definito all'inizio dell'esercizio Rxing
			"duration_seconds": exerctime.total_seconds(),
			"wpm_min": minwpm,
			"wpm_max": maxwpm,
			"wpm_avg": avg_wpm_calc,
			"items_sent_session": len(callssend),
			"items_correct_session": len(callsget),
			"chars_sent_session": send_char, 
			"errors_detail_session": char_error_counts, 
			"total_errors_chars_session": total_mistakes_calculated 
		}
		historical_rx_log = app_data.get('historical_rx_data', {}).get('sessions_log', [])
		historical_rx_log.append(session_data_for_history)
		while len(historical_rx_log) > max_sessions_to_keep:
			historical_rx_log.pop(0)
		if 'historical_rx_data' not in app_data: 
			app_data['historical_rx_data'] = DEFAULT_DATA['historical_rx_data'].copy()
		app_data['historical_rx_data']['sessions_log'] = historical_rx_log
		overall_settings_changed = True
		if sessions > 0 and report_interval > 0 and (sessions % report_interval == 0):
			print(Trnsl('generating_historical_report', lang=app_language)) 
			generate_historical_rx_report()
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
			for char, count in sorted_errors: # Usa la stessa lista ordinata
				percentage = round(count / total_mistakes_calculated * 100, 2)
				f.write(f"\n{char.upper()}: {count} = {percentage}%")
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
		if report_interval > 0: # Assicurati che l'intervallo sia valido
			completed_in_cycle = sessions % report_interval
			if completed_in_cycle == 0:
				exercises_pending = report_interval # Quindi ne mancano 'report_interval' per il PROSSIMO
			else:
				exercises_pending = report_interval - completed_in_cycle
		print(Trnsl('exercises_to_next_report', lang=app_language, count=exercises_pending))
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
	
	# WPM min e max complessivi
	# Filtra i valori non significativi (es. 0 se non impostato, o 100 per minwpm iniziale)
	valid_min_wpms = [s.get("wpm_min", 0) for s in session_list if s.get("wpm_min", 0) > 0 and s.get("wpm_min", 0) != 100]
	valid_max_wpms = [s.get("wpm_max", 0) for s in session_list if s.get("wpm_max", 0) > 0]
	wpm_min_overall = min(valid_min_wpms) if valid_min_wpms else 0
	wpm_max_overall = max(valid_max_wpms) if valid_max_wpms else 0

	# WPM medio basato su CPM (caratteri totali / tempo totale in minuti)
	total_duration_minutes = total_duration_seconds / 60.0
	wpm_avg_overall_cpm_based = 0.0
	if total_duration_minutes > 0:
		cpm_avg_overall = total_chars_sent_overall / total_duration_minutes
		wpm_avg_overall_cpm_based = cpm_avg_overall / 5.0 # Assumendo 5 caratteri per parola (standard PARIS)

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
		"wpm_avg_overall_cpm_based": wpm_avg_overall_cpm_based,
		"total_items_sent": total_items_sent,
		"total_items_correct": total_items_correct,
		"total_chars_sent_overall": total_chars_sent_overall,
		"aggregated_errors_detail": aggregated_errors_detail,
		"total_errors_chars_overall": total_errors_chars_overall
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

	# Nome del file del report
	report_filename = f"cwapu_super_global_stats_last_{num_sessions_in_current_report}.txt"
	# Crea traduzioni per le etichette nel file di report
	# Es: 'report_generated_on', 'stats_based_on_exercises', 'overall_speed_stats', 'min_wpm', 'max_wpm', 'avg_wpm', ...
	
	try:
		with open(report_filename, "w", encoding="utf-8") as f:
			timestamp_now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
			f.write(f"{Trnsl('report_header_appname', lang=app_language)} - {Trnsl('historical_stats_report_title', lang=app_language)}\n")
			f.write(f"{Trnsl('report_generated_on', lang=app_language)}: {timestamp_now}\n")
			f.write(Trnsl('stats_based_on_exercises', lang=app_language, count=num_sessions_in_current_report) + "\n")
			f.write("--------------------------------------------------\n")
			
			# Statistiche di Velocità Correnti
			f.write(f"{Trnsl('overall_speed_stats', lang=app_language)}:\n")
			f.write(f"  {Trnsl('min_wpm', lang=app_language)}: {current_aggregates['wpm_min_overall']:.1f} WPM\n")
			f.write(f"  {Trnsl('max_wpm', lang=app_language)}: {current_aggregates['wpm_max_overall']:.1f} WPM\n")
			f.write(f"  {Trnsl('avg_wpm_cpm_based', lang=app_language)}: {current_aggregates['wpm_avg_overall_cpm_based']:.1f} WPM\n")
			f.write("\n")

			# Statistiche Errori Correnti
			f.write(f"{Trnsl('overall_error_stats', lang=app_language)}:\n")
			total_chars = current_aggregates['total_chars_sent_overall']
			total_errs = current_aggregates['total_errors_chars_overall']
			overall_error_rate = (total_errs / total_chars * 100) if total_chars > 0 else 0.0
			f.write(f"  {Trnsl('total_chars_sent_in_block', lang=app_language)}: {total_chars}\n")
			f.write(f"  {Trnsl('total_errors_in_block', lang=app_language)}: {total_errs} ({overall_error_rate:.2f}%)\n")
			
			if current_aggregates['aggregated_errors_detail']:
				f.write(f"  {Trnsl('error_details_by_char', lang=app_language)}:\n")
				# Ordina per conteggio (decrescente) e poi per carattere
				sorted_errors = sorted(current_aggregates['aggregated_errors_detail'].items(), key=lambda item: (-item[1], item[0]))
				for char, count in sorted_errors:
					percentage = (count / total_chars * 100) if total_chars > 0 else 0.0
					f.write(f"    '{char.upper()}': {count} ({percentage:.2f}% {Trnsl('of_total_chars', lang=app_language)})\n")
			f.write("\n")

			# Variazioni rispetto al blocco precedente
			if previous_aggregates and previous_aggregates["num_sessions_in_block"] > 0:
				f.write("--------------------------------------------------\n")
				f.write(f"{Trnsl('variations_from_previous_block', lang=app_language)} (vs {previous_aggregates['num_sessions_in_block']} {Trnsl('exercises_articles', lang=app_language)})\n")
				f.write("--------------------------------------------------\n")

				# Variazione WPM Medio
				prev_wpm_avg = previous_aggregates['wpm_avg_overall_cpm_based']
				curr_wpm_avg = current_aggregates['wpm_avg_overall_cpm_based']
				delta_wpm = curr_wpm_avg - prev_wpm_avg
				perc_delta_wpm_str = f"({(delta_wpm / prev_wpm_avg * 100):+.2f}%)" if prev_wpm_avg != 0 else ""
				f.write(f"  {Trnsl('avg_wpm_cpm_based', lang=app_language)}: {curr_wpm_avg:.1f} WPM ({Trnsl('vs', lang=app_language)} {prev_wpm_avg:.1f} WPM). {Trnsl('change', lang=app_language)}: {delta_wpm:+.1f} WPM {perc_delta_wpm_str}\n")

				# Variazione Tasso di Errore Generale
				prev_total_chars = previous_aggregates['total_chars_sent_overall']
				prev_total_errs = previous_aggregates['total_errors_chars_overall']
				prev_err_rate = (prev_total_errs / prev_total_chars * 100) if prev_total_chars > 0 else 0.0
				
				curr_err_rate = overall_error_rate # Già calcolato sopra
				delta_err_rate = curr_err_rate - prev_err_rate
				# Nota: per i tassi di errore, una diminuzione è positiva.
				# La percentuale di cambiamento di un tasso di errore può essere meno intuitiva, quindi mostriamo la variazione assoluta del tasso.
				f.write(f"  {Trnsl('overall_error_rate', lang=app_language)}: {curr_err_rate:.2f}% ({Trnsl('vs', lang=app_language)} {prev_err_rate:.2f}%). {Trnsl('change', lang=app_language)}: {delta_err_rate:+.2f}%\n")
				f.write("\n")
				
				# Variazioni per errori specifici (Top N errori o tutti)
				f.write(f"  {Trnsl('error_details_variations', lang=app_language)}:\n")
				all_error_chars = set(current_aggregates['aggregated_errors_detail'].keys()) | set(previous_aggregates['aggregated_errors_detail'].keys())
				if not all_error_chars:
					f.write(f"    {Trnsl('no_errors_in_either_block', lang=app_language)}\n")
				
				sorted_all_error_chars = sorted(list(all_error_chars))
				for char_err in sorted_all_error_chars:
					curr_count = current_aggregates['aggregated_errors_detail'].get(char_err, 0)
					prev_count = previous_aggregates['aggregated_errors_detail'].get(char_err, 0)
					curr_err_char_rate = (curr_count / total_chars * 100) if total_chars > 0 else 0.0
					prev_err_char_rate = (prev_count / prev_total_chars * 100) if prev_total_chars > 0 else 0.0
					delta_char_rate = curr_err_char_rate - prev_err_char_rate
					f.write(f"    '{char_err.upper()}': {curr_err_char_rate:.2f}% ({curr_count}) {Trnsl('vs', lang=app_language)} {prev_err_char_rate:.2f}% ({prev_count}). {Trnsl('rate_change_char', lang=app_language)}: {delta_char_rate:+.2f}%\n")
			print(Trnsl('historical_report_saved_to', lang=app_language, filename=report_filename))
	except IOError as e:
		print(Trnsl('error_saving_historical_report', lang=app_language, filename=report_filename, e=str(e)))
	except Exception as e:
		print(Trnsl('unexpected_error_generating_report', lang=app_language, e=str(e)))

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
print(Trnsl('welcome_message', lang=app_language, version=VERS, count=launch_count)) # Aggiunto count=launch_count
print(f"\tWPM: {overall_speed}, Hz: {overall_pitch}, Volume: {int(overall_volume*100)}\n\tL/S/P: {overall_dashes}/{overall_spaces}/{overall_dots}, Wave: {WAVE_TYPES[overall_wave-1]}, MS:	{overall_ms}, FS: {SAMPLE_RATES[overall_fs]}.")

while True:
	k=menu(d=MNMAIN,show=False,keyslist=True,full_keyslist=False, ntf=Trnsl('not_a_command', lang=app_language))
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
CWzator(msg="bk hpe cuagn - 73 de iz4apu tu e e", wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], sync=False, wv=overall_wave)
sys.exit()