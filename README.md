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
    *   **Multi-language Support:** English and Italian. The language is chosen on first launch and stored in `selected_language.json`; delete that file to be asked again.

## Requirements & Setup

**Running from Source Code (`cwapu.py`):**

*   Python 3.x.
*   Required libraries: `pynput`, `pyperclip`, plus the audio stack used by GBUtils (`sounddevice`, `numpy`, `scipy`). Statistics also need `pandas` and `matplotlib`, loaded only when you open them.
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
*   `Manuale_CWapu.html`: The full manual, in Italian.

All of these live next to the program, never in the directory you happened to launch it from.

## Acknowledgements

*   **Mr. Kevin Schmidt, W9CF** for the foundational CW audio module and inspiration from `cwsim`.
*   **Mario, IZ4EKG** for testing and feedback.
*   **Stefano, IK4UXA** for extensive testing and valuable feedback on compiled versions.
*   **Piero Tofy** for the Italian dictionary.
*   **Salvatore, IK1OJM** for high speed testing.

73 de Gabe, IZ4APU
CW forever.