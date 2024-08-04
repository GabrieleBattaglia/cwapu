import numpy as np
import sounddevice as sd
import math, time
from collections import deque

class Keyer():
	"""
	Class to encode text to morse and produce keying envelope from morse
	"""
	_morse = ({ "a":".-", "b":"-...", "c":"-.-.", "d":"-..", "e":".", "f":"..-.",
			"g":"--.", "h":"....", "i":"..", "j":".---", "k":"-.-", "l":".-..",
			"m":"--", "n":"-.", "o":"---", "p":".--.", "q":"--.-", "r":".-.",
			"s":"...", "t":"-", "u":"..-", "v":"...-", "w":".--", "x":"-..-",
			"y":"-.--", "z":"--..", "0":"-----", "1":".----", "2":"..---",
			"3":"...--", "4":"....-", "5":".....", "6":"-....", "7":"--...",
			"8":"---..", "9":"----.", ".":".-.-.-", "-":"-....-", ",":"--..--",
			"?":"..--..", "/":"-..-.", ";":"-.-.-.", "(":"-.--.", "[":"-.--.",
			")":"-.--.-", "]":"-.--.-", "@":".--.-.", "*":"...-.-", "+":".-.-.",
			"%":".-...", ":":"---...", "=":"-...-", '"':".-..-.", "'":".----.",
			"!":"-.-.--", "$":"...-..-"," ":"", "_":"",
			"ò":"---.", "à":".--.-", "ù":"..--", "è":"..-..",
			"é":"..-..", "ì":".---."
	})

	def __init__(self, rate=11025, bufsize=512, risetime=0.005, reg_balance=True, dot=100, dash=300, insgn=100, inchr=300):
		"""
		Keyword arguments:
			rate: audio sample rate (default 11025)
			bufsize: audio buffer size (default 512)
			risetime: keyer risetime in seconds (default 0.005)
			reg_balance: regulate balance based on WPM (default True)
			dot: length of dot in ms (default 100)
			dash: length of dash in ms (default 300)
			insgn: length of space between dots and dashes in ms (default 100)
			inchr: length of space between characters in ms (default 300)
		"""
		self.rate = rate
		self._bufsize = bufsize
		self.risetime = risetime
		self.reg_balance = reg_balance
		self.dot = dot
		self.dash = dash
		self.insgn = insgn
		self.inchr = inchr

	@property
	def risetime(self):
		"""
		keyer risetime in seconds
		"""
		return self._risetime

	@risetime.setter
	def risetime(self, risetime):
		self._risetime = risetime
		x = np.arange(0.0, 1.0, 1.0 / (2.7 * risetime * self.rate))
		erf = np.frompyfunc(math.erf, 1, 1)
		self.rise = 0.5 * (1.0 + erf(5 * (x - 0.5))).astype(np.float32)
		self.fall = np.array(self.rise)
		self.fall[:] = self.rise[len(self.rise)::-1]

	def encode(self, txt):
		"""
		Arguments:
			txt: ascii text to convert to morse
		Returns:
			string encoding for morse dits and dahs
		"""
		s = ""
		for i in range(len(txt) - 1):
			s += Keyer._morse[txt[i]] + " "
		s += Keyer._morse[txt[len(txt) - 1]]
		if s != "":
			s += "~"
		return s

	def getenvelop(self, msg, wpm):
		"""
		Arguments:
			msg: morse encoding of dits and dahs
			wpm: speed in words per minute (PARIS)
		Returns:
			keying envelop for audio samples
		"""
		nr = len(self.rise)

		if self.reg_balance:
			dot_length = int(np.rint(1.2 * self.rate / wpm))
			dash_length = 3 * dot_length
			insgn_length = dot_length
			inchr_length = 3 * dot_length
		else:
			dot_length = int(self.dot / 1000 * self.rate)
			dash_length = int(self.dash / 1000 * self.rate)
			insgn_length = int(self.insgn / 1000 * self.rate)
			inchr_length = int(self.inchr / 1000 * self.rate)

		count = 2 * (msg.count('.') + msg.count(' ') + 2 * msg.count('-')) + msg.count('~')
		n = int(self._bufsize * np.ceil((count * dot_length + nr) / self._bufsize))

		env = np.zeros(n, dtype=np.float32)

		dit = np.ones(nr + dot_length, dtype=np.float32)
		dit[:nr] = self.rise
		dit[dot_length:] = self.fall

		dah = np.ones(nr + dash_length, dtype=np.float32)
		dah[:nr] = self.rise
		dah[dash_length:] = self.fall

		k = 0
		for i in range(len(msg)):
			if msg[i] == '.':
				env[k:k + len(dit)] = dit
				k += 2 * insgn_length
			elif msg[i] == '-':
				env[k:k + len(dah)] = dah
				k += 4 * insgn_length
			elif msg[i] == ' ':
				k += 2 * insgn_length - nr
				if i > 0 and msg[i - 1] == ' ':
					k += 2 * inchr_length
			elif msg[i] == '~':
				k += insgn_length - nr
		return env

class CWSender:
	def __init__(self, pitch=500, amp=0.7, bufsize=512, rate=11025):
		self.pitch = pitch
		self.amp = amp
		self._keyer = Keyer(rate, bufsize)
		self._bufsize = bufsize
		self._rate = rate
		self._phase = 0.0
		self._stream = sd.OutputStream(samplerate=rate
									   , blocksize=bufsize, channels=1, dtype=np.float32, latency=0.1
									   , callback=self._getAudio)
		self._started = False
		self._envelopes = deque()
		self._envelop = None

	def audioOn(self, on):
		if on:
			if not self._started:
				self._stream.start()
		else:
			if self._started:
				self._stream.stop()

	def addMessage(self, msg, wpm, pitch=0, dot=100, dash=300, insgn=100, inchr=300, reg_balance=True):
		self._keyer.reg_balance = reg_balance
		self._keyer.dot = dot
		self._keyer.dash = dash
		self._keyer.insgn = insgn
		self._keyer.inchr = inchr
		self._envelopes.append((pitch,
			self._keyer.getenvelop(self._keyer.encode(msg.lower()), wpm)))

	def _getBuffer(self):
		if self._envelop is None:
			if len(self._envelopes) > 0:
				(pitch, self._envelop) = self._envelopes.popleft()
				if pitch != 0:
					self.pitch = pitch
				self._sendpos = 0
		if self._envelop is None:
			buffer = np.zeros(self._bufsize, dtype=np.float32)
		else:
			buffer = self._envelop[self._sendpos:self._sendpos + self._bufsize]
			self._sendpos += self._bufsize
			if self._sendpos >= len(self._envelop):
				self._envelop = None
				self._sendpos = 0
		return buffer

	def _getAudio(self, outdata, nf, tinfo, status):
		buf = self._getBuffer()
		dphase = 2.0 * np.pi * self.pitch / self._rate
		phases = np.arange(self._bufsize, dtype=np.float64) * dphase + self._phase
		outdata[:, 0] = buf * self.amp * np.sin(phases).astype(np.float32)
		self._phase = (phases[-1] + dphase) % (2.0 * np.pi)

sender = None

def CWzator(msg, wpm=35, pitch=550, dot=100, dash=300, insgn=100, inchr=300, reg_balance=True):
	'''
	Convert txt to Morse, copyright IZ4APU Gabe and W9CF Kevin.
	RX msg, wpm, pitch, dot, dash, insgn, inchr, reg_balance
	TX False if prompt is empty.
	ToDo parameters to customize sits/dashes balance and spaces
	ToDo security controls over incoming variables to avoid errors
	'''
	if msg == "": return False
	global sender
	if sender is None:
		sender = CWSender()
		sender.audioOn(True)
	sender.addMessage(msg, wpm, pitch, dot, dash, insgn, inchr, reg_balance)