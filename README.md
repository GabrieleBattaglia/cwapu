# CWapu v5.0.0 by Gabriele Battaglia (IZ4APU) and Gemini 3 Pro

A collection of command-line tools and exercises designed to help amateur radio operators improve their skills in receiving and sending Morse Code (CW).

## Features

CWapu offers several modes to practice and utilize CW:

1.  **Receiving Exercise (Rxing - `r`):**
    *   **New in v5.0! Contest Mode:** A dedicated simulation of a contest exchange (Call + 5NN + Serial) featuring:
        *   **Dynamic realism:** Random pitch and speed variations for each QSO.
        *   **Smart Error Handling:** The system gives granular feedback (`CALL?`, `NR?`, `?`) based on your specific mistake.
        *   **Keyboard Shortcuts:** Real-time speed adjustment (`PgUp`/`PgDn`), repetitions (`F5` Call, `F6` Serial, `F7` All), and quick edit (`Alt+W`).
        *   **Real Callsigns:** Utilizes the `MASTER.SCP` database to generate realistic callsigns (50% probability).
        *   **Detailed Stats:** Tracks accuracy for both Callsigns and Serial numbers separately.
    *   **Standard Modes:** Practice receiving randomly generated pseudo-callsigns, words, or character groups.
    *   **Categories:** Organized into groups: Words, Characters (Letters, Numbers, Symbols, Mixed), and QRZ/Contest.
    *   **Adaptive Speed:** Option to automatically increase/decrease WPM based on your accuracy.
    *   **Reporting:** Detailed session reports saved to `CWapu_Diary.txt` and comprehensive historical statistics tracked in `cwapu_settings.json` (broken down by category: Words, Chars, QRZ).

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
    *   **Multi-language Support (`z`):** Switch between English and Italian on the fly.

## Requirements & Setup

**Running from Source Code (`cwapu.py`):**

*   Python 3.x.
*   Required libraries: `pynput`, `pyperclip` (install via `pip install pynput pyperclip`).
*   **Essential Files:**
    *   `cwapu.py`: The main application.
    *   `GBUtils.py`: Helper module.
    *   `MASTER.SCP`: Database of real callsigns (for Contest mode).
    *   `words.txt`: Dictionary for word exercises.
    *   `locales/`: Folder containing translation files.

## Configuration and Data Files

*   `cwapu_settings.json`: Stores user settings and historical statistics.
*   `CWapu_Diary.txt`: Plain text log of all exercise sessions.
*   `MASTER.SCP`: Standard contest callsign database file.

## Acknowledgements

*   **Mr. Kevin Schmidt, W9CF** for the foundational CW audio module and inspiration from `cwsim`.
*   **Mario, IZ4EKG** for testing and feedback.
*   **Piero Tofy** for the Italian dictionary.

73 de Gabe, IZ4APU
CW forever.