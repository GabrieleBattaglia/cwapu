# CWAPU - Utility per il CW, di Gabry, IZ4APU
# Data concepimento 21/12/2022.
# GitHub publishing on july 2nd, 2024.

import sys, random, pickle, string, pyperclip, re, difflib
import datetime as dt
from GBUtils import key, dgt, menu
from cwzator2 import *
from time import localtime as lt
from time import sleep as wait
from translations import translations

def Trnsl(key, lang='en', **kwargs):
	value = translations.get(lang, {}).get(key, '')
	if isinstance(value, dict):
		return value
	return value.format(**kwargs)

app_language = ''
overall_speed=0
overall_hertz=0
overall_dashes=0
overall_spaces=0
overall_dots=0
overall_volume=0
overall_settings_changed=False
try:
	f=open("CWapu_Overall.pkl", "rb")
	app_language, overall_speed, overall_hertz, overall_dashes, overall_spaces, overall_dots, overall_volume = pickle.load(f)
	f.close()
	print(Trnsl('o_set_loaded',lang=app_language))
except IOError:
	app_language, overall_speed, overall_hertz, overall_dashes, overall_spaces, overall_dots, overall_volume = 'en', 18, 550, 30, 50, 50, 0.7
	overall_settings_changed=True
	print(Trnsl('o_set_created',lang=app_language))

#QConstants
VERS="2.5.5, (2024-11-16)"
MNLANG={
	"en":"English",
	"it":"Italiano"}
MNMAIN = Trnsl('menu_main', lang=app_language)
MNRX = Trnsl('menu_rx', lang=app_language)
MNRXKIND = Trnsl('menu_rx_kind', lang=app_language)
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
wpm=22
customized_set=''
words=[]

#qf
def KeyboardCW():
	'''Settings for CW and tx with keyboard'''
	global overall_speed, overall_hertz, overall_dashes, overall_spaces, overall_dots, overall_volume, overall_settings_changed
	print("\n"+Trnsl("h_keyboard",lang=app_language))
	while True:
		msg=sys.stdin.readline()
		msg=msg[:-1]+" "
		if msg==" ":
			CWzator2(msg="73", wpm=overall_speed, pitch=overall_hertz, dashes=overall_dashes, spaces=overall_spaces, dots=overall_dots, vol=overall_volume)
			break
		elif msg=="? ":
			print("\n"+Trnsl("h_keyboard",lang=app_language))
			msg=""
		elif msg=="?? ":
			print(f"WPM: {overall_speed}, Hz: {overall_hertz}, Volume: {int(overall_volume*100)}\n\tL/S/P: {overall_dashes}/{overall_spaces}/{overall_dots}.")
			msg=""
		elif msg==".rs ":
			overall_dashes, overall_spaces, overall_dots = 30, 50, 50
			CWzator2(msg="bk reset ok bk", wpm=overall_speed, pitch=overall_hertz, dashes=overall_dashes, spaces=overall_spaces, dots=overall_dots, vol=overall_volume)
			msg=""
		elif msg.startswith("."):
			msg = msg.lstrip('.')
			match = re.match(r'([a-zA-Z]+)(\d+)', msg)
			if match:
				cmd = match.group(1)
				value = match.group(2)
				overall_settings_changed=True
			else:
				CWzator2(msg="?", wpm=overall_speed, pitch=overall_hertz, dashes=overall_dashes, spaces=overall_spaces, dots=overall_dots, vol=overall_volume)
			if cmd=="w":
				overall_speed=int(value)
				overall_speed = max(5, min(99, overall_speed))
				CWzator2(msg=f"bk r w is {overall_speed} bk", wpm=overall_speed, pitch=overall_hertz, dashes=overall_dashes, spaces=overall_spaces, dots=overall_dots, vol=overall_volume)
				msg=""
			elif cmd=="h":
				overall_hertz=int(value)
				overall_hertz = max(130, min(2700, overall_hertz))
				CWzator2(msg=f"bk r h is {overall_hertz} bk", wpm=overall_speed, pitch=overall_hertz, dashes=overall_dashes, spaces=overall_spaces, dots=overall_dots, vol=overall_volume)
				msg=""
			elif cmd=="l":
				overall_dashes=int(value)
				overall_dashes = max(1, min(99, overall_dashes))
				CWzator2(msg=f"bk r l is {overall_dashes} bk", wpm=overall_speed, pitch=overall_hertz, dashes=overall_dashes, spaces=overall_spaces, dots=overall_dots, vol=overall_volume)
				msg=""
			elif cmd=="s":
				overall_spaces=int(value)
				overall_spaces = max(3, min(99, overall_spaces))
				CWzator2(msg=f"bk r s is {overall_spaces} bk", wpm=overall_speed, pitch=overall_hertz, dashes=overall_dashes, spaces=overall_spaces, dots=overall_dots, vol=overall_volume)
				msg=""
			elif cmd=="p":
				overall_dots=int(value)
				overall_dots = max(1, min(99, overall_dots))
				CWzator2(msg=f"bk r p is {overall_dots} bk", wpm=overall_speed, pitch=overall_hertz, dashes=overall_dashes, spaces=overall_spaces, dots=overall_dots, vol=overall_volume)
				msg=""
			elif cmd=="v":
				overall_volume=int(value)
				overall_volume = max(0, min(100, overall_volume))
				overall_volume/=100
				CWzator2(msg=f"bk v is {int(overall_volume*100)} bk", wpm=overall_speed, pitch=overall_hertz, dashes=overall_dashes, spaces=overall_spaces, dots=overall_dots, vol=overall_volume)
				msg=""
		if msg: CWzator2(msg=msg, wpm=overall_speed, pitch=overall_hertz, dashes=overall_dashes, spaces=overall_spaces, dots=overall_dots, vol=overall_volume)
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
def CustomSet(wpm):
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
			CWzator2(msg=scelta, wpm=wpm, pitch=550)
		else: CWzator2(msg="?", wpm=wpm, pitch=550)
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
	from winsound import Beep as B
	print(Trnsl('counting_prompt', lang=app_language))
	try:
		f=open("CWapu_Index.pkl", "rb")
		esnum=pickle.load(f)
		f.close()
	except IOError:
		esnum=1
	cont = 0
	corr = 0
	scelta = ""
	B(350,200)
	print(Trnsl('exercise_number', lang=app_language, esnum=esnum))
	while True:
		if cont % 100 == 0: B(1600, 200)
		elif cont % 50 == 0: B(1150, 80)
		elif cont % 25 == 0: B(900, 60)
		elif cont % 10 == 0: B(600, 40)
		if corr > 0:
			prompt = f"T{cont}, {corr*100/cont:.2f}%, C{corr}/N{cont-corr}> "
		else:
			prompt = "T1, 0%> "
		scelta=key("\n"+prompt)
		if scelta == " ":
			corr += 1
			B(1380,15)
		elif ord(scelta) == 27: break
		else:
			B(310,25)
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
		with open("CWapu_Diary.txt", "a") as f:
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
	f=open("CWapu_Index.pkl", "wb")
	esnum+=1
	pickle.dump(esnum, f)
	f.close()
	print(Trnsl('bye_message', lang=app_language))
	return
def GroupMistakesByFrequency(dict_mistakes):
	total_mistakes = sum(count for count, _ in dict_mistakes.values())
	grouped_errors = {}
	for letter, (count, _) in dict_mistakes.items():
		percentage = round(count / total_mistakes * 100, 2)
		key = (count, percentage)
		if key not in grouped_errors:
			grouped_errors[key] = []
		grouped_errors[key].append(letter)
	formatted_output = []
	for (count, percentage), letters in sorted(grouped_errors.items(), reverse=True):
		letter_group = " ".join(sorted(letters))
		formatted_output.append(f"{letter_group}: {count} = {percentage}%")
	return formatted_output
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
def MistakesCollectorInLists(rights, received):
	errors = {}
	for right, rxed in zip(rights, received):
		s = difflib.SequenceMatcher(None, right, rxed)
		for tag, i1, i2, j1, j2 in s.get_opcodes():
			if tag == 'replace' or tag == 'delete':
				for char in right[i1:i2]:
					errors[char] = errors.get(char, 0) + 1
			elif tag == 'insert':
				for char in rxed[j1:j2]:
					errors[char] = errors.get(char, 0) + 1
	ordered_mistakes = dict(sorted(errors.items(), key=lambda item: item[1], reverse=True))
	total_mistakes = sum(ordered_mistakes.values())
	perc_mistakes = {k: (v, v / total_mistakes * 100) for k, v in ordered_mistakes.items()}
	return perc_mistakes
def AlwaysRight(yep, nope):
	letters = set("".join(yep))
	letters_misspelled = set(nope.keys())
	return letters - letters_misspelled
def Rxing():
	# receiving exercise
	global words
	print(Trnsl('time_to_receive', lang=app_language))
	try:
		with open('words.txt', 'r', encoding='utf-8') as file:
			words = file.readlines()
			words = [line.strip() for line in words]
			print(Trnsl('dictionary_loaded', lang=app_language, word_count=len(words)))
	except FileNotFoundError:
		print(Trnsl('file_not_found', lang=app_language))
		del MNRXKIND["5"]
	try:
		f=open("CWapu_Rxing.pkl", "rb")
		wpm, totalcalls, sessions, totalget, totalwrong, totaltime = pickle.load(f)
		f.close()
		print(Trnsl('got_data', lang=app_language, wpm=wpm, sessions=sessions-1, totalcalls=totalcalls, totalget=totalget, totalwrong=totalwrong, totaltime=str(totaltime)[:-5]))
	except IOError:
		print(Trnsl('first_class', lang=app_language))
		wpm, totalcalls, sessions, totalget, totalwrong, totaltime = 22, 0, 1, 0, 0, dt.datetime.now()-dt.datetime.now()
	calls, callsget, callswrong, callsrepeated, minwpm, maxwpm, repeatedflag = 1, [], [], 0, 100, 14, False
	global customized_set
	callssend=[]; average_wpm=0.0
	dz_mistakes={}
	wpm=dgt(prompt=Trnsl('set_wpm', lang=app_language, wpm=wpm),kind="i",imin=10,imax=85,default=wpm)
	print(Trnsl('select_exercise', lang=app_language))
	call_or_groups=menu(d=MNRX,show=True,keyslist=True,ntf=Trnsl('please_just_1_or_2', lang=app_language))
	if call_or_groups == "2":
		kind=menu(d=MNRXKIND,show=True,keyslist=True,ntf=Trnsl('choose_a_number', lang=app_language))
		kindstring="Group"
		if kind=="4":
			customized_set=CustomSet(wpm)
			length=dgt(prompt=Trnsl('give_length', lang=app_language), kind="i", imin=1, imax=7)
		elif kind=="5":
			words=FilterWord(words)
			length=0
			kindstring="words"
		else:
			length=dgt(prompt=Trnsl('give_length', lang=app_language),kind="i",imin=1,imax=7)
	else: kindstring="Call-like"
	print(Trnsl('careful_type', lang=app_language, kindstring=kindstring))
	attesa=key()
	print(Trnsl('begin_session', lang=app_language, sessions=sessions))
	starttime=dt.datetime.now()
	while True:
		if call_or_groups == "1":
			c=random.choices(list(MDL.keys()), weights=MDL.values(), k=1)
			qrz=Mkdqrz(c)
		else:
			qrz=GeneratingGroup(kind=kind, length=length, wpm=wpm)
		pitch=random.randint(300, 1050)
		prompt=f"S{sessions}-#{calls} - WPM{wpm} - +{len(callsget)}/-{len(callswrong)} - > "
		CWzator2(msg=qrz, wpm=wpm, pitch=pitch)
		guess=dgt(prompt=prompt, kind="s", smin=0, smax=64)
		if guess==".":
			calls-=1
			break
		elif guess == "" or "?" in guess:
			repeatedflag=True
			prompt=f"S{sessions}-#{calls} - WPM{wpm} - +{len(callsget)}/-{len(callswrong)} - % {guess[:-1]}"
			CWzator2(msg=qrz, wpm=wpm, pitch=pitch)
			guess=guess[:-1] + dgt(prompt=prompt, kind="s", smin=0, smax=64)
		callssend.append(qrz.lower())
		guess=guess.lower(); qrz=qrz.lower()
		if qrz == guess:
			callsget.append(qrz)
			average_wpm+=wpm
			if repeatedflag: callsrepeated+=1
			if wpm<100: wpm+=1
		else:
			callswrong.append(qrz.lower())
			diff=MistakesCollectorInStrings(qrz,guess)
			diff_ratio=(1 - difflib.SequenceMatcher(None,qrz,guess).ratio()) * 100
			print(f"TX: {qrz} RX: {guess} <>: {diff} RT: {int(diff_ratio):d}")
			dz_mistakes[len(callssend)]=(qrz,guess)
			if wpm>15: wpm-=1
		calls+=1
		if wpm>maxwpm: maxwpm=wpm
		if wpm<minwpm: minwpm=wpm
		repeatedflag=False
	exerctime=dt.datetime.now()-starttime
	print(Trnsl('over_check', lang=app_language))
	if calls>9 and len(callsget)>0:
		send_char=0
		for j in callssend:
			send_char+=len(j)
		print(Trnsl('session_summary', lang=app_language, sessions=sessions, calls=calls, kindstring=kindstring, callsget_len=len(callsget), percentage=len(callsget)*100/calls))
		print(Trnsl('first_shot', lang=app_language, first_shot=len(callsget)-callsrepeated, first_shot_percentage=(len(callsget)-callsrepeated)*100/len(callsget)))
		print(Trnsl('with_repetition', lang=app_language, repetitions=callsrepeated, kindstring=kindstring, repetitions_percentage=callsrepeated*100/len(callsget)))
		print(Trnsl('speed_summary', lang=app_language, minwpm=minwpm, maxwpm=maxwpm, range_wpm=maxwpm-minwpm, average_wpm=average_wpm/len(callsget)))
		dict_mistakes = MistakesCollectorInLists(callssend, callswrong)
		results=GroupMistakesByFrequency(dict_mistakes)
		print(Trnsl('character_mistakes', lang=app_language))
		for item in results:
			print(item.upper())
		global_mistakes = sum([v[0] for v in dict_mistakes.values()])
		print(Trnsl('total_mistakes', lang=app_language, global_mistakes=global_mistakes, send_char=send_char, mistake_percentage=global_mistakes*100/send_char))
		good_letters = AlwaysRight(callssend, dict_mistakes)
		print(Trnsl('never_misspelled', lang=app_language, good_letters=" ".join(sorted(good_letters)).upper()))
		f=open("CWapu_Diary.txt", "a")
		print(Trnsl('report_saved', lang=app_language))
		date = f"{lt()[0]}/{lt()[1]}/{lt()[2]}"
		time = f"{lt()[3]}, {lt()[4]}"
		f.write(Trnsl('receiving_exercise_report', lang=app_language, sessions=sessions, date=date, time=time))
		f.write(Trnsl('session_summary', lang=app_language, sessions=sessions, calls=calls, kindstring=kindstring, callsget_len=len(callsget), percentage=len(callsget)*100/calls) + "\n")
		f.write(Trnsl('first_shot', lang=app_language, first_shot=len(callsget)-callsrepeated, first_shot_percentage=(len(callsget)-callsrepeated)*100/len(callsget)) + "\n")
		f.write(Trnsl('with_repetition', lang=app_language, repetitions=callsrepeated, kindstring=kindstring, repetitions_percentage=callsrepeated*100/len(callsget)) + "\n")
		f.write(Trnsl('speed_summary', lang=app_language, minwpm=minwpm, maxwpm=maxwpm, range_wpm=maxwpm-minwpm, average_wpm=average_wpm/len(callsget)) + "\n")
		f.write(Trnsl('character_mistakes', lang=app_language))
		for item in results:
			f.write("\n"+item.upper())
		f.write(Trnsl('list_of_wrong_words', lang=app_language))
		for k, v in dz_mistakes.items():
			rslt=MistakesCollectorInStrings(v[0],v[1])
			f.write(Trnsl('wrong_word_entry', lang=app_language, k=k, tx=v[0], rx=v[1], dif=rslt))
		f.write(Trnsl('total_mistakes', lang=app_language, global_mistakes=global_mistakes, send_char=send_char, mistake_percentage=global_mistakes*100/send_char))
		f.write(Trnsl('never_misspelled', lang=app_language, good_letters=" ".join(sorted(good_letters)).upper()))
		nota=dgt(prompt=Trnsl('note_on_exercise', lang=app_language), kind="s", smin=0, smax=512)
		if nota != "":
			f.write(Trnsl('note_with_text', lang=app_language, nota=nota))
		else:
			f.write("\n" + Trnsl('empty_note', lang=app_language) + "\n***\n")
		f.close()
	else: print(Trnsl('received_too_few', lang=app_language, kindstring=kindstring))
	totalcalls+=calls
	totalget+=len(callsget)
	totalwrong+=len(callswrong)
	totaltime+=exerctime
	sessions+=1
	f=open("CWapu_Rxing.pkl", "wb")
	pickle.dump([wpm, totalcalls, sessions, totalget, totalwrong, totaltime], f)
	f.close()
	print(Trnsl('session_saved', lang=app_language, session_number=sessions-1, duration=str(exerctime)[:-5]))
	return

#main
print(Trnsl('welcome_message', lang=app_language, version=VERS))
print(f"\t\tWPM = {overall_speed}, Hertz = {overall_hertz}, Lang = {app_language}\n\t\tCW Ratio L/S/P = {overall_dashes}/{overall_spaces}/{overall_dots}, Vol = {int(overall_volume*100)}")

while True:
	k=menu(d=MNMAIN,show=False,keyslist=True,ntf=Trnsl('not_a_command', lang=app_language))
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
			CWzator2(msg=ltc, wpm=overall_speed, pitch=overall_hertz)
		else: CWzator2(msg=Trnsl('empty_clipboard', lang=app_language), wpm=overall_speed, pitch=overall_hertz)
	elif k=="m": menu(d=Trnsl('menu_main', lang=app_language),show_only=True)
	elif k=="w": CreateDictionary()
	elif k=="q": break
print(Trnsl('exit_message', lang=app_language))
CWzator2(msg="bk hpe cuagn - 73 de iz4apu tu e e", wpm=40, pitch=599)
if overall_settings_changed:
	f=open("CWapu_Overall.pkl", "wb")
	pickle.dump([app_language, overall_speed, overall_hertz, overall_dashes, overall_spaces, overall_dots, overall_volume],f)
	f.close()
	print(Trnsl('o_set_saved',lang=app_language))
wait(8.5)
sys.exit()