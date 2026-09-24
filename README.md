# CWapu v6.0.0 by Gabriele Battaglia (IZ4APU) and ClaudIA

A collection of command-line tools and exercises designed to help amateur radio operators improve their skills in receiving and sending Morse Code (CW).

## Features

CWapu offers several modes to practice and utilize CW:

0.  **Built-in Manual (`g`):**
    *   Opens the full manual in your browser. It is written in Italian only; modern browsers translate it in one command, and the page is plain HTML precisely so that automatic translation works well on it.

1.  **Receiving Exercise (Rxing - `r`):**
    *   **Contest Mode:** A dedicated simulation of a contest exchange (Call + 5NN + Serial) featuring:
        *   **Dynamic realism:** Random pitch and speed variations for each QSO.
        *   **Smart Error Handling:** The system gives granular feedback (`CALL?`, `NR?`, `?`) based on your specific mistake.
        *   **Keyboard Shortcuts:** Real-time speed adjustment (`F10` faster, `F9` slower), repetitions (`F5` Call, `F6` Serial, `F7` All), abort with `F8` (NIL), and quick edit (`Alt+W`).
        *   **Real Callsigns:** Utilizes the `MASTER.SCP` database to generate realistic callsigns.
        *   **Detailed Stats:** Tracks accuracy for both Callsigns and Serial numbers separately.
    *   **Standard Modes:** Practice receiving randomly generated pseudo-callsigns, words, or character groups.
    *   **Categories:** Organized into groups: Words, Characters (Letters, Numbers, Symbols, Mixed), and QRZ/Contest.
    *   **Adaptive Speed:** Option to automatically increase/decrease WPM based on your accuracy, up to 120 WPM.
    *   **Reporting:** Detailed session reports saved to `CWapu_Diary.txt` and comprehensive historical statistics tracked in `cwapu_settings.json` (broken down by category: Words, Chars, QRZ, Contest).

2.  **Transmission Practice Aid (Txing - `t`):**
    *   Generates random callsign-like structures and sequential numbers for sending practice with your own key/paddle.

3.  **Counting Exercise (Counting - `c`):**
    *   A tool to practice item recognition from external sources.

4.  **Keyboard CW (Keyboard - `k`):**
    *   Type text directly into the console to hear it played as CW.
    *   Supports real-time adjustment of WPM, pitch, Farnsworth timing, volume, audio sample rate, and waveform.
    *   Save generated audio to `.wav` files.

5.  **Clipboard Playback (`l`):**
    *   Instantly plays text from the system clipboard.

6.  **Utilities:**
    *   **Dictionary Word Filter/Creator (`w`):** Process word lists.
    *   **Settings Management:** All settings and stats are saved in `cwapu_settings.json`.
    *   **Multi-language Support:** English and Italian. The language is chosen on first launch and stored in `selected_language.json`; delete that file to be asked again.

## Requirements & Setup

**Running from Source Code (`cwapu.py`):**

*   Python 3.x.
*   Required libraries: `pip install -r requirements.txt`. The file lists every package and says what each one is for. `pandas` and `matplotlib` are needed only by the statistics, and are loaded only when you open them. Contributors will also want `requirements-dev.txt`.
*   `GBUtils` is not on PyPI: clone https://github.com/GabrieleBattaglia/GBUtils and make it reachable from Python.
*   **Project layout** (since version 8.0.0):
    *   `cwapu.py`: The main application, the only one to launch.
    *   `modules/`: The contest engine, the historical reports, the Wilson interval and the dictionary builder.
    *   `resources/`: What ships with the program: `words.txt`, the dictionary for word exercises; `MASTER.SCP`, the database of real callsigns; `Manuale_CWapu.html`, the full manual in Italian; `locales/`, the translations.
    *   `tools/`: `zip_maker.py`, which builds the release archive, and `babel.cfg`, for extracting the strings to translate.
    *   `docs/`: The changelog.
    *   `tests/`: The automated tests, run with `python -m pytest`.

## Configuration and Data Files

CWapu writes its files into subfolders next to the program, never into the directory you happened to launch it from:

*   `data/`: `cwapu_settings.json`, with user settings and historical statistics; `CWapu_Diary.txt`, the plain text log of all exercise sessions; `selected_language.json`; and your own `words.txt`, if you want a personal dictionary.
*   `reports/`: The historical report pages and the timeline reports.
*   `graphics/`: The historical report charts.
*   `audio/`: The WAV files saved with `.sv`.

The compiled version is a folder, with `cwapu.exe` next to `_internal`, where libraries and resources live. When upgrading from version 7, CWapu moves the old files into these subfolders by itself on first launch.

## Acknowledgements

*   **Mr. Kevin Schmidt, W9CF** for the foundational CW audio module and inspiration from `cwsim`.
*   **Mario, IZ4EKG** for testing and feedback.
*   **Stefano, IK4UXA** for extensive testing and valuable feedback on compiled versions.
*   **Piero Tofy** for the Italian dictionary.
*   **Salvatore, IK1OJM** for high speed testing.

73 de Gabe, IZ4APU
CW forever.