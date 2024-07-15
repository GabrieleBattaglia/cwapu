# CWAPU - Utility per il CW, di Gabry, IZ4APU
# Data concepimento 21/12/2022.
# GitHub publishing on july 2nd, 2024.

import sys, random, pickle, string
import datetime as dt
from GBUtils import key, dgt, menu
from cwzator import *
from time import localtime as lt

#constants
VERS="1.1.0-Beta, july 2024"
MNMAIN={
	"c":"Counting results",
	"t":"Transmitting exercise",
	"r":"Receiving exercise",
	"m":"shows Menu",
	"q":"To quit this app"}
MNRX={
	"1":"Call-like",
	"2":"Groups"}
MNRXKIND={
										"1":"Letters only",
										"2":"Numbers only",
										"3":"Letters and Numbers",
										"4":"Custom set"}
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

#Variable
wpm=22

#quif
def CustomSet(wpm):
	cs=""
	print("Type all characters you want to practice on. (minimum of 2) Empty line to proceed")
	while True:
		scelta=key().lower()
		if scelta=="": break
		elif scelta not in cs:
			cs+=scelta
			CWzator(msg=scelta, wpm=wpm, pitch=550)
		else: CWzator(msg="?", wpm=wpm, pitch=550)
	return cs
def GeneratingGroup(kind, length, wpm):
	if kind == "1":
		return ''.join(random.choice(string.ascii_letters) for _ in range(length))
	elif kind == "2":
		return ''.join(random.choice(string.digits) for _ in range(length))
	elif kind == "3":
		return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))
	elif kind == "4":
		return CustomSet(wpm)
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
		f=open("CWapu_Diary.txt", "a")
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
		f.close()
	else:
		print(f"Groups received {cont} up to 100: exercise not saved on disk.")
	f=open("CWapu_Index.pkl", "wb")
	esnum+=1
	pickle.dump(esnum, f)
	f.close()
	print("Bye for now, back to main menu.")
	return


def Rxing():
	# receiving exercise
	print("Time to receive? Yep, you're to the right place. Let's go!\n\tLoading your progresses...")
	try:
		f=open("CWapu_Rxing.pkl", "rb")
		wpm, totalcalls, sessions, totalget, totalwrong, totaltime = pickle.load(f)
		f.close()
		print(f"I got your data from disk, so:\nYour actual WPM is {wpm} and you did {sessions-1} sessions.\nI sent to you {totalcalls} total calls-like or groups, and you got {totalget} of them, while {totalwrong} were missed\nYour overall time receiving calls-like is {str(totaltime)[:-5]}.")
	except IOError:
		print("Ups, this is your first class, probably. So I'm creating the record.")
		wpm, totalcalls, sessions, totalget, totalwrong, totaltime = 22, 0, 1, 0, 0, dt.datetime.now()-dt.datetime.now()
	calls, callsget, callswrong, callsrepeated, minwpm, maxwpm, repeatedflag = 0, [], [], 0, 100, 14, False
	wpm=dgt(prompt=f"Do you want to set your WPM? Enter to accept {wpm}> ",kind="i",imin=10,imax=85,default=wpm)
	print("Now select which exercise do you want to take:")
	call_or_groups=menu(d=MNRX,show=True,keyslist=True,ntf="Please, just 1 or 2")
	if call_or_groups == "2":
		kind=menu(d=MNRXKIND,show=True,keyslist=True,ntf="1 2 or 3, please")
		length=dgt(prompt="Give me the length of the group in between 1 and 7: ",kind="i",imin=1,imax=7)
		kindstring="Group"
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
		pitch=random.randint(350, 850)
		prompt=f"S{sessions}-#{calls} - WPM{wpm} - +{len(callsget)}/-{len(callswrong)} - > "
		CWzator(msg=qrz, wpm=wpm, pitch=pitch)
		guess=dgt(prompt=prompt, kind="s", smin=0, smax=6)
		if guess==".": break
		elif guess == "" or "?" in guess:
			repeatedflag=True
			prompt=f"S{sessions}-#{calls} - WPM{wpm} - +{len(callsget)}/-{len(callswrong)} - % {guess[:-1]}"
			CWzator(msg=qrz, wpm=wpm, pitch=pitch)
			guess=guess[:-1] + dgt(prompt=prompt, kind="s", smin=0, smax=6)
		if qrz.lower() == guess.lower():
			callsget.append(qrz)
			if repeatedflag: callsrepeated+=1
			if wpm<100: wpm+=1
		else:
			callswrong.append(qrz)
			if wpm>15: wpm-=1
		calls+=1
		if wpm>maxwpm: maxwpm=wpm
		if wpm<minwpm: minwpm=wpm
		repeatedflag=False
	exerctime=dt.datetime.now()-starttime
	print("It's over! Now let me check what we've got.")
	if calls>14 and len(callsget)>0:
		print(f"In this session #{sessions}, I sent {calls} {kindstring} to you and you got {len(callsget)} of them: {len(callsget)*100/calls:.1f}%")
		print(f"\t{len(callsget)-callsrepeated} of these has been taken at the first shot: {(len(callsget)-callsrepeated)*100/len(callsget):.1f}%")
		print(f"\twhile {callsrepeated} {kindstring} with repetition: {callsrepeated*100/len(callsget):.1f}%.")
		print(f"You ran with a minimum speed of {minwpm} up to {maxwpm}: range of {maxwpm-minwpm} WPM.")
		f=open("CWapu_Diary.txt", "a")
		print("Report saved on CW_Diary.txt")
		f.write(f"Receiving exercise #{sessions} performed on {str(lt()[0])}/{str(lt()[1])}/{str(lt()[2])} at {str(lt()[3])}, {str(lt()[4])} minutes:\n")
		f.write(f"In this session #{sessions}, I sent {calls} {kindstring} to you and you got {len(callsget)} of them: {len(callsget)*100/calls:.1f}%\n")
		f.write(f"\t{len(callsget)-callsrepeated} of these has been taken at the first shot: {(len(callsget)-callsrepeated)*100/len(callsget):.1f}%\n")
		f.write(f"\twhile {callsrepeated} {kindstring} with repetition: {callsrepeated*100/len(callsget):.1f}%.\n")
		f.write(f"You ran with a minimum speed of {minwpm} up to {maxwpm}: range of {maxwpm-minwpm} WPM.\n")
		nota=dgt(prompt="Note on this exercise: ", kind="s", smin=0, smax=512)
		if nota != "":
			f.write(f"Note: {nota}\n***\n")
		else:
			f.write(f"Note: empty\n***\n")
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
print(f"CWAPU - VERSION: {VERS} BY GABE - IZ4APU.\n----UTILITIES FOR YOUR CW----")
while True:
	k=menu(d=MNMAIN,show=True,keyslist=True,ntf="It's not a command!")
	if k=="c": Count()
	elif k=="t": Txing()
	elif k=="r": Rxing()
	elif k=="m": menu(d=MNMAIN,show_only=True)
	elif k=="q": break
print("\nI hope to see you soon - 73 de IZ4APU TU EE")
CWzator(msg="73 de iz4apu tu ee", wpm=wpm, pitch=550)
sys.exit()