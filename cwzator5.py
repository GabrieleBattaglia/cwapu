import numpy as np
import sounddevice as sd
import math, time
from collections import deque
class Keyer():
	"""
	Class to encode text to morse and produce keying envelope from morse
	with customizable timing parameters
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
	
	def __init__(self, rate=11025, bufsize=512, risetime=0.005):
		self.rate = rate
		self._bufsize = bufsize
		self.risetime = risetime
		self._p = 50  # Default dot length
		self._s = 50  # Default space length
		self._l = 30  # Default line length factor
		
	@property
	def risetime(self):
		return self._risetime
		
	@risetime.setter
	def risetime(self, risetime):
		self._risetime = risetime
		x = np.arange(0.0, 1.0, 1.0/(2.7*risetime*self.rate))
		erf = np.frompyfunc(math.erf, 1, 1)
		self.rise = 0.5*(1.0 + erf(5*(x-0.5))).astype(np.float32)
		self.fall = np.array(self.rise)
		self.fall[:] = self.rise[len(self.rise)::-1]
		
	def set_timing(self, p=50, s=None, l=30):
		"""Set custom timing parameters"""
		self._p = max(1, min(99, p))
		self._s = self._p if s is None else max(1, min(99, s))
		self._l = max(1, min(99, l))
		
	def encode(self, txt):
		s = ""
		for i in range(len(txt)-1):
			s += Keyer._morse[txt[i]] + " "
		s += Keyer._morse[txt[len(txt)-1]]
		if s != "":
			s += "~"
		return s
	def getenvelop(self, msg, wpm):
		nr = len(self.rise)
		# Calculate base sample length from WPM
		base_samples = int(np.rint(1.2*self.rate/wpm))
		base_time_no_risetime = 1.2 / wpm  # Calcola base_time senza risetime
		base_time = (base_samples + 2 * len(self.rise)) / self.rate # Calcola base_time CON risetime
		# Adjust sample lengths based on p, s, and l parameters
		dot_samples = int(base_samples * (self._p/50))
		space_samples = int(base_samples * (self._s/50))
		dash_samples = int(dot_samples * (self._l/10))
		# Calculate total samples needed
		count = (msg.count('.') * (dot_samples + space_samples) + 
				msg.count('-') * (dash_samples + space_samples) +
				msg.count(' ') * (2 * space_samples) +
				msg.count('~') * space_samples)
		n = int(self._bufsize * np.ceil((count + nr)/self._bufsize))
		env = np.zeros(n, dtype=np.float32)
		# Create dot and dash envelopes
		dit = np.ones(nr + dot_samples, dtype=np.float32)
		dit[:nr] = self.rise
		dit[dot_samples:] = self.fall
		dah = np.ones(nr + dash_samples, dtype=np.float32)
		dah[:nr] = self.rise
		dah[dash_samples:] = self.fall
		k = 0
		for i in range(len(msg)):
			if msg[i] == '.':
				env[k:k+len(dit)] = dit
				k += dot_samples + space_samples
			elif msg[i] == '-':
				env[k:k+len(dah)] = dah
				k += dash_samples + space_samples
			elif msg[i] == ' ':
				k += 2 * space_samples
			elif msg[i] == '~':
				k += space_samples
		return env, base_time, base_time_no_risetime

class CWSender:
	def __init__(self, pitch=500, amp=0.7, bufsize=512, rate=11025):
		self.pitch = pitch
		self.amp = amp
		self._keyer = Keyer(rate, bufsize)
		self._bufsize = bufsize
		self._rate = rate
		self._phase = 0.0
		self._stream = sd.OutputStream(samplerate=rate,
			blocksize=bufsize, channels=1, dtype=np.float32, latency=0.1,
			callback=self._getAudio)
		self._started = False
		self._envelopes = deque()
		self._envelop = None
	def set_timing(self, p=50, s=None, l=30):
		self._keyer.set_timing(p, s, l)
	def audioOn(self, on):
		if on and not self._started:
			self._stream.start()
			self._started = True
		elif not on and self._started:
			self._stream.stop()
			self._started = False
	def addMessage(self, msg, wpm, pitch=0):
		msg=msg[:-1]
		num_elements = len(msg)  # Calcola la lunghezza della stringa originale
		print(f"T: ({msg})")
		envelop, base_time, base_time_no_risetime = self._keyer.getenvelop(self._keyer.encode(msg.lower()), wpm) # Corretto: assegnare solo 3 valori
		self._envelopes.append((pitch, envelop, num_elements))
		return base_time, base_time_no_risetime, num_elements
	def _getBuffer(self):
		if self._envelop is None:
			if len(self._envelopes) > 0:
				(pitch, self._envelop, self.num_elements) = self._envelopes.popleft()
				if pitch != 0:
					self.pitch = pitch
				self._sendpos = 0
				self._start_time = time.time() # Registra il tempo di inizio del messaggio
		if self._envelop is None:
			buffer = np.zeros(self._bufsize, dtype=np.float32)
		else:
			buffer = self._envelop[self._sendpos:self._sendpos+self._bufsize]
			self._sendpos += self._bufsize
			if self._sendpos >= len(self._envelop) and self._start_time is not None: # Controlla se il messaggio è terminato
				end_time = time.time()
				total_time = end_time - self._start_time
				minutes = int(total_time // 60)
				seconds = total_time % 60
				total_time_formatted = f"{minutes:02d}:{seconds:06.3f}"
				chars_per_minute = 0
				if total_time > 0:
					chars_per_minute = self.num_elements / (total_time / 60)
				print(f"Tempo totale: {total_time_formatted}, Caratteri trasmessi: {self.num_elements}, Velocità: {chars_per_minute:.2f} caratteri/minuto")
				self._start_time = None
				self._envelop = None
				self._sendpos = 0
		return buffer
		
	def _getAudio(self, outdata, nf, tinfo, status):
		buf = self._getBuffer()
		dphase = 2.0*np.pi*self.pitch/self._rate
		phases = np.arange(self._bufsize, dtype=np.float64)*dphase + self._phase
		outdata[:,0] = buf*self.amp*np.sin(phases).astype(np.float32)
		self._phase = (phases[-1]+dphase) % (2.0*np.pi)

sender = None

def CWzator5(msg, wpm=35, pitch=550, dashes=30, spaces=None, dots=50, vol=0.7, risetime=0.002): 
	'''
	Convert txt to Morse with customizable timing parameters
	V4 by W9CF, IZ4APU and Gemini EXP114
	Args:
		msg: text message to convert
		wpm: words per minute (default 35)
		pitch: tone frequency in Hz (default 550)
		vol: volume from 0 to 1 (default 0.7)
		dots: dot length 1-99 (default 50)
		spaces: space length 1-99 (default=p)
		dashes: dash length factor 1-99 (default 30, meaning dash = 3*dot)
		risetime: time for signal ramp up/down in seconds (default 0.002)
	Returns:
		wpm_offset: float indicating the difference from the desired speed if parameters are not default.
	'''
	if msg == "": 
		return False
	# Input validation
	wpm = max(5, min(99, wpm))
	vol = max(0, min(1, vol))
	dots = max(1, min(99, dots))
	spaces = dots if spaces is None else max(1, min(99, spaces))
	dashes = max(1, min(99, dashes))
	global sender
	if sender is None:
		sender = CWSender(pitch=pitch, amp=vol)
		sender.audioOn(True)
	else:
		sender.amp = vol
		sender.pitch = pitch
	sender.set_timing(dots, spaces, dashes)
	sender._keyer.risetime = risetime  # Imposta il risetime
	base_time, base_time_no_risetime, num_elements = sender.addMessage(msg, wpm, pitch)
	wpm_offset = 0
	if (dashes != 30 or spaces != dots or dots != 50):
		wpm_offset = base_time / base_time_no_risetime
	return wpm_offset