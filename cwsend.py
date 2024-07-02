import sys
from cwzator import *

wpm=int(input("WPM: "))
pitch=int(input("HZ: "))
print("\ per uscire")
while True:
	msg=sys.stdin.readline()
	msg=msg[:-1]+" "
	if msg=="\ ": sys.exit()
	CWzator(msg=msg, wpm=wpm, pitch=pitch)