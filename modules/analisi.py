# CWapu, l'analisi comune al rapporto storico in pagina e in grafico.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).
# 24/09/2026: nato con il restyling del rapporto grafico, issue 8.

"""Cio' che il rapporto storico dice, calcolato una volta sola.

La pagina HTML e il grafico SVG raccontano lo stesso blocco di esercizi, e
la regola della issue 8 vuole che il grafico non contenga niente che la
pagina non abbia: chi legge con il lettore di schermo non deve perdere
niente. Per questo i numeri li calcola questo modulo, e le due forme li
mettono in pagina ciascuna a modo suo.

I caratteri deboli si ordinano per il limite basso dell'intervallo di
Wilson, cioe' per quanto li si sbaglia di sicuro: un carattere mandato poche
volte non sale in cima per un errore fortunato. I solidi, al contrario, per
il limite alto, cioe' per quanto poco li si sbaglia di sicuro. Il colore e
il livello di un carattere dipendono dal suo tasso d'errore con soglie
fisse, non dalla posizione nell'elenco.
"""

from .wilson import wilson_score_lower_bound, wilson_score_upper_bound

# Le soglie del tasso d'errore di un carattere, in percento: sotto la prima
# e' solido, poi da tenere d'occhio, poi debole, oltre l'ultima molto debole.
SOGLIE = (5.0, 15.0, 30.0)
LIVELLI = ("solido", "attenzione", "debole", "molto_debole")
# Quanti caratteri mostra ogni elenco del grafico, e quante volte un
# carattere deve essere stato mandato per contare fra i solidi.
QUANTI = 10
MINIMO_INVIATI_SOLIDI = 20
# Sotto questi invii un carattere non si giudica debole: sbagliato una volta
# su una, avrebbe un limite basso di Wilson del 20 per cento e salirebbe in
# cima all'elenco per un errore solo.
MINIMO_INVIATI_DEBOLI = 10
# Sotto questa variazione, in punti percentuali, un carattere e' stabile.
STABILE = 1.0
# La tavolozza, uguale nel grafico e nella pagina. Blu per cio' che va
# bene o migliora, arancio e vermiglio per cio' che va male o peggiora:
# e' la tavolozza di Okabe e Ito, che si distingue anche con il daltonismo
# piu' diffuso, al posto della coppia rosso e verde.
COLORI = {
    "solido": "#56B4E9",
    "attenzione": "#F0E442",
    "debole": "#E69F00",
    "molto_debole": "#D55E00",
    "migliora": "#56B4E9",
    "peggiora": "#E69F00",
    "stabile": "#BBBBBB",
    "attuale": "#56B4E9",
    "precedente": "#8C8C8C",
}


def formatta(valore, decimali=1, lingua="it", segno=False):
    """Un numero con i decimali chiesti e la virgola in italiano, il punto nelle altre lingue.

    Con segno, il piu' davanti ai positivi. Lo zero arrotondato non porta mai
    il meno davanti, che letto ad alta voce direbbe una variazione che non c'e'.
    """
    testo = f"{valore:+.{decimali}f}" if segno else f"{valore:.{decimali}f}"
    if float(testo) == 0:
        testo = f"{0:.{decimali}f}"
    if str(lingua).lower().startswith("it"):
        testo = testo.replace(".", ",")
    return testo


def formatta_data(iso, lingua="it"):
    """Il giorno di un istante ISO, come giorno, mese e anno in italiano e in forma ISO nelle altre lingue."""
    import datetime as dt

    try:
        giorno = dt.datetime.fromisoformat(str(iso))
    except (TypeError, ValueError):
        return "?"
    return giorno.strftime("%d/%m/%Y") if str(lingua).lower().startswith("it") else giorno.strftime("%Y-%m-%d")


def livello(tasso):
    """Il livello di un carattere dal suo tasso d'errore in percento."""
    for soglia, nome in zip(SOGLIE, LIVELLI, strict=False):
        if tasso < soglia:
            return nome
    return LIVELLI[-1]


def caratteri(aggregati):
    """Ogni carattere mandato nel blocco, con errori, invii, tasso e intervallo di Wilson in percento."""
    inviati_per_carattere = aggregati.get("aggregated_sent_chars_detail", {}) or {}
    errori_per_carattere = aggregati.get("aggregated_errors_detail", {}) or {}
    risultato = []
    for carattere in sorted(set(inviati_per_carattere) | set(errori_per_carattere)):
        inviati = inviati_per_carattere.get(carattere, 0)
        if inviati <= 0:
            # Un errore su un carattere mai mandato non ha un tasso: e' un
            # dato sporco, e non entra in nessun elenco.
            continue
        errori = min(errori_per_carattere.get(carattere, 0), inviati)
        tasso = errori / inviati * 100
        risultato.append(
            {
                "carattere": carattere,
                "errori": errori,
                "inviati": inviati,
                "tasso": tasso,
                "inf": wilson_score_lower_bound(errori, inviati) * 100,
                "sup": wilson_score_upper_bound(errori, inviati) * 100,
                "livello": livello(tasso),
            }
        )
    return risultato


def deboli(aggregati, quanti=None, minimo_inviati=MINIMO_INVIATI_DEBOLI):
    """I caratteri sbagliati almeno una volta, dal piu' sicuramente debole: limite basso di Wilson decrescente.

    Con quanti None li restituisce tutti, come fa la pagina; il grafico ne
    chiede QUANTI. Quelli mandati meno di minimo_inviati volte restano fuori,
    e li elenca pochi.
    """
    elenco = [c for c in caratteri(aggregati) if c["errori"] > 0 and c["inviati"] >= minimo_inviati]
    elenco.sort(key=lambda c: (-c["inf"], -c["tasso"], c["carattere"]))
    return elenco if quanti is None else elenco[:quanti]


def solidi(aggregati, quanti=QUANTI, minimo_inviati=MINIMO_INVIATI_SOLIDI):
    """I caratteri piu' sicuramente solidi: limite alto di Wilson crescente, fra quelli mandati abbastanza volte.

    Chi sta fra i primi QUANTI punti deboli non e' anche un punto di forza:
    quando quasi tutti i caratteri si sbagliano fra il dieci e il venti per
    cento, lo stesso carattere finirebbe in tutti e due gli elenchi.
    """
    esclusi = {c["carattere"] for c in deboli(aggregati, QUANTI)}
    elenco = [c for c in caratteri(aggregati) if c["inviati"] >= minimo_inviati and c["carattere"] not in esclusi]
    elenco.sort(key=lambda c: (c["sup"], c["tasso"], c["carattere"]))
    return elenco[:quanti]


def pochi(aggregati, minimo_inviati=MINIMO_INVIATI_DEBOLI):
    """I caratteri sbagliati almeno una volta ma mandati troppo poche volte per giudicarli."""
    return [c for c in caratteri(aggregati) if c["errori"] > 0 and c["inviati"] < minimo_inviati]


def andamento(delta, piu_e_meglio=True, stabile=STABILE):
    """migliora, peggiora o stabile, per una variazione e il verso in cui e' buona."""
    if abs(delta) <= stabile:
        return "stabile"
    migliora = delta > 0 if piu_e_meglio else delta < 0
    return "migliora" if migliora else "peggiora"


def variazioni(attuali, precedenti, elenco):
    """Per i caratteri dell'elenco, il tasso d'errore di adesso, quello di prima e la differenza in punti.

    Un carattere che nel blocco precedente non era mai stato mandato non ha
    un tasso di prima, e resta fuori: una differenza da niente non dice niente.
    """
    prima = {c["carattere"]: c for c in caratteri(precedenti or {})}
    risultato = []
    for voce in elenco:
        vecchio = prima.get(voce["carattere"])
        if vecchio is None:
            continue
        delta = voce["tasso"] - vecchio["tasso"]
        risultato.append({"carattere": voce["carattere"], "attuale": voce, "precedente": vecchio, "delta": delta, "andamento": andamento(delta, piu_e_meglio=False)})
    return risultato


def tasso_generale(aggregati):
    """Il tasso d'errore di tutto il blocco in percento, con errori e caratteri."""
    inviati = aggregati.get("total_chars_sent_overall", 0) or 0
    errori = aggregati.get("total_errors_chars_overall", 0) or 0
    return (errori / inviati * 100 if inviati else 0.0), errori, inviati


def velocita(attuali, precedenti):
    """Le tre velocita' del blocco, minima, media e massima, con quelle di prima e la differenza."""
    voci = (("minima", "wpm_min_overall"), ("media", "wpm_avg_of_session_avgs"), ("massima", "wpm_max_overall"))
    risultato = []
    for nome, chiave in voci:
        adesso = float(attuali.get(chiave, 0) or 0)
        prima = float(precedenti.get(chiave, 0) or 0) if precedenti else None
        delta = None if prima is None else adesso - prima
        percento = delta / prima * 100 if prima else None
        risultato.append({"nome": nome, "attuale": adesso, "precedente": prima, "delta": delta, "percento": percento, "andamento": None if delta is None else andamento(delta, stabile=0.05)})
    return risultato
