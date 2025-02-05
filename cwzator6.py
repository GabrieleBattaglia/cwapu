def CWZator6(msg, wpm=35, pitch=550, l=30, s=50, p=50, fs=44100, ms=1, vol=0.5, sync=False, wave=1):
	"""
	Generates and plays Morse code audio from the given text message.
	Parameters:
		msg (str): Text message to convert to Morse code.
		wpm (int): Words per minute rate for Morse timing (valid range: 5 to 100).
		pitch (int): Frequency in Hz for the tone (valid range: 130 to 2000).
		l (int): Weight for dash (line) duration relative to the standard (default 30).
		s (int): Weight for gap (space) duration between symbols relative to the standard (default 50).
		p (int): Weight for dot duration relative to the standard (default 50).
		fs (int): Sampling frequency in Hz (default 44100).
		ms (int): Duration in milliseconds for fade-in and fade-out (anti-click ramps); the tone’s effective duration is reduced by 2*ms (default 1).
		vol (float): Volume multiplier (range 0.0 [silence] to 1.0 [maximum], default 0.5).
		sync (bool): If True, the function blocks until audio playback is finished; otherwise, it returns immediately (default False).
		wave (int): Waveform type for the tone:
		          1 = Sine (default),
		          2 = Square,
		          3 = Triangle,
		          4 = Sawtooth.
	Returns:
		An object representing the playback (from simpleaudio), or None if parameters are invalid.
	"""
	import numpy as np
	import simpleaudio as sa
	if not isinstance(msg, str) or msg == "" or pitch < 130 or pitch > 2000 or wpm < 5 or wpm > 100 or \
	   l < 1 or l > 100 or s < 1 or s > 100 or p < 1 or p > 100 or vol < 0 or vol > 1 or wave not in [1,2,3,4]:
		print("Not valid CW parameters")
		return None
	T = 1.2 / float(wpm)
	dot_duration = T * (p/50.0)
	dash_duration = 3 * T * (l/30.0)
	intra_gap = T * (s/50.0)
	letter_gap = 3 * T * (s/50.0)
	word_gap = 7 * T * (s/50.0)
	def generate_tone(duration):
		N = int(fs * duration)
		t = np.linspace(0, duration, N, False)
		if wave == 1:  # Sine wave
			signal = np.sin(2 * np.pi * pitch * t)
		elif wave == 2:  # Square wave
			signal = np.sign(np.sin(2 * np.pi * pitch * t))
		elif wave == 3:  # Triangle wave
			# Triangle wave: 2 * abs(2*(t*freq - floor(t*freq + 0.5))) - 1
			signal = 2 * np.abs(2 * (pitch * t - np.floor(pitch * t + 0.5))) - 1
		elif wave == 4:  # Sawtooth wave
			# Sawtooth wave: 2*(t*freq - floor(0.5 + t*freq))
			signal = 2 * (pitch * t - np.floor(0.5 + pitch * t))
		fade_samples = int(fs * ms / 1000)
		if fade_samples * 2 < N:
			ramp = np.linspace(0, 1, fade_samples)
			signal[:fade_samples] *= ramp
			signal[-fade_samples:] *= ramp[::-1]
		return (signal * (2**15 - 1) * vol).astype(np.int16)
	def generate_silence(duration):
		return np.zeros(int(fs * duration), dtype=np.int16)
	# Morse code mapping defined at module level (could be imported externally)
	morse_map = { "a":".-", "b":"-...", "c":"-.-.", "d":"-..", "e":".", "f":"..-.",
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
	}
	segments = []
	words = msg.lower().split()
	for w_idx, word in enumerate(words):
		letters = [ch for ch in word if ch in morse_map]
		for l_idx, letter in enumerate(letters):
			code = morse_map[letter]
			for s_idx, symbol in enumerate(code):
				if symbol == '.':
					segments.append(generate_tone(dot_duration))
				elif symbol == '-':
					segments.append(generate_tone(dash_duration))
				if s_idx < len(code)-1:
					segments.append(generate_silence(intra_gap))
			if l_idx < len(letters)-1:
				segments.append(generate_silence(letter_gap))
		if w_idx < len(words)-1:
			segments.append(generate_silence(word_gap))
	audio = np.concatenate(segments) if segments else np.array([], dtype=np.int16)
	play_obj = sa.play_buffer(audio, 1, 2, fs)
	if sync:
		play_obj.wait_done()
	return play_obj