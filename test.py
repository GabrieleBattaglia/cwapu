import time
from cwzator6 import CWZator6
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
def calculate_expected_duration(msg, wpm, l, s, p):
	T = 1.2/float(wpm)
	dot_duration = T * (p/50.0)
	dash_duration = 3 * T * (l/30.0)
	intra_gap = T * (s/50.0)
	letter_gap = 3 * T * (s/50.0)
	word_gap = 7 * T * (s/50.0)
	total = 0.0
	words = msg.lower().split()
	for w_idx, word in enumerate(words):
		letters = [ch for ch in word if ch in morse_map]
		for l_idx, letter in enumerate(letters):
			code = morse_map[letter]
			for s_idx, symbol in enumerate(code):
				if symbol == '.':
					total += dot_duration
				elif symbol == '-':
					total += dash_duration
				if s_idx < len(code)-1:
					total += intra_gap
			if l_idx < len(letters)-1:
				total += letter_gap
		if w_idx < len(words)-1:
			total += word_gap
	return total
test_str = ("Ciao, sono gabriele battaglia e sto testando questa routine per creare codice morse. "
            "voglio calcolare gli effettivi tempi di esecuzione passando una lunga stringa per verificare "
            "se il calcolo dei tempi rimane entro parametri accettabili. 73 de iz4apu")
wpm_val = 45
pitch_val = 480
tests = [
	("Test 1 - Standard", 30, 50, 50),
	("Test 2", 30, 75, 50),
	("Test 3", 30, 75, 28),
	("Test 4", 30, 50, 18),
	("Test 5", 50, 50, 50),
	("Test 6", 40, 25, 67),
	("Test 7", 20, 50, 35),
	("Test 8", 70, 20, 58)
]
for desc, l_val, s_val, p_val in tests:
	expected_sec = calculate_expected_duration(test_str, wpm_val, l_val, s_val, p_val)
	minutes = int(expected_sec // 60)
	seconds = int(expected_sec % 60)
	milliseconds = int((expected_sec - int(expected_sec)) * 1000)
	print(f"{desc}: L={l_val}, S={s_val}, P={p_val}")
	print(f"Expected duration: {minutes} min {seconds} sec {milliseconds} ms (total {expected_sec:.3f} sec)")
	start_time = time.perf_counter()
	CWZator6(test_str, wpm=wpm_val, pitch=pitch_val, l=l_val, s=s_val, p=p_val, sync=True, vol=0.3,	wave=4)
	end_time = time.perf_counter()
	actual_sec = end_time - start_time
	diff_percent = abs(actual_sec - expected_sec) / expected_sec * 100 if expected_sec > 0 else 0
	print(f"Actual duration: {actual_sec:.3f} sec")
	print(f"Difference: {diff_percent:.2f}%\n")
