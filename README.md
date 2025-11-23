# CWapu v3.0.1 by Gabriele Battaglia (IZ4APU) and Gemini 2.5

A collection of command-line tools and exercises designed to help amateur radio operators improve their skills in receiving and sending Morse Code (CW).

## Features

CWapu offers several modes to practice and utilize CW:

1.  **Receiving Exercise (Rxing - `r`):**
    * Practice receiving randomly generated pseudo-callsigns or groups.
    * Choose between letters only, numbers only, mixed alphanumeric, a custom character set defined by you, or words from a dictionary file.
    * Adaptive speed: Option to automatically increase/decrease WPM based on your accuracy (or keep it fixed).
    * Adjustable target WPM and number of items per session.
    * Detailed session reports saved to `CWapu_Diary.txt`, including accuracy, WPM range, character-specific mistakes, and a list of missed items.
    * Progress tracking across sessions stored in `cwapu_settings.json`.

2.  **Transmission Practice Aid (Txing - `t`):**
    * Generates random callsign-like structures and sequential numbers.
    * Displays them on screen for you to practice sending using your own key/paddle. Useful for contest/DXpedition preparation.
    * Press ESC to end the exercise.

3.  **Counting Exercise (Counting - `c`):**
    * A generic tool to practice recognizing items. Listen to external CW (or any other source) and simply press SPACE for a correct reception or any other key for an error.
    * Provides real-time feedback on accuracy percentage.
    * Saves a report with statistics and optional notes to `CWapu_Diary.txt` if at least 100 items are attempted.
    * Tracks the exercise number in `cwapu_settings.json`.

4.  **Keyboard CW (Keyboard - `k`):**
    * Type text directly into the console and hear it played as CW.
    * Supports real-time adjustment of WPM, pitch, Farnsworth timing (dash/space/dot lengths), volume, audio sample rate, and waveform (sine, square, triangle, sawtooth) using simple dot commands (e.g., `.w20`, `.h600`, `.l25`, `.sr`, `.f2`). Type `?` for help, `??` for current settings.
    * Save the generated CW audio directly to a `.wav` file using the `.sv` command prefix (e.g., `.sv ciao mondo`).

5.  **Clipboard Playback (`l`):**
    * Instantly plays any text currently copied to the system clipboard as CW using the current settings.

6.  **Dictionary Word Filter/Creator (`w`):**
    * Includes functionality (via `Words_Creator.py`) to process and potentially create word lists compatible with the 'Words' exercise mode. (*Note: Requires `Words_Creator.py` when running from source.*)

7.  **Settings Management:**
    * All application settings (speed, pitch, volume, timing, language, etc.) and exercise statistics are saved in a human-readable `cwapu_settings.json` file.
    * Settings are automatically loaded on startup and saved on exit.

8.  **Multi-language Support (`z`):**
    * The user interface language can be changed on the fly. Currently supports English and Italian. (Requires `translations.py`).

## Requirements & Setup

**For Users of the Compiled Executable (`cwapu.exe` from GitHub Releases):**

* Download `cwapu.exe`.
* You **only** need the `words.txt` file in the same directory as `cwapu.exe` to use the "Words from dictionary" exercise mode. An Italian dictionary is usually provided. You can replace it with a UTF-8 encoded text file containing one word per line for your desired language.
* Optionally, if migrating from v2.x, you will also need `migrateTo3.exe` initially (see Migration section).

**For Users Running from Source Code (`cwapu.py`):**

* Python 3.x.
* The `GBUtils.py` module (available from the GBUtils project on GitHub) must be in the same directory.
* The `translations.py` file for multi-language support.
* The `words.txt` file for the "Words from dictionary" exercise mode.
* Optionally `Words_Creator.py` for the 'w' menu option.
* The `pyperclip` library might be required if not included in your Python distribution (`pip install pyperclip`).
* Optionally, if migrating from v2.x, you will also need `migrateTo3.py` initially (see Migration section).

## Migration from v2.x to v3.x

Version 3.x uses a new settings file format (`cwapu_settings.json`) and no longer uses the old `.pkl` files.

* To migrate your existing exercise statistics (like total calls, total correct, sessions count) from a v2.x installation, run the `migrateTo3.exe` (or `migrateTo3.py` if using source) utility **once**.
* This utility will read the old `.pkl` files and create/update the `cwapu_settings.json` file with your V2 statistics.
* After successful migration, you can safely **delete** all `.pkl` files from your CWapu directory. They are no longer needed.

## Configuration and Data Files

* `cwapu_settings.json`: Stores all user settings (speed, pitch, volume, timings, sample rate, waveform, language) and exercise statistics (Rxing progress, Counting exercise number). Automatically created/updated.
* `CWapu_Diary.txt`: A plain text file where detailed reports from Rxing and Counting exercises are appended. Automatically created.
* `words.txt`: The dictionary file used by the Rxing "Words from dictionary" mode. Must be UTF-8 encoded, one word per line.

## Resetting Progress

To reset your exercise statistics and settings to the defaults:

1.  Close CWapu.
2.  Delete the `cwapu_settings.json` file.
3.  Optionally, delete or rename `CWapu_Diary.txt` to clear the exercise log.
CWapu will recreate these files with default values on the next launch.

## Acknowledgements

* A special thanks to **Mr. Kevin Schmidt, W9CF** for the foundational module used to produce and play CW audio. Your work made this project possible!
* Thanks to **Mario, IZ4EKG** for precious testing and feedback.
* Thanks to **Piero Tofy** for providing the comprehensive Italian language dictionary used in `words.txt`.

## Contributing & Contact

If you have suggestions, find bugs, or want to contribute, feel free to open an issue or contact me.

73 de Gabe, IZ4APU
CW forever.