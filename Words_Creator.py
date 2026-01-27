# Creato assieme a ChatGPT4o il 4 agosto 2024
import os
import string
import tkinter as tk
from tkinter import filedialog
from GBUtils import key

def LoadInitialDictionary(file_path):
	with open(file_path, 'r', encoding='utf-8') as file:
		dictionary = set(line.strip().lower() for line in file)
	return dictionary

def ChooseFolder():
	root = tk.Tk()
	root.withdraw()
	root.attributes("-topmost", True)
	folder_path = filedialog.askdirectory(title="Choose a directory:")
	root.destroy()
	return folder_path if folder_path else None

def clean_line(line):
	# Replace apostrophes with spaces
	line = line.replace("'", " ")
	# Replace punctuation with spaces
	line = line.translate(str.maketrans(string.punctuation, ' ' * len(string.punctuation)))
	# Convert to lowercase
	line = line.lower()
	# Remove multiple spaces and trim
	line = ' '.join(line.split())
	return line

def is_valid_word(word):
	# Define valid characters
	valid_chars = set(string.ascii_lowercase + "àèéìòù")
	return all(char in valid_chars for char in word)

def process_text_file(file_path, dictionary):
	added_words = 0
	discarded_words = 0
	processed_lines = 0
	try:
		with open(file_path, 'r', encoding='utf-8') as file:
			for line in file:
				processed_lines += 1
				# Clean the line
				cleaned_line = clean_line(line)
				# Split into words
				words = cleaned_line.split()
				for word in words:
					if is_valid_word(word) and word not in dictionary:
						dictionary.add(word)
						added_words += 1
					else:
						discarded_words += 1
	except UnicodeDecodeError:
		try:
			with open(file_path, 'r', encoding='ISO-8859-1') as file:
				for line in file:
					processed_lines += 1
					# Clean the line
					cleaned_line = clean_line(line)
					# Split into words
					words = cleaned_line.split()
					for word in words:
						if is_valid_word(word) and word not in dictionary:
							dictionary.add(word)
							added_words += 1
						else:
							discarded_words += 1
		except UnicodeDecodeError:
			return processed_lines, added_words, discarded_words, False
	return processed_lines, added_words, discarded_words, True

def ProcessFolder(folder_path, dictionary):
	total_files = 0
	total_lines = 0
	total_added_words = 0
	total_discarded_words = 0
	skipped_files = []
	total_folders = 0
	for root, _, files in os.walk(folder_path):
		total_folders += 1
		for file_name in files:
			if file_name.endswith('.txt'):
				total_files += 1
				file_path = os.path.join(root, file_name)
				lines, added_words, discarded_words, success = process_text_file(file_path, dictionary)
				total_lines += lines
				total_added_words += added_words
				total_discarded_words += discarded_words
				if not success:
					skipped_files.append(file_name)
	return total_files, total_lines, total_added_words, total_discarded_words, skipped_files, total_folders

def SaveDictionary(dictionary, output_file):
	with open(output_file, 'w', encoding='utf-8') as file:
		for word in sorted(dictionary):
			if isinstance(word, str) and word.isprintable():
				file.write(word + '\n')
import sys

def resource_path(relative_path):
	""" Get absolute path to resource, works for dev and for PyInstaller """
	try:
		# PyInstaller creates a temp folder and stores path in _MEIPASS
		base_path = sys._MEIPASS
	except Exception:
		base_path = os.path.abspath(".")
	return os.path.join(base_path, relative_path)

def Start():
	print("Now, let's begin: this script will ask you to select a folder from the filesystem.\nAll .txt files within the folder and its subfolders will be opened and processed.")
	discard=key(prompt="Press any key to continue...")
	print("Thank you")
	
	# Try to load words.txt from current directory first, then fallback to internal resource
	words_path = 'words.txt'
	if not os.path.exists(words_path):
		words_path = resource_path('words.txt')
		if not os.path.exists(words_path):
			# Fallback if somehow neither exists (shouldn't happen with correct build)
			print("Error: words.txt not found in current directory or internal resources.")
			return

	initial_dictionary = LoadInitialDictionary(words_path)
	initial_word_count = len(initial_dictionary)
	folder_path = ChooseFolder()
	if not folder_path:
		print("No folder selected. Exiting the script.")
		return
	total_files, total_lines, total_added_words, total_discarded_words, skipped_files, total_folders = ProcessFolder(folder_path, initial_dictionary)
	SaveDictionary(initial_dictionary, 'words_updated.txt')
	final_word_count = len(initial_dictionary)
	word_difference = final_word_count - initial_word_count
	percentage_change = (word_difference / initial_word_count) * 100 if initial_word_count > 0 else 0
	print(f"Total number of folders processed: {total_folders}")
	print(f"Total number of files read: {total_files}")
	print(f"Total number of lines processed: {total_lines}")
	print(f"Total number of words added: {total_added_words}")
	print(f"Total number of words discarded: {total_discarded_words}")
	print(f"Initial number of words in the dictionary: {initial_word_count}")
	print(f"Final number of words in the dictionary: {final_word_count}")
	print(f"Percentage change in the dictionary: {percentage_change:.2f}%")
	print(f"Number of files skipped due to incorrect encoding: {len(skipped_files)}")
	if skipped_files:
		print("Skipped files:")
		for skipped_file in skipped_files:
			print(f" - {skipped_file}")
