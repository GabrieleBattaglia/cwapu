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
VERS="3.0.1, (2025-04-10"
SETTINGS_FILE = "cwapu_settings.json"
DEFAULT_DATA = {
    "app_info": {
        "launch_count": 0 # Inizierà da 1 al primo caricamento
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
	global overall_settings_changed
	if os.path.exists(SETTINGS_FILE):
		try:
			with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
				loaded_data = json.load(f)
				merged_data = {}
				for main_key, default_values in DEFAULT_DATA.items():
					# Prende la sezione dai dati caricati, o un dizionario vuoto se la sezione manca
					loaded_section = loaded_data.get(main_key, {})
					# Inizia con i default per quella sezione
					merged_section = default_values.copy()
					# Aggiorna con i valori effettivamente presenti nel file caricato
					merged_section.update(loaded_section)
					merged_data[main_key] = merged_section
				# Messaggio basato sulla lingua caricata (se presente)
				loaded_lang = merged_data.get('overall_settings', {}).get('app_language', 'en')
				print(Trnsl('o_set_loaded', lang=loaded_lang))
				return merged_data
		except (json.JSONDecodeError, IOError, TypeError) as e: # Aggiunto TypeError
			print(f"Errore nel caricare o leggere {SETTINGS_FILE}: {e}. Uso i valori di default.")
			overall_settings_changed = True # Forza salvataggio se il file era corrotto o illeggibile
			return DEFAULT_DATA.copy() # Restituisci una copia dei default
	else:
		default_lang = DEFAULT_DATA.get('overall_settings', {}).get('app_language', 'en')
		print(Trnsl('o_set_created', lang=default_lang))
		overall_settings_changed = True # Deve essere salvato alla fine
		return DEFAULT_DATA.copy() # Restituisci una copia dei default
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
	global overall_speed, overall_pitch, overall_dashes, overall_spaces, overall_dots, overall_volume, overall_settings_changed,	overall_ms, overall_fs, overall_wave
	print("\n"+Trnsl("h_keyboard",lang=app_language))
	tosave=False
	rwpm=overall_speed
	while True:
		if overall_speed!=rwpm:
			cmd_prompt=f"RWPM: {rwpm:.2f}"
		else:
			cmd_prompt=f"WPM: {overall_speed}"
		if tosave:
			tosave=False
			print(cmd_prompt+" SV>",end="",	flush=True)
		print(cmd_prompt+"> ",end="",	flush=True)
		msg=sys.stdin.readline()
		msg=msg[:-1]+" "
		if msg==" ":
			plo,rwpm=CWzator(msg="73", wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
			break
		elif msg=="? ":
			print("\n"+Trnsl("h_keyboard",lang=app_language))
			msg=""
		elif msg=="?? ":
			print(f"WPM: {overall_speed}, Hz: {overall_pitch}, Volume: {int(overall_volume*100)}\n\tL/S/P: {overall_dashes}/{overall_spaces}/{overall_dots}, Wave: {WAVE_TYPES[overall_wave-1]}, MS:	{overall_ms}, FS: {SAMPLE_RATES[overall_fs]}.")
			msg=""
		elif msg==".sr ":
			overall_fs=ItemChooser(SAMPLE_RATES)
			plo,rwpm=CWzator(msg=f"bk fs is {SAMPLE_RATES[overall_fs]} bk", wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
			overall_settings_changed=True
			msg=""
		elif msg==".rs ":
			overall_dashes, overall_spaces, overall_dots = 30, 50, 50
			plo,rwpm=CWzator(msg="bk reset ok bk", wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
			msg=""
		elif msg.startswith(".sv "):
			msg=msg[4:]
			tosave=True
		elif msg.startswith("."):
			msg = msg.lstrip('.')
			match = re.match(r'([a-zA-Z]+)(\d+)', msg)
			if match:
				cmd = match.group(1)
				value = match.group(2)
				overall_settings_changed=True
			else:
				plo,rwpm=CWzator(msg="?", wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave, sync=True)
			if cmd=="w":
				overall_speed=int(value)
				overall_speed = max(5, min(99, overall_speed))
				plo,rwpm=CWzator(msg=f"bk r w is {overall_speed} bk", wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
				msg=""
			elif cmd=="m":
				overall_ms=int(value)
				overall_ms = max(1, min(30, overall_ms))
				plo,rwpm=CWzator(msg=f"bk r ms is {overall_ms} bk", wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
				msg=""
			elif cmd=="f":
				overall_wave=int(value)
				overall_wave= max(1, min(4, overall_wave))
				plo,rwpm=CWzator(msg=f"bk r wave is {WAVE_TYPES[overall_wave-1]} bk", wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
				msg=""
			elif cmd=="h":
				overall_pitch=int(value)
				overall_pitch = max(130, min(2700, overall_pitch))
				plo,rwpm=CWzator(msg=f"bk r h is {overall_pitch} bk", wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
				msg=""
			elif cmd=="l":
				overall_dashes=int(value)
				overall_dashes = max(1, min(99, overall_dashes))
				plo,rwpm=CWzator(msg=f"bk r l is {overall_dashes} bk", wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
				msg=""
			elif cmd=="s":
				overall_spaces=int(value)
				overall_spaces = max(3, min(99, overall_spaces))
				plo,rwpm=CWzator(msg=f"bk r s is {overall_spaces} bk", wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
				msg=""
			elif cmd=="p":
				overall_dots=int(value)
				overall_dots = max(1, min(99, overall_dots))
				plo,rwpm=CWzator(msg=f"bk r p is {overall_dots} bk", wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
				msg=""
			elif cmd=="v":
				overall_volume=int(value)
				overall_volume = max(0, min(100, overall_volume))
				overall_volume/=100
				plo,rwpm=CWzator(msg=f"bk r v is {int(overall_volume*100)} bk", wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave)
				msg=""
		if msg: plo,rwpm=CWzator(msg=msg, wpm=overall_speed, pitch=overall_pitch, l=overall_dashes, s=overall_spaces, p=overall_dots, vol=overall_volume, ms=overall_ms, fs=SAMPLE_RATES[overall_fs], wv=overall_wave, file=tosave)
	print("Ciao\n")
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