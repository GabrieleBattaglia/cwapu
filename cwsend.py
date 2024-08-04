import sys
from cwzator2 import *

wpm=int(input("WPM: "))
pitch=int(input("HZ: "))
param=input("dot.dash,insgn,inchr")
l = param.split(".")
dot=int(l[0])
dash=int(l[1])
insgn=int(l[2])
inchr=int(l[3])
print("\ per uscire")
while True:
	msg=sys.stdin.readline()
	msg=msg[:-1]+" "
	if msg=="\ ": sys.exit()
	#CWzator(msg=msg, wpm=wpm, pitch=pitch, dot=dot, dash=dash, insgn=insgn, inchr=inchr, reg_balance=False)
	