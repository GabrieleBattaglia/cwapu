# CWapu, il report storico in forma di grafico.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' UltraCode).
# 06/09/2026: estratto da cwapu.py, dove occupava un ottavo dell'applicazione.
# 24/09/2026: rifatto con ClaudIA (Claude Opus 5.5, modalita' auto), issue 8.

"""Disegna in un file SVG le statistiche del blocco di esercizi appena chiuso.

Sono le stesse informazioni della pagina HTML, calcolate dallo stesso modulo
analisi, messe in forma di grafico per chi le legge con gli occhi. Chi usa un
lettore di schermo non perde niente restando sulla pagina.

Lo scopo e' il colpo d'occhio: dove sei forte, dove sei fragile, e come e'
cambiato rispetto al blocco precedente. Per questo ogni carattere si
disegna con il suo intervallo di Wilson, una barra che dice fra quanto e
quanto lo sbagli davvero, e un punto sul valore misurato; il colore dice il
livello con soglie fisse, e le variazioni portano anche una freccia, cosi'
il colore non e' mai l'unico segnale. Fino al restyling del 24 settembre
2026 le etichette della velocita' minima e massima erano scambiate, i
numeri uscivano con sedici cifre, i colori dei caratteri seguivano la
posizione nell'elenco invece del valore, e l'ordine era per numero di
errori, che mette in testa i caratteri mandati piu' spesso invece dei piu'
deboli.

matplotlib si importa dentro la funzione: e' pesante e serve soltanto qui, e
un utente che non generi mai un rapporto grafico non deve pagarne il costo.
La funzione di traduzione arriva come parametro, come per timeline, cosi' il
modulo non dipende da chi lo chiama.
"""

import datetime as dt
import math

from . import analisi

SFONDO = "#1f1f1f"
PANNELLO = "#2b2f36"
TESTO = "#f0f0f0"
TENUE = "#b8b8b8"


def freccia(delta, andamento):
    """Il segno che accompagna una variazione: su, giu' o uguale."""
    if andamento == "stabile":
        return "="
    return "▲" if delta > 0 else "▼"


def crea_report_grafico(current_aggregates, previous_aggregates, g_val, x_val, num_sessions_in_report, output_filename, _, lang="en", categoria=""):
    """Crea il rapporto grafico del blocco e lo salva come SVG."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import Patch
    except ImportError as e_import:
        print(_("matplotlib non trovato, il report grafico non si genera: {errore}").format(errore=e_import))
        return
    except Exception as e_import:  # noqa: BLE001 -- matplotlib puo' fallire in molti modi diversi
        print(_("Errore durante l'importazione di matplotlib: {errore}").format(errore=e_import))
        return

    def numero(valore, decimali=1, segno=False):
        return analisi.formatta(valore, decimali, lang, segno)

    attuali = current_aggregates
    precedenti = previous_aggregates if previous_aggregates and previous_aggregates.get("num_sessions_in_block", 0) > 0 else None
    velocita = analisi.velocita(attuali, precedenti)
    deboli = analisi.deboli(attuali, analisi.QUANTI)
    solidi = analisi.solidi(attuali)
    variazioni = analisi.variazioni(attuali, precedenti, deboli) if precedenti else []

    sezioni = [("intestazione", 0.9), ("velocita", 2.4), ("generale", 1.4)]
    if deboli:
        sezioni.append(("deboli", 1.0 + 0.42 * len(deboli)))
    if solidi:
        sezioni.append(("solidi", 1.0 + 0.42 * len(solidi)))
    if variazioni:
        sezioni.append(("variazioni", 1.2 + 0.42 * len(variazioni)))
    sezioni.append(("legenda", 0.8))
    plt.style.use("dark_background")
    fig, assi = plt.subplots(
        len(sezioni), 1, figsize=(11, 1.0 + sum(h for _nome, h in sezioni)), gridspec_kw={"height_ratios": [h for _nome, h in sezioni]}, layout="constrained"
    )
    fig.patch.set_facecolor(SFONDO)
    pannelli = dict(zip((nome for nome, _h in sezioni), assi, strict=True))
    titolo = _("CWapu - Rapporto storico") + (f", {categoria}" if categoria else "")
    fig.suptitle(titolo, color=TESTO, fontsize=17, weight="bold")

    def prepara(ax, titolo_sezione):
        ax.set_facecolor(PANNELLO)
        ax.set_title(titolo_sezione, loc="left", color=TESTO, fontsize=13, weight="bold", pad=10)
        for lato in ("top", "right", "left"):
            ax.spines[lato].set_visible(False)
        ax.spines["bottom"].set_color(TENUE)
        ax.tick_params(axis="x", colors=TENUE, labelsize=9)
        ax.tick_params(axis="y", colors=TESTO, labelsize=11, length=0)

    # L'intestazione: quanti esercizi, quali giorni, con quali G e X.
    ax = pannelli["intestazione"]
    ax.axis("off")
    righe = [
        _("{quanti} esercizi, dal {inizio} al {fine}. G={g}, X={x}.").format(
            quanti=num_sessions_in_report, inizio=analisi.formatta_data(attuali.get("primo_iso"), lang), fine=analisi.formatta_data(attuali.get("ultimo_iso"), lang), g=g_val, x=x_val
        ),
        _("Generato il {quando}.").format(quando=dt.datetime.now().strftime("%d/%m/%Y %H:%M" if str(lang).startswith("it") else "%Y-%m-%d %H:%M")),
    ]
    if precedenti:
        righe.append(_("Confronto con i {quanti} esercizi del blocco precedente.").format(quanti=precedenti["num_sessions_in_block"]))
    for indice, riga in enumerate(righe):
        ax.text(0.5, 0.95 - indice * 0.33, riga, color=TESTO if not indice else TENUE, ha="center", va="top", fontsize=12 if not indice else 10, transform=ax.transAxes)

    # La velocita': adesso e prima, con la variazione a destra.
    ax = pannelli["velocita"]
    prepara(ax, _("Velocità, in parole al minuto"))
    nomi = {"minima": _("Minima"), "media": _("Media"), "massima": _("Massima")}
    massimo = max([v["attuale"] for v in velocita] + [v["precedente"] or 0 for v in velocita] + [10])
    limite = math.ceil(massimo * 1.7 / 10) * 10
    ax.set_xlim(0, limite)
    ax.set_ylim(len(velocita) - 0.4, -0.6)
    ax.set_yticks(range(len(velocita)))
    ax.set_yticklabels([nomi[v["nome"]] for v in velocita])
    alto = 0.34
    for indice, voce in enumerate(velocita):
        y_adesso = indice - (alto / 2 if precedenti else 0)
        ax.barh(y_adesso, voce["attuale"], height=alto, color=analisi.COLORI["attuale"], zorder=3)
        # Adesso e prima si dicono accanto al valore, non in una legenda che
        # finirebbe sopra le variazioni.
        valore_adesso = _("adesso {valore}").format(valore=numero(voce["attuale"])) if precedenti else numero(voce["attuale"])
        ax.text(voce["attuale"] + limite * 0.01, y_adesso, valore_adesso, color=TESTO, va="center", fontsize=10, weight="bold")
        if voce["precedente"] is not None:
            y_prima = indice + alto / 2
            ax.barh(y_prima, voce["precedente"], height=alto, color=analisi.COLORI["precedente"], zorder=2)
            ax.text(voce["precedente"] + limite * 0.01, y_prima, _("prima {valore}").format(valore=numero(voce["precedente"])), color=TENUE, va="center", fontsize=9)
            variazione = f"{freccia(voce['delta'], voce['andamento'])} {numero(voce['delta'], segno=True)}"
            if voce["percento"] is not None:
                variazione += f" ({numero(voce['percento'], segno=True)}%)"
            ax.text(limite * 0.98, indice, variazione, color=analisi.COLORI[voce["andamento"]], ha="right", va="center", fontsize=11, weight="bold")

    # Gli errori in generale, in parole.
    ax = pannelli["generale"]
    ax.axis("off")
    ax.set_title(_("Errori in generale"), loc="left", color=TESTO, fontsize=13, weight="bold", pad=10)
    tasso, errori, inviati = analisi.tasso_generale(attuali)
    righe = [(_("Tasso d'errore: {tasso}%, cioè {errori} caratteri sbagliati su {inviati} ricevuti.").format(tasso=numero(tasso), errori=errori, inviati=inviati), TESTO)]
    if not errori:
        righe.append((_("Nessun errore in questo blocco."), analisi.COLORI["solido"]))
    if precedenti:
        tasso_prima, _errori_prima, inviati_prima = analisi.tasso_generale(precedenti)
        delta = tasso - tasso_prima
        verso = analisi.andamento(delta, piu_e_meglio=False, stabile=0.1)
        righe.append(
            (
                _("Prima: {tasso}%, con {inviati} caratteri ricevuti. Variazione: {freccia} {delta} punti.").format(tasso=numero(tasso_prima), inviati=inviati_prima, freccia=freccia(delta, verso), delta=numero(delta, segno=True)),
                analisi.COLORI[verso],
            )
        )
    for indice, (riga, colore) in enumerate(righe):
        ax.text(0.0, 0.85 - indice * 0.36, riga, color=colore, ha="left", va="top", fontsize=12, transform=ax.transAxes)

    def disegna_caratteri(ax, elenco, titolo_sezione):
        """Un carattere per riga: la barra e' l'intervallo di Wilson, il punto il valore misurato."""
        prepara(ax, titolo_sezione)
        massimo = max([c["sup"] for c in elenco] + [10.0])
        limite = massimo * 1.9
        ax.set_xlim(0, limite)
        ax.set_ylim(len(elenco) - 0.4, -0.6)
        ax.set_yticks(range(len(elenco)))
        ax.set_yticklabels([c["carattere"].upper() for c in elenco], weight="bold")
        for soglia in analisi.SOGLIE:
            if soglia < limite:
                ax.axvline(soglia, color=TENUE, linestyle=":", linewidth=0.8, zorder=1)
                ax.text(soglia, -0.55, f"{numero(soglia, 0)}%", color=TENUE, ha="center", va="bottom", fontsize=8)
        for indice, c in enumerate(elenco):
            colore = analisi.COLORI[c["livello"]]
            ax.hlines(indice, c["inf"], c["sup"], color=colore, linewidth=9, zorder=2)
            ax.plot(c["tasso"], indice, "o", color=TESTO, markeredgecolor=SFONDO, markersize=7, zorder=3)
            etichetta = _("{errori} su {inviati}, {tasso}% [{inf}-{sup}]").format(errori=c["errori"], inviati=c["inviati"], tasso=numero(c["tasso"]), inf=numero(c["inf"]), sup=numero(c["sup"]))
            ax.text(c["sup"] + limite * 0.012, indice, etichetta, color=TESTO, va="center", fontsize=9)
        ax.set_xlabel(_("Tasso d'errore in percento: il punto è il valore misurato, la barra l'intervallo di Wilson."), color=TENUE, fontsize=9)

    if deboli:
        disegna_caratteri(pannelli["deboli"], deboli, _("Punti deboli: i caratteri che sbagli di più, di sicuro"))
    if solidi:
        disegna_caratteri(pannelli["solidi"], solidi, _("Punti di forza: i caratteri che sbagli di meno, di sicuro"))

    # Le variazioni dei punti deboli rispetto al blocco precedente.
    if variazioni:
        ax = pannelli["variazioni"]
        prepara(ax, _("Com'è cambiato rispetto al blocco precedente"))
        massimo = max([abs(v["delta"]) for v in variazioni] + [2.0])
        limite = massimo * 1.6
        ax.set_xlim(-limite, limite)
        ax.set_ylim(len(variazioni) - 0.4, -0.6)
        ax.set_yticks(range(len(variazioni)))
        ax.set_yticklabels([v["carattere"].upper() for v in variazioni], weight="bold")
        ax.axvline(0, color=TENUE, linewidth=1, zorder=1)
        for indice, v in enumerate(variazioni):
            colore = analisi.COLORI[v["andamento"]]
            ax.barh(indice, v["delta"], height=0.55, color=colore, zorder=2)
            testo = f"{freccia(v['delta'], v['andamento'])} {numero(v['delta'], segno=True)}"
            if v["delta"] < 0:
                ax.text(v["delta"] - limite * 0.02, indice, testo, color=TESTO, ha="right", va="center", fontsize=9)
            else:
                ax.text(v["delta"] + limite * 0.02, indice, testo, color=TESTO, ha="left", va="center", fontsize=9)
        ax.set_xlabel(_("Variazione del tasso d'errore, in punti: a sinistra migliora, a destra peggiora."), color=TENUE, fontsize=9)

    # La legenda dei colori, detta anche a parole.
    ax = pannelli["legenda"]
    ax.axis("off")
    basso, medio, alto_soglia = (numero(s, 0) for s in analisi.SOGLIE)
    voci = [
        Patch(color=analisi.COLORI["solido"], label=_("sotto il {soglia}%: solido").format(soglia=basso)),
        Patch(color=analisi.COLORI["attenzione"], label=_("dal {da} al {a}%: da tenere d'occhio").format(da=basso, a=medio)),
        Patch(color=analisi.COLORI["debole"], label=_("dal {da} al {a}%: debole").format(da=medio, a=alto_soglia)),
        Patch(color=analisi.COLORI["molto_debole"], label=_("oltre il {soglia}%: molto debole").format(soglia=alto_soglia)),
    ]
    ax.legend(handles=voci, loc="center", ncol=2, fontsize=10, facecolor=PANNELLO, edgecolor=TENUE, labelcolor=TESTO, title=_("Colori dei caratteri"), title_fontsize=10)

    try:
        plt.savefig(output_filename, format="svg", facecolor=SFONDO)
    except (OSError, ValueError) as e:
        print(_("Errore nel salvataggio del file grafico: {errore}").format(errore=e))
    finally:
        plt.close(fig)
