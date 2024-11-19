# tentativo di Claude 3.5 concise per implementare il rise_time nel calcolo wpm e restituire il real_speed se si cambia peso LSP
# da verificare e implementare non ha scritto tutti i metodi.

import numpy as np
import sounddevice as sd
import math
from collections import deque

class Keyer:
    _morse = { ... }  # Dizionario Morse invariato
    
    def __init__(self, rate=11025, bufsize=512, risetime=0.002):  # Ridotto a 2ms
        self.rate = rate
        self._bufsize = bufsize
        self.risetime = risetime
        self._p = 50
        self._s = 50
        self._l = 30
        self._actual_risetime_samples = len(self.rise)
    
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
        
    def calculate_wpm_offset(self, base_samples, dot_samples, dash_samples):
        """Calcola l'offset WPM rispetto alle impostazioni standard"""
        standard_dot = base_samples * (50/50)
        standard_dash = standard_dot * (30/10)
        actual_dot = dot_samples
        actual_dash = dash_samples
        
        dot_ratio = standard_dot / actual_dot
        dash_ratio = standard_dash / actual_dash
        
        return round((dot_ratio + dash_ratio) / 2, 2)

    def getenvelop(self, msg, wpm):
        # Calcolo con compensazione rise time
        base_samples = int(np.rint(1.2*self.rate/wpm))
        rise_samples = len(self.rise)
        
        dot_samples = int(base_samples * (self._p/50)) - rise_samples
        space_samples = int(base_samples * (self._s/50))
        dash_samples = int(dot_samples * (self._l/10)) - rise_samples
        
        wpm_offset = self.calculate_wpm_offset(base_samples, dot_samples, dash_samples)
        
        # Resto del metodo invariato
        count = (msg.count('.') * (dot_samples + space_samples) + 
                 msg.count('-') * (dash_samples + space_samples) +
                 msg.count(' ') * (2 * space_samples) +
                 msg.count('~') * space_samples)
        
        n = int(self._bufsize * np.ceil((count + rise_samples)/self._bufsize))
        env = np.zeros(n, dtype=np.float32)
        
        # Generazione envelope come prima
        # ...

        return env, wpm_offset

class CWSender:
    # Invariato con piccole modifiche per gestire wpm_offset
    def addMessage(self, msg, wpm, pitch=0):
        envelope, wpm_offset = self._keyer.getenvelop(
            self._keyer.encode(msg.lower()), wpm)
        self._envelopes.append((pitch, envelope, wpm_offset))

def CWzator2(msg, wpm=35, pitch=550, dashes=30, spaces=None, dots=50, vol=0.7):
    if msg == "": 
        return False, None

    # Validazione input come prima
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
    sender.addMessage(msg, wpm, pitch)

    # Restituisce anche wpm_offset
    return True, sender._envelopes[-1][2] if sender._envelopes else None
