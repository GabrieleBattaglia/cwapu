# CWapu, utilita': prepara l'archivio per la distribuzione.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' auto).
# 04/09/2026: primo chiamante, il mestiere sta in crea_archivio_release di GBUtils V104.
# 24/09/2026: con la 8.0.0 sta in tools e comprime la cartella dist\cwapu.

"""Comprime il risultato di PyInstaller in un solo archivio.

Tutto il mestiere sta in GBUtils, cosi' la regola sulle esclusioni e' una
sola per tutti i progetti. Qui restano soltanto i nomi di CWapu.

Dalla 8.0.0, issue 21, CWapu si compila a cartella: in dist\\cwapu ci sono
cwapu.exe e _internal, dove stanno le librerie e le risorse, cioe'
words.txt, MASTER.SCP, il manuale e i cataloghi delle lingue sotto
resources. L'archivio li mette alla radice, come perform_update vuole, e
scrive il manifesto di _internal che serve a pulisci_residui.

Provando l'eseguibile prima di comprimere, accanto a lui nascono le
cartelle dei dati di chi ha compilato: data con impostazioni, diario,
lingua scelta e dizionario personale, reports, graphics e audio. Restano
fuori tutte, insieme alla copia del manuale che CWapu tiene accanto
all'eseguibile e che rifa' da se' al primo avvio.

Lo script sta in tools, e crea_archivio_release risolve i percorsi
relativi rispetto a chi la chiama: per questo dist e l'archivio si
indicano a partire dalla cartella del progetto, un livello sopra.
Si lancia dalla cartella del progetto con
    python tools\\zip_maker.py
"""

import os
import sys

from GBUtils import crea_archivio_release

PROGETTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUORI = [
    "data/",
    "reports/",
    "graphics/",
    "audio/",
    "Manuale_CWapu.html",
]


def main():
    try:
        crea_archivio_release(
            "cwapu",
            cartella_dist=os.path.join(PROGETTO, "dist", "cwapu"),
            archivio=os.path.join(PROGETTO, "cwapu.zip"),
            escludi=FUORI,
        )
    except (FileNotFoundError, OSError) as e:
        print(f"Archivio non creato: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
