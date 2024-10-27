# CWAPU - Utility per il CW, di Gabry, IZ4APU
# Data concepimento 21/12/2022.
# GitHub publishing on july 2nd, 2024.

import sys, random, pickle, string, pyperclip, re, difflib
import datetime as dt
from GBUtils import key, dgt, menu
from cwzator import *
from time import localtime as lt
from time import sleep as wait

#constants
VERS="1.5.13, october 27th, 2024"
MNMAIN={
	"c":"Counting results",
	"h":"Set Hertz",
	"l":"Listen to clipboard",
	"m":"shows Menu",
	"q":"To quit this app",
	"r":"Receiving exercise",
	"s":"Set speed",
	"t":"Transmitting exercise",
	"w":"Words Creator"}
MNRX={
	"1":"Call-like",
	"2":"Groups"}
MNRXKIND={
										"1":"Letters only (A to Z)",
										"2":"Numbers only (0 to 9)",
										"3":"Letters and Numbers (A to Z and 0 to 9)",
										"4":"Custom set (let's decide which symbols you want to work on)",
										"5":"Words (words peeked up from a customizable file)"}
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
overall_speed=35
overall_hertz=550
overall_settings_changed=False
wpm=22
customized_set=''
words=[]

#qf
def StringCleaning(stringa):
	stringa = stringa.strip()
	stringa = stringa.lower()
	cleaned = re.sub(r"[^a-z0-9\sàèéìòù@.,;:!?\'\"()-=]", "", stringa)
	cleaned = re.sub(r"\s+", " ", cleaned)
	return cleaned
def CreateDictionary():
	print("Attention! Please read carefully.\n"
							"For the reception exercises, (r) from the main menu, CWAPU uses the file words.txt, "
							"which must be located in the folder from which you launched cwapu.py or cwapu.exe. "
							"If this file does not exist, create one with a text editor and write some words in it, "
							"one word per line, then save it.\n"
							"The WordsCreator procedure allows you to scan all the txt files contained in the folders you indicate "
							"and add all the words from those files to words.txt. The words will be added uniquely, "
							"meaning they will all be different from each other.\n"
							"The file produced by this process will be named words_updated.txt. Check it with a text editor and, "
							"if you are satisfied with it, rename it to words.txt, replacing the existing words.txt.\n"
							"You can repeat this operation as many times as you like: words_updated.txt will contain the words "
							"from words.txt plus all those collected from the newly processed .txt files.")
	import Words_Creator
	Words_Creator.Start()
	return
def FilterWord(w):
	print("\nLet's filter the words set to using with the exercise\nPlease type minimum.maximum length of the words you want to be choosen randomly. e.g. 3.6\nwill choose words with length in between 3 and 6 characters only.\nType enter to use the whole dictonary")
	ex=False
	while True:
		while True:
			mnmx=input("Minimum.Maximum: ")
			if mnmx=="":
				ex=True
				break
			elif "." in mnmx:
				x=mnmx.split(".")
				mn,mx=x[0],x[1]
				if mn.isdigit() and mx.isdigit(): break
				else: print("You havn't inserted numbers")
			else: print("Try again")
		if ex: break
		mn=int(mn); mx=int(mx)
		if mn<1: mn=1
		elif mn>10: mn=10
		if mx<3: mx=3
		elif mx>35: mx=35
		print(f"Filtering word which are in {mn}/{mx} range of length.")
		w1=[l for l in w if len(l)>=mn and len(l)<=mx]
		scelta=key(prompt=f"{len(w1)} words, are you ok with it? (y|n)> ").lower()
		if scelta=="y": break
	if ex: return w
	else: return w1
def CustomSet(wpm):
	cs=set(); prompt=""
	print("Type all characters you want to practice on. (minimum of 2) Empty line to proceed")
	while True:
		prompt=''.join(sorted(cs))
		scelta = key(prompt="\n"+prompt)
		if scelta=="\r" and len(cs)>=2:
			scelta=""
			break
		elif scelta not in cs and scelta!="\r":
			cs.add(scelta)
			CWzator(msg=scelta, wpm=wpm, pitch=550)
		else: CWzator(msg="?", wpm=wpm, pitch=550)
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
	print("Transmitting exercise.\nHere you're going to have random calls-like and numbers,\n\ttry to play them on your favourite CW key.\nAny key to go on, ESCAPE to close the App.")
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
	print("Bye-Bye & 73. de IZ4APU Gabe, back to main menu.")
	return
def Count():
	from winsound import Beep as B
	print("Counting, YES or NO?.\nSpacebar means: group received;\nAny other key means: group lost;\nPress ESCAPE to go back to main menu.")
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
	print(f"Exercise number {esnum}:")
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
	print(f"Total: {cont}, correct: {corr}, mistakes(%): {pde:.2f}%.")
	if pde<=6:
		print("Passed!")
	else:
		print(f"Failed: {pde-6:.2f}% to the threshold.")
	if cont >= 100:
		with open("CWapu_Diary.txt", "a") as f:
			nota=input("Note on this exercise: ")
			print("Report saved on CW_Diary.txt")
			f.write(f"Counting exercise #{esnum} performed on {str(lt()[0])}/{str(lt()[1])}/{str(lt()[2])} at {str(lt()[3])}, {str(lt()[4])} minutes:\n")
			f.write(f"Total {cont}, fixed {corr}, mistake(%) {pde:.2f}%.\n")
			if pde<=6:
				f.write("Got it!\n")
			else:
				f.write(f"Failed: {pde-6:.2f}% to the threshold.\n")
			if nota != "":
				f.write(f"Note: {nota}\n***\n")
			else:
				f.write(f"Note: empty\n***\n")
	else:
		print(f"Groups received {cont} up to 100: exercise not saved on disk.")
	f=open("CWapu_Index.pkl", "wb")
	esnum+=1
	pickle.dump(esnum, f)
	f.close()
	print("Bye for now, back to main menu.")
	return
def GroupMistakesByFrequency(dict_mistakes):
	# Calcola il totale degli errori per la percentuale
	total_mistakes = sum(count for count, _ in dict_mistakes.values())
	# Raggruppa le lettere per conteggio e percentuale
	grouped_errors = {}
	for letter, (count, _) in dict_mistakes.items():
		percentage = round(count / total_mistakes * 100, 2)
		key = (count, percentage)
		if key not in grouped_errors:
			grouped_errors[key] = []
		grouped_errors[key].append(letter)
	# Crea l'output formattato
	formatted_output = []
	for (count, percentage), letters in sorted(grouped_errors.items(), reverse=True):
		letter_group = " ".join(sorted(letters))
		formatted_output.append(f"{letter_group}: {count} = {percentage}%")
	return formatted_output
import difflib

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
		# Usa SequenceMatcher per rilevare le differenze con precisione
		s = difflib.SequenceMatcher(None, right, rxed)
		for tag, i1, i2, j1, j2 in s.get_opcodes():
			if tag == 'replace' or tag == 'delete':
				for char in right[i1:i2]:
					errors[char] = errors.get(char, 0) + 1
			elif tag == 'insert':
				for char in rxed[j1:j2]:
					errors[char] = errors.get(char, 0) + 1
	# Ordina e calcola le percentuali come nel modello originale
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
	print("\nTime to receive? Yep, you're to the right place. Let's go!\n\tLoading the status of your progress and check for dictonary database...")
	try:
		with open('words.txt', 'r', encoding='utf-8') as file:
			words = file.readlines()
			words = [line.strip() for line in words]
			print(f"Word's dictionary loaded with {len(words)} words.")
	except FileNotFoundError:
		print("File words.txt not found. Please provide a dictionary file: 1 word per line.")
		del MNRXKIND["5"]
	try:
		f=open("CWapu_Rxing.pkl", "rb")
		wpm, totalcalls, sessions, totalget, totalwrong, totaltime = pickle.load(f)
		f.close()
		print(f"I got your data from disk, so:\nYour actual WPM is {wpm} and you did {sessions-1} sessions.\nI sent to you {totalcalls} total calls-like or groups, and you got {totalget} of them, while {totalwrong} were missed\nYour overall time receiving calls-like is {str(totaltime)[:-5]}.")
	except IOError:
		print("Ups, this is your first class, probably. So I'm creating the record.")
		wpm, totalcalls, sessions, totalget, totalwrong, totaltime = 22, 0, 1, 0, 0, dt.datetime.now()-dt.datetime.now()
	calls, callsget, callswrong, callsrepeated, minwpm, maxwpm, repeatedflag = 0, [], [], 0, 100, 14, False
	global customized_set
	callssend=[]
	dz_mistakes={}
	wpm=dgt(prompt=f"Do you want to set your WPM? Enter to accept {wpm}> ",kind="i",imin=10,imax=85,default=wpm)
	print("Now select which exercise do you want to take:")
	call_or_groups=menu(d=MNRX,show=True,keyslist=True,ntf="Please, just 1 or 2")
	if call_or_groups == "2":
		kind=menu(d=MNRXKIND,show=True,keyslist=True,ntf="Choose a number please")
		kindstring="Group"
		if kind=="4":
			customized_set=CustomSet(wpm)
			length=dgt(prompt="Give me the length of the group in between 1 and 7: ", kind="i", imin=1, imax=7)
		elif kind=="5":
			words=FilterWord(words)
			length=0
			kindstring="words"
		else:
			length=dgt(prompt="Give me the length of the group in between 1 and 7: ",kind="i",imin=1,imax=7)
	else: kindstring="Call-like"
	print(f"Now, careful. Type the {kindstring} you hear.\nGiving an empty line (or adding a ?) will gift you a second listen to the {kindstring}.\n\tTo stop, just type a '.' (fullstop) followed by enter.\nENJOY. \tPress any key when you're ready to start.")
	attesa=key()
	print(f"Let's begin session {sessions}!")
	starttime=dt.datetime.now()
	while True:
		if call_or_groups == "1":
			c=random.choices(list(MDL.keys()), weights=MDL.values(), k=1)
			qrz=Mkdqrz(c)
		else:
			qrz=GeneratingGroup(kind=kind, length=length, wpm=wpm)
		callssend.append(qrz.lower())
		pitch=random.randint(300, 1050)
		prompt=f"S{sessions}-#{calls} - WPM{wpm} - +{len(callsget)}/-{len(callswrong)} - > "
		CWzator(msg=qrz, wpm=wpm, pitch=pitch)
		guess=dgt(prompt=prompt, kind="s", smin=0, smax=64)
		if guess==".": break
		elif guess == "" or "?" in guess:
			repeatedflag=True
			prompt=f"S{sessions}-#{calls} - WPM{wpm} - +{len(callsget)}/-{len(callswrong)} - % {guess[:-1]}"
			CWzator(msg=qrz, wpm=wpm, pitch=pitch)
			guess=guess[:-1] + dgt(prompt=prompt, kind="s", smin=0, smax=64)
		guess=guess.lower(); qrz=qrz.lower()
		diff=MistakesCollectorInStrings(qrz,guess)
		print(f"TX: {qrz} RX: {guess} <>: {diff}")
		if qrz == guess:
			callsget.append(qrz)
			if repeatedflag: callsrepeated+=1
			if wpm<100: wpm+=1
		else:
			callswrong.append(qrz.lower())
			dz_mistakes[len(callssend)]=(qrz,guess)
			if wpm>15: wpm-=1
		calls+=1
		if wpm>maxwpm: maxwpm=wpm
		if wpm<minwpm: minwpm=wpm
		repeatedflag=False
	exerctime=dt.datetime.now()-starttime
	print("It's over! Now let me check what we've got.")
	if calls>14 and len(callsget)>0:
		send_char=0
		for j in callssend:
			send_char+=len(j)
		print(f"In this session #{sessions}, I sent {calls} {kindstring} to you and you got {len(callsget)} of them: {len(callsget)*100/calls:.1f}%")
		print(f"\t{len(callsget)-callsrepeated} of these has been taken at the first shot: {(len(callsget)-callsrepeated)*100/len(callsget):.1f}%")
		print(f"\twhile {callsrepeated} {kindstring} with repetition: {callsrepeated*100/len(callsget):.1f}%.")
		print(f"You ran with a minimum speed of {minwpm} up to {maxwpm}: range of {maxwpm-minwpm} WPM.")
		dict_mistakes = MistakesCollectorInLists(callssend, callswrong)
		results=GroupMistakesByFrequency(dict_mistakes)
		print("Character: mistakes = Percentage")
		for item in results:
			print(item.upper())
		global_mistakes = sum([v[0] for v in dict_mistakes.values()])
		print(f"\nTotal mistakes: {global_mistakes} on {send_char} = {global_mistakes*100/send_char:.2f}%")
		good_letters = AlwaysRight(callssend, dict_mistakes)
		print("\nNever misspelled characters:", " ".join(good_letters).upper())
		f=open("CWapu_Diary.txt", "a")
		print("Report saved on CW_Diary.txt")
		f.write(f"\nReceiving exercise #{sessions} performed on {str(lt()[0])}/{str(lt()[1])}/{str(lt()[2])} at {str(lt()[3])}, {str(lt()[4])} minutes:\n")
		f.write(f"In this session #{sessions}, I sent {calls} {kindstring} to you and you got {len(callsget)} of them: {len(callsget)*100/calls:.1f}%\n")
		f.write(f"\t{len(callsget)-callsrepeated} of these has been taken at the first shot: {(len(callsget)-callsrepeated)*100/len(callsget):.1f}%\n")
		f.write(f"\twhile {callsrepeated} {kindstring} with repetition: {callsrepeated*100/len(callsget):.1f}%.\n")
		f.write(f"You ran with a minimum speed of {minwpm} up to {maxwpm}: range of {maxwpm-minwpm} WPM.\n")
		f.write("Character: mistakes = Percentage")
		for item in results:
			f.write("\n"+item.upper())
		f.write("\nList of wrong received words:")
		for k, v in dz_mistakes.items():
			rslt=MistakesCollectorInStrings(v[0],v[1])
			f.write(f"\n\t({k}) TX: {v[0]}, RX: {v[1]}, DIF: {rslt};")
		f.write(f"\nTotal mistakes: {global_mistakes} on {send_char} = {global_mistakes*100/send_char:.2f}%")
		f.write(f"\nNever misspelled characters: {' '.join(good_letters).upper()}")
		nota=dgt(prompt="Note on this exercise: ", kind="s", smin=0, smax=512)
		if nota != "":
			f.write(f"\nNote: {nota}\n***\n")
		else:
			f.write(f"\nNote: empty\n***\n")
		f.close()
	else: print(f"You received too few {kindstring} to generate a consistant statistics.")
	totalcalls+=calls
	totalget+=len(callsget)
	totalwrong+=len(callswrong)
	totaltime+=exerctime
	sessions+=1
	f=open("CWapu_Rxing.pkl", "wb")
	pickle.dump([wpm, totalcalls, sessions, totalget, totalwrong, totaltime], f)
	f.close()
	print(f"Session {sessions-1}, lasts: {str(exerctime)[:-5]} has been saved on disk.")
	return

#main
print(f"\nCWAPU - VERSION: {VERS} BY GABE - IZ4APU.\n----UTILITIES FOR YOUR CW----\n\t\tPress 'm' for menu.")
try:
	f=open("CWapu_Overall.pkl", "rb")
	overall_speed, overall_hertz = pickle.load(f)
	f.close()
except IOError:
	overall_speed, overall_hertz = 30, 550

while True:
	k=menu(d=MNMAIN,show=False,keyslist=True,ntf="It's not a command!")
	if k=="c": Count()
	elif k=="t": Txing()
	elif k=="r": Rxing()
	elif k=="h": overall_hertz=dgt(prompt=f"New frequency for cw? (return to accept {overall_hertz}) > ",kind="i",imin=130,imax=1300); overall_settings_changed=True
	elif k=="s": overall_speed=dgt(prompt=f"New speed for cw? (return to accept {overall_speed}) > ",kind="i",imin=8,imax=100); overall_settings_changed=True
	elif k=="l":
		ltc=pyperclip.paste()
		if ltc:
			ltc=StringCleaning(ltc)
			CWzator(msg=ltc, wpm=overall_speed, pitch=overall_hertz)
		else: CWzator(msg="empty", wpm=overall_speed, pitch=overall_hertz)
	elif k=="m": menu(d=MNMAIN,show_only=True)
	elif k=="w": CreateDictionary()
	elif k=="q": break
print("\nI hope to see you soon - 73 de IZ4APU TU EE")
CWzator(msg="hpe cuagn - 73 de iz4apu tu e e", wpm=40, pitch=599)
if overall_settings_changed:
	f=open("CWapu_Overall.pkl", "wb")
	pickle.dump([overall_speed, overall_hertz],f)
	f.close()
wait(8)
sys.exit()