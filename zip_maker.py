# CWapu, utilita': prepara l'archivio per la distribuzione.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' auto).
# 04/09/2026: primo chiamante, il mestiere sta in crea_archivio_release di GBUtils V104.

"""Comprime il risultato di PyInstaller in un solo archivio.

Tutto il mestiere sta in GBUtils, cosi' la regola sulle esclusioni e' una
sola per tutti i progetti. Qui restano soltanto i nomi di CWapu.

CWapu si compila in un file unico, quindi dentro dist c'e' soltanto
l'eseguibile: words.txt, MASTER.SCP e i cataloghi delle lingue viaggiano
dentro di lui e li trova resource_path passando da _MEIPASS.

Proprio per questo un words.txt accanto all'eseguibile e' il dizionario
personale di chi ha compilato, non quello di serie: CWapu prova prima
quello che sta accanto al programma e solo dopo ripiega sulla copia interna.
Va lasciato fuori, insieme al words_updated.txt che produce WordsCreator,
alle impostazioni e a tutti i rapporti che CWapu scrive.
"""

import sys

from GBUtils import crea_archivio_release

FUORI = [
    "cwapu_settings.json",
    "words.txt",
    "words_updated.txt",
    "cwapu_*.txt",
]


def main():
    try:
        crea_archivio_release("cwapu", cartella_dist="dist", escludi=FUORI)
    except (FileNotFoundError, OSError) as e:
        print(f"Archivio non creato: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
