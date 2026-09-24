# CWapu, il rapporto storico in pagina HTML.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).
# 24/09/2026: estratto da cwapu.py e rifatto con il grafico, issue 8.

"""Scrive la pagina HTML del rapporto storico di un blocco di esercizi.

E' la forma che si legge con il lettore di schermo: intestazioni vere,
tabelle con le intestazioni di riga e di colonna, numeri arrotondati con la
virgola in italiano, e ogni cosa che il grafico dice con un colore detta
anche a parole, cioe' il livello di un carattere e se una variazione
migliora o peggiora. I numeri vengono dal modulo analisi, lo stesso del
grafico, e la pagina ne contiene sempre almeno quanto il grafico: le stesse
sezioni con gli stessi caratteri, e in fondo tutti i caratteri sbagliati,
non soltanto i primi dieci.

Fino al 24 settembre 2026 la pagina stava dentro cwapu.py, i numeri uscivano
con sedici cifre, i caratteri erano in ordine di errori e non di quanto li
si sbaglia davvero, e la tabella delle variazioni si chiudeva dopo la prima
riga, lasciando le altre fuori.
"""

import datetime as dt
import html

from . import analisi

STILE = """
        body { background-color: #1f1f1f; color: #f0f0f0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; line-height: 1.5; }
        main { max-width: 1100px; margin: auto; background-color: #2b2f36; padding: 20px 30px; border-radius: 8px; }
        h1, h2 { color: #56B4E9; }
        h1 { font-size: 1.9em; margin-bottom: 0.3em; }
        h2 { border-bottom: 2px solid #56B4E9; padding-bottom: 4px; margin-top: 1.8em; }
        table { border-collapse: collapse; width: 100%; margin: 12px 0 20px; }
        caption { text-align: left; color: #b8b8b8; padding-bottom: 6px; }
        th, td { border: 1px solid #4b5260; padding: 8px 10px; text-align: left; }
        thead th { background-color: #3a3f4b; }
        tbody th { font-weight: bold; }
        .tenue { color: #b8b8b8; }
"""


def scrivi_rapporto_html(percorso, attuali, precedenti, g_val, x_val, num_sessioni, _, lingua="it", categoria=""):
    """Scrive la pagina nel percorso dato. Gli errori di scrittura arrivano a chi chiama come OSError."""
    precedenti = precedenti if precedenti and precedenti.get("num_sessions_in_block", 0) > 0 else None

    def numero(valore, decimali=1, segno=False):
        return analisi.formatta(valore, decimali, lingua, segno)

    def esc(testo):
        return html.escape(str(testo))

    nomi_livelli = {
        "solido": _("solido"),
        "attenzione": _("da tenere d'occhio"),
        "debole": _("debole"),
        "molto_debole": _("molto debole"),
    }
    nomi_andamento = {"migliora": _("migliora"), "peggiora": _("peggiora"), "stabile": _("stabile")}

    def cella_colorata(testo, chiave):
        return f'<td style="color: {analisi.COLORI[chiave]};">{esc(testo)}</td>'

    titolo = _("CWapu - Rapporto storico") + (f", {categoria}" if categoria else "")
    righe = [
        "<!DOCTYPE html>",
        f'<html lang="{esc(str(lingua)[:2])}">',
        "<head>",
        '    <meta charset="UTF-8">',
        f"    <title>{esc(titolo)}</title>",
        "    <style>" + STILE + "    </style>",
        "</head>",
        "<body>",
        "<main>",
        f"<h1>{esc(titolo)}</h1>",
        "<p>"
        + esc(
            _("{quanti} esercizi, dal {inizio} al {fine}. G={g}, X={x}.").format(
                quanti=num_sessioni, inizio=analisi.formatta_data(attuali.get("primo_iso"), lingua), fine=analisi.formatta_data(attuali.get("ultimo_iso"), lingua), g=g_val, x=x_val
            )
        )
        + "</p>",
        '<p class="tenue">' + esc(_("Generato il {quando}.").format(quando=dt.datetime.now().strftime("%d/%m/%Y %H:%M" if str(lingua).startswith("it") else "%Y-%m-%d %H:%M"))) + "</p>",
    ]
    if precedenti:
        righe.append("<p>" + esc(_("Confronto con i {quanti} esercizi del blocco precedente.").format(quanti=precedenti["num_sessions_in_block"])) + "</p>")

    # La velocita'.
    righe.append("<h2>" + esc(_("Velocità, in parole al minuto")) + "</h2>")
    righe.append("<table>")
    intestazione = ["<thead><tr>", f'<th scope="col">{esc(_("Velocità"))}</th>', f'<th scope="col">{esc(_("Adesso"))}</th>']
    if precedenti:
        intestazione += [f'<th scope="col">{esc(_("Prima"))}</th>', f'<th scope="col">{esc(_("Variazione"))}</th>']
    righe.append("".join(intestazione) + "</tr></thead>")
    righe.append("<tbody>")
    nomi_velocita = {"minima": _("Minima"), "media": _("Media"), "massima": _("Massima")}
    for voce in analisi.velocita(attuali, precedenti):
        riga = f'<tr><th scope="row">{esc(nomi_velocita[voce["nome"]])}</th><td>{numero(voce["attuale"])}</td>'
        if voce["precedente"] is not None:
            variazione = numero(voce["delta"], segno=True)
            if voce["percento"] is not None:
                variazione += f" ({numero(voce['percento'], segno=True)}%)"
            variazione += ", " + nomi_andamento[voce["andamento"]]
            riga += f"<td>{numero(voce['precedente'])}</td>" + cella_colorata(variazione, voce["andamento"])
        righe.append(riga + "</tr>")
    righe.append("</tbody>")
    righe.append("</table>")

    # Gli errori in generale.
    righe.append("<h2>" + esc(_("Errori in generale")) + "</h2>")
    tasso, errori, inviati = analisi.tasso_generale(attuali)
    righe.append("<p>" + esc(_("Tasso d'errore: {tasso}%, cioè {errori} caratteri sbagliati su {inviati} ricevuti.").format(tasso=numero(tasso), errori=errori, inviati=inviati)) + "</p>")
    if not errori:
        righe.append("<p>" + esc(_("Nessun errore in questo blocco.")) + "</p>")
    if precedenti:
        tasso_prima, _errori_prima, inviati_prima = analisi.tasso_generale(precedenti)
        delta = tasso - tasso_prima
        verso = analisi.andamento(delta, piu_e_meglio=False, stabile=0.1)
        testo = _("Prima: {tasso}%, con {inviati} caratteri ricevuti. Variazione: {delta} punti, {andamento}.").format(tasso=numero(tasso_prima), inviati=inviati_prima, delta=numero(delta, segno=True), andamento=nomi_andamento[verso])
        righe.append(f'<p style="color: {analisi.COLORI[verso]};">{esc(testo)}</p>')

    # I livelli, detti a parole prima delle tabelle che li usano.
    basso, medio, alto = (numero(s, 0) for s in analisi.SOGLIE)
    righe.append(
        "<p>"
        + esc(
            _("I livelli dei caratteri: sotto il {basso}%: solido; dal {basso} al {medio}%: da tenere d'occhio; dal {medio} al {alto}%: debole; oltre il {alto}%: molto debole.").format(basso=basso, medio=medio, alto=alto)
        )
        + "</p>"
    )

    def tabella_caratteri(elenco, didascalia):
        righe.append("<table>")
        righe.append(f"<caption>{esc(didascalia)}</caption>")
        righe.append(
            "<thead><tr>"
            + "".join(f'<th scope="col">{esc(t)}</th>' for t in (_("Carattere"), _("Errori su inviati"), _("Tasso"), _("Intervallo di Wilson"), _("Livello")))
            + "</tr></thead>"
        )
        righe.append("<tbody>")
        for c in elenco:
            righe.append(
                f'<tr><th scope="row">{esc(c["carattere"].upper())}</th>'
                f"<td>{esc(_('{errori} su {inviati}').format(errori=c['errori'], inviati=c['inviati']))}</td>"
                f"<td>{numero(c['tasso'])}%</td>"
                f"<td>{esc(_('da {inf} a {sup}%').format(inf=numero(c['inf']), sup=numero(c['sup'])))}</td>"
                + cella_colorata(nomi_livelli[c["livello"]], c["livello"])
                + "</tr>"
            )
        righe.append("</tbody>")
        righe.append("</table>")

    tutti_deboli = analisi.deboli(attuali)
    primi_deboli = tutti_deboli[: analisi.QUANTI]
    righe.append("<h2>" + esc(_("Punti deboli: i caratteri che sbagli di più, di sicuro")) + "</h2>")
    if primi_deboli:
        tabella_caratteri(
            primi_deboli,
            _("I {quanti} caratteri con il limite basso dell'intervallo di Wilson più alto, cioè quelli che di sicuro sbagli di più, fra quelli mandati almeno {minimo} volte.").format(
                quanti=len(primi_deboli), minimo=analisi.MINIMO_INVIATI_DEBOLI
            ),
        )
    else:
        righe.append("<p>" + esc(_("Nessun carattere sbagliato abbastanza volte da giudicarlo.")) + "</p>")

    solidi = analisi.solidi(attuali)
    righe.append("<h2>" + esc(_("Punti di forza: i caratteri che sbagli di meno, di sicuro")) + "</h2>")
    if solidi:
        tabella_caratteri(
            solidi,
            _("I {quanti} caratteri con il limite alto dell'intervallo di Wilson più basso, cioè quelli che di sicuro sbagli poco, fra quelli mandati almeno {minimo} volte e fuori dai primi punti deboli.").format(
                quanti=len(solidi), minimo=analisi.MINIMO_INVIATI_SOLIDI
            ),
        )
    else:
        righe.append("<p>" + esc(_("Nessun carattere mandato abbastanza volte da giudicarlo.")) + "</p>")

    if precedenti:
        righe.append("<h2>" + esc(_("Com'è cambiato rispetto al blocco precedente")) + "</h2>")
        variazioni = analisi.variazioni(attuali, precedenti, primi_deboli)
        if variazioni:
            righe.append("<table>")
            righe.append("<caption>" + esc(_("Il tasso d'errore dei punti deboli, adesso e nel blocco precedente, e la differenza in punti.")) + "</caption>")
            righe.append("<thead><tr>" + "".join(f'<th scope="col">{esc(t)}</th>' for t in (_("Carattere"), _("Adesso"), _("Prima"), _("Variazione"))) + "</tr></thead>")
            righe.append("<tbody>")
            for v in variazioni:
                adesso, prima = v["attuale"], v["precedente"]
                righe.append(
                    f'<tr><th scope="row">{esc(v["carattere"].upper())}</th>'
                    f"<td>{esc(_('{tasso}%, {errori} su {inviati}').format(tasso=numero(adesso['tasso']), errori=adesso['errori'], inviati=adesso['inviati']))}</td>"
                    f"<td>{esc(_('{tasso}%, {errori} su {inviati}').format(tasso=numero(prima['tasso']), errori=prima['errori'], inviati=prima['inviati']))}</td>"
                    + cella_colorata(_("{delta} punti, {andamento}").format(delta=numero(v["delta"], segno=True), andamento=nomi_andamento[v["andamento"]]), v["andamento"])
                    + "</tr>"
                )
            righe.append("</tbody>")
            righe.append("</table>")
        else:
            righe.append("<p>" + esc(_("Nessuno dei punti deboli era stato mandato nel blocco precedente.")) + "</p>")

    # Tutti i caratteri sbagliati, per chi vuole il quadro intero: il grafico
    # si ferma ai primi, la pagina no.
    if len(tutti_deboli) > len(primi_deboli):
        righe.append("<h2>" + esc(_("Tutti i caratteri sbagliati")) + "</h2>")
        tabella_caratteri(tutti_deboli, _("Dal più debole al più solido, in ordine dal limite basso dell'intervallo di Wilson."))
    pochi = analisi.pochi(attuali)
    if pochi:
        elenco = ", ".join(_("{carattere}, {errori} su {inviati}").format(carattere=c["carattere"].upper(), errori=c["errori"], inviati=c["inviati"]) for c in pochi)
        righe.append("<p>" + esc(_("Sbagliati ma mandati meno di {minimo} volte, troppo poche per giudicarli: {elenco}.").format(minimo=analisi.MINIMO_INVIATI_DEBOLI, elenco=elenco)) + "</p>")

    righe += ["</main>", "</body>", "</html>", ""]
    with open(percorso, "w", encoding="utf-8") as f:
        f.write("\n".join(righe))
