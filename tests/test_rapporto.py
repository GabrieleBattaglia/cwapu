# Prove automatiche di CWapu, il rapporto storico in pagina e in grafico.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).
# Nate con il restyling del 24 settembre 2026, issue 8. Coprono i difetti che
# il grafico aveva: le etichette della velocita' minima e massima scambiate,
# i numeri con sedici cifre, i caratteri in ordine di errori invece che di
# quanto li si sbaglia davvero, i colori per posizione, e nella pagina la
# tabella delle variazioni che si chiudeva dopo la prima riga.

import html.parser
import os
import re
import sys

import pytest

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)

import cwapu  # noqa: E402
from modules import analisi  # noqa: E402
from modules.grafico import crea_report_grafico  # noqa: E402
from modules.rapporto import scrivi_rapporto_html  # noqa: E402


def aggregati(errori, inviati, **altro):
    """Un blocco con questi errori e invii per carattere."""
    base = {
        "num_sessions_in_block": 5,
        "wpm_min_overall": 14,
        "wpm_max_overall": 63,
        "wpm_avg_of_session_avgs": 44.52055952742684,
        "total_chars_sent_overall": sum(inviati.values()),
        "total_errors_chars_overall": sum(errori.values()),
        "aggregated_errors_detail": dict(errori),
        "aggregated_sent_chars_detail": dict(inviati),
        "primo_iso": "2026-03-23T10:00:00",
        "ultimo_iso": "2026-09-15T21:00:00",
    }
    base.update(altro)
    return base


# Dai dati veri di Gabriele: B e' sbagliata meno volte di 7, ma di piu' in proporzione.
ATTUALI = aggregati(
    {"7": 49, "b": 38, "h": 28, "a": 3, "t": 3, "e": 1, "x": 1},
    {"7": 149, "b": 80, "h": 90, "a": 93, "t": 82, "e": 1, "x": 3, "m": 120},
)
PRECEDENTI = aggregati({"7": 50, "b": 37, "a": 5}, {"7": 150, "b": 86, "a": 90}, num_sessions_in_block=4, wpm_min_overall=25, wpm_max_overall=64, wpm_avg_of_session_avgs=44.47797086568772)


class TestAnalisi:
    def test_i_numeri_si_arrotondano_con_la_virgola_in_italiano(self):
        assert analisi.formatta(16.085714285714285, 1, "it") == "16,1"
        assert analisi.formatta(16.085714285714285, 1, "en") == "16.1"
        assert analisi.formatta(4.5, 1, "it", segno=True) == "+4,5"

    def test_lo_zero_arrotondato_non_ha_il_meno(self):
        assert analisi.formatta(-0.04, 1, "it", segno=True) == "0,0"

    def test_i_livelli_seguono_le_soglie(self):
        assert [analisi.livello(t) for t in (0, 4.9, 5, 14.9, 15, 29.9, 30, 100)] == ["solido", "solido", "attenzione", "attenzione", "debole", "debole", "molto_debole", "molto_debole"]

    def test_i_deboli_sono_in_ordine_di_quanto_li_sbagli_di_sicuro(self):
        """B, 38 su 80, sta davanti a 7, 49 su 149: il vecchio grafico li
        metteva al contrario, perche' contava gli errori."""
        ordine = [c["carattere"] for c in analisi.deboli(ATTUALI)]
        assert ordine.index("b") < ordine.index("7")

    def test_un_carattere_mandato_poche_volte_non_si_giudica(self):
        """Sbagliata una volta su una, la E avrebbe il limite basso di Wilson
        al 20 per cento e salirebbe in cima."""
        assert "e" not in [c["carattere"] for c in analisi.deboli(ATTUALI)]
        assert [c["carattere"] for c in analisi.pochi(ATTUALI)] == ["e", "x"]

    def test_i_solidi_non_sono_anche_deboli(self):
        deboli = {c["carattere"] for c in analisi.deboli(ATTUALI, analisi.QUANTI)}
        solidi = analisi.solidi(ATTUALI)
        assert solidi
        assert not deboli & {c["carattere"] for c in solidi}

    def test_i_solidi_sono_in_ordine_dal_piu_sicuro(self):
        """Zero errori su 120 invii e' di sicuro piu' solido di zero su 40."""
        elenco = analisi.solidi(aggregati({}, {"k": 40, "m": 120}))
        assert [c["carattere"] for c in elenco] == ["m", "k"]

    def test_il_colore_segue_il_valore_non_la_posizione(self):
        for c in analisi.deboli(ATTUALI):
            assert c["livello"] == analisi.livello(c["tasso"])

    def test_la_velocita_e_minima_media_massima_con_i_valori_giusti(self):
        """Il vecchio grafico diceva Max 14 e Min 63."""
        voci = analisi.velocita(ATTUALI, PRECEDENTI)
        assert [v["nome"] for v in voci] == ["minima", "media", "massima"]
        assert (voci[0]["attuale"], voci[2]["attuale"]) == (14, 63)
        assert voci[0]["andamento"] == "peggiora"

    def test_le_variazioni_tengono_solo_chi_c_era_prima(self):
        variazioni = analisi.variazioni(ATTUALI, PRECEDENTI, analisi.deboli(ATTUALI))
        per_carattere = {v["carattere"]: v for v in variazioni}
        assert "h" not in per_carattere
        assert per_carattere["b"]["delta"] == pytest.approx(38 / 80 * 100 - 37 / 86 * 100)
        assert per_carattere["b"]["andamento"] == "peggiora"


class Struttura(html.parser.HTMLParser):
    """Controlla che ogni tag si chiuda nell'ordine in cui si e' aperto, e raccoglie il testo."""

    def __init__(self):
        super().__init__()
        self.aperti, self.errori, self.testo = [], [], []

    def handle_starttag(self, tag, attrs):
        if tag not in ("meta", "br"):
            self.aperti.append(tag)

    def handle_endtag(self, tag):
        if not self.aperti or self.aperti[-1] != tag:
            self.errori.append(tag)
        else:
            self.aperti.pop()

    def handle_data(self, data):
        self.testo.append(data)


def pagina(tmp_path, attuali, precedenti, lingua="it"):
    percorso = tmp_path / "rapporto.html"
    scrivi_rapporto_html(str(percorso), attuali, precedenti, 400, 3500, 5, cwapu._, lingua, "caratteri/misto")
    struttura = Struttura()
    struttura.feed(percorso.read_text(encoding="utf-8"))
    return struttura


class TestPagina:
    def test_i_tag_si_chiudono_tutti_e_in_ordine(self, tmp_path):
        """La tabella delle variazioni si chiudeva dopo la prima riga."""
        struttura = pagina(tmp_path, ATTUALI, PRECEDENTI)
        assert struttura.errori == []
        assert struttura.aperti == []

    def test_titolo_con_categoria_e_periodo(self, tmp_path):
        testo = " ".join(pagina(tmp_path, ATTUALI, PRECEDENTI).testo)
        assert "Rapporto storico, caratteri/misto" in testo
        assert "dal 23/03/2026 al 15/09/2026" in testo

    def test_nessun_numero_con_troppe_cifre(self, tmp_path):
        testo = " ".join(pagina(tmp_path, ATTUALI, PRECEDENTI).testo)
        assert not re.search(r"\d[.,]\d{3,}", testo), re.search(r"\d[.,]\d{3,}", testo)
        assert "44,5" in testo

    def test_i_livelli_e_gli_andamenti_si_dicono_a_parole(self, tmp_path):
        """Il colore non e' mai l'unico segnale."""
        testo = " ".join(pagina(tmp_path, ATTUALI, PRECEDENTI).testo)
        assert "molto debole" in testo
        assert "peggiora" in testo
        assert "Punti di forza" in testo

    def test_senza_blocco_precedente_niente_confronti(self, tmp_path):
        struttura = pagina(tmp_path, ATTUALI, None)
        testo = " ".join(struttura.testo)
        assert struttura.errori == []
        assert "rispetto al blocco precedente" not in testo
        assert "Prima" not in testo

    def test_senza_errori(self, tmp_path):
        vuoto = aggregati({}, {"a": 50, "b": 40})
        struttura = pagina(tmp_path, vuoto, None)
        assert struttura.errori == []
        assert "Nessun errore in questo blocco." in " ".join(struttura.testo)


class TestGrafico:
    @pytest.mark.parametrize("precedenti", [PRECEDENTI, None])
    def test_si_disegna_con_e_senza_blocco_precedente(self, tmp_path, precedenti):
        percorso = tmp_path / "grafico.svg"
        crea_report_grafico(ATTUALI, precedenti, 400, 3500, 5, str(percorso), cwapu._, "it", categoria="parole")
        assert percorso.read_text(encoding="utf-8").lstrip().startswith("<?xml")

    def test_si_disegna_anche_senza_errori(self, tmp_path):
        percorso = tmp_path / "grafico.svg"
        crea_report_grafico(aggregati({}, {"a": 50}), None, 400, 3500, 5, str(percorso), cwapu._, "it", categoria="parole")
        assert percorso.exists()


class TestAggregati:
    def test_il_blocco_sa_che_giorni_copre(self):
        sessioni = [
            {"timestamp_iso": "2026-09-10T10:00:00", "items_sent_session": 1},
            {"timestamp_iso": "2026-08-01T09:00:00", "items_sent_session": 1},
        ]
        aggregati_veri = cwapu._calculate_aggregates(sessioni)
        assert aggregati_veri["primo_iso"] == "2026-08-01T09:00:00"
        assert aggregati_veri["ultimo_iso"] == "2026-09-10T10:00:00"
