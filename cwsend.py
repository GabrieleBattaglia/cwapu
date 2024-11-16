import sys
from cwzator2 import *

wpm=int(input("WPM: "))
pitch=550
param=input("l p s")
x = param.split(".")
p=int(x[1])
l=int(x[0])
s=int(x[2])
print("\ per uscire")
while True:
	msg=sys.stdin.readline()
	msg=msg[:-1]+" "
	if msg=="\ ": sys.exit()
	CWzator2(msg=msg, wpm=wpm, pitch=pitch, dashes=l, dots=p, spaces=s)
	