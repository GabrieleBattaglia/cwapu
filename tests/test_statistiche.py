# Prove automatiche di CWapu, parte statistiche.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' UltraCode).
# Coprono gli aggregati dell'archivio storico, il confronto fra cio' che si e'
# trasmesso e cio' che l'utente ha copiato, e la formattazione delle durate.
# Sono i numeri che l'applicazione dice all'utente e scrive nel diario: se
# sbagliano, sbaglia il giudizio che l'utente da' ai propri progressi.

import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cwapu


def sessione(**campi):
    """Una sessione dell'archivio con i valori minimi, sovrascrivibili."""
    base = {
        "timestamp_iso": "2026-01-01T10:00:00",
        "duration_seconds": 60.0,
        "rwpm_min": 20.0,
        "rwpm_max": 25.0,
        "rwpm_avg": 22.0,
        "items_sent_session": 10,
        "items_correct_session": 9,
        "item_details": [],
        "chars_sent_session": 50,
        "errors_detail_session": {},
        "total_errors_chars_session": 0,
        "sent_chars_detail_session": {},
    }
    base.update(campi)
    return base


class TestAggregati:
    def test_i_due_rami_restituiscono_le_stesse_chiavi(self):
        """Il ramo della lista vuota deve promettere quanto quello normale.

        Chiamavano la stessa metrica con due nomi diversi, e chi avesse letto
        il risultato di una lista vuota si sarebbe trovato un KeyError dentro
        la generazione del report.
        """
        vuoto = cwapu._calculate_aggregates([])
        pieno = cwapu._calculate_aggregates([sessione()])
        assert set(vuoto) == set(pieno)

    def test_media_delle_medie_di_sessione(self):
        aggregati = cwapu._calculate_aggregates([sessione(rwpm_avg=20.0), sessione(rwpm_avg=30.0)])
        assert aggregati["wpm_avg_of_session_avgs"] == 25.0

    def test_minimo_e_massimo_sull_intero_blocco(self):
        aggregati = cwapu._calculate_aggregates([sessione(rwpm_min=18.0, rwpm_max=24.0), sessione(rwpm_min=21.0, rwpm_max=31.0)])
        assert aggregati["wpm_min_overall"] == 18.0
        assert aggregati["wpm_max_overall"] == 31.0

    def test_un_minimo_di_cento_wpm_e_un_dato_vero(self):
        """Cento era la sentinella delle sessioni vuote e veniva scartato.

        Chi riceve a cento wpm esiste, e il suo minimo non va buttato via: le
        sessioni senza dati adesso non si registrano piu' e load_settings le
        toglie dall'archivio, quindi l'eccezione non serve piu'.
        """
        aggregati = cwapu._calculate_aggregates([sessione(rwpm_min=100, rwpm_max=100)])
        assert aggregati["wpm_min_overall"] == 100

    def test_i_minimi_a_zero_restano_fuori(self):
        """Zero non e' una velocita': e' l'assenza del dato."""
        aggregati = cwapu._calculate_aggregates([sessione(rwpm_min=0), sessione(rwpm_min=30.0)])
        assert aggregati["wpm_min_overall"] == 30.0

    def test_errori_e_invii_si_sommano_per_carattere(self):
        aggregati = cwapu._calculate_aggregates(
            [
                sessione(errors_detail_session={"k": 2}, sent_chars_detail_session={"k": 10}, total_errors_chars_session=2),
                sessione(errors_detail_session={"k": 1, "q": 3}, sent_chars_detail_session={"k": 5, "q": 8}, total_errors_chars_session=4),
            ]
        )
        assert aggregati["aggregated_errors_detail"] == {"k": 3, "q": 3}
        assert aggregati["aggregated_sent_chars_detail"] == {"k": 15, "q": 8}
        assert aggregati["total_errors_chars_overall"] == 6


class TestConfrontoCopia:
    def test_nessun_errore_su_copia_esatta(self):
        errori = {}
        assert cwapu.collect_char_errors("paris", "paris", errori) == 0
        assert errori == {}

    def test_il_carattere_sbagliato_viene_contato_una_volta(self):
        errori = {}
        assert cwapu.collect_char_errors("paris", "paras", errori) == 1
        assert errori == {"i": 1}

    def test_il_dizionario_si_accumula_fra_una_chiamata_e_l_altra(self):
        errori = {}
        cwapu.collect_char_errors("paris", "paras", errori)
        cwapu.collect_char_errors("paris", "paras", errori)
        assert errori == {"i": 2}

    def test_caratteri_mai_sbagliati(self):
        buoni = cwapu.AlwaysRight(["abc", "cde"], {"c": 2})
        assert buoni == {"a", "b", "d", "e"}


class TestDurate:
    def test_singolare_e_plurale(self):
        assert cwapu.format_duration(dt.timedelta(seconds=1)) == "1 secondo"
        assert cwapu.format_duration(dt.timedelta(seconds=2)) == "2 secondi"
        assert cwapu.format_duration(dt.timedelta(minutes=1)) == "1 minuto"
        assert cwapu.format_duration(dt.timedelta(hours=1)) == "1 ora"
        assert cwapu.format_duration(dt.timedelta(days=1)) == "1 giorno"

    def test_le_unita_si_compongono(self):
        testo = cwapu.format_duration(dt.timedelta(hours=1, minutes=1, seconds=1))
        assert "1 ora" in testo and "1 minuto" in testo and "1 secondo" in testo

    def test_i_secondi_si_dicono_anche_da_soli(self):
        """Con una durata sotto il minuto non deve restare una frase vuota."""
        assert cwapu.format_duration(dt.timedelta(seconds=7)).strip() != ""


class TestRapportoPeriodico:
    """Il rapporto storico che nasce ogni .x caratteri, comune all'esercizio
    di ricezione e al contest dalla 7.0.5, issue 15."""

    def prepara(self, monkeypatch, soglia, gia_contati, registro):
        import copy

        dati = copy.deepcopy(cwapu.DEFAULT_DATA)
        dati["historical_rx_settings"]["report_interval"] = soglia
        dati["historical_rx_data_contest"]["chars_since_last_report"] = gia_contati
        dati["historical_rx_data_contest"]["sessions_log"] = registro
        monkeypatch.setattr(cwapu, "app_data", dati, raising=False)
        chiamate = []

        def genera(sessioni, categoria):
            chiamate.append((sessioni, categoria))
            return {"num_sessions_in_block": len(sessioni)}

        monkeypatch.setattr(cwapu, "generate_historical_rx_report", genera)
        return dati, chiamate

    def test_sotto_la_soglia_conta_e_basta(self, monkeypatch):
        dati, chiamate = self.prepara(monkeypatch, 500, 100, [sessione(chars_sent_session=50)])
        cwapu.avanza_rapporto_storico("contest", 50)
        assert dati["historical_rx_data_contest"]["chars_since_last_report"] == 150
        assert chiamate == []

    def test_passata_la_soglia_nasce_il_rapporto_del_contest(self, monkeypatch):
        registro = [sessione(chars_sent_session=300), sessione(chars_sent_session=200), sessione(chars_sent_session=120)]
        dati, chiamate = self.prepara(monkeypatch, 400, 300, registro)
        cwapu.avanza_rapporto_storico("contest", 120)
        # 420 caratteri da coprire: le ultime due sessioni ne fanno 320, le
        # ultime tre 620, e l'eccedenza sopra i 400 passa al rapporto dopo.
        sessioni, categoria = chiamate[0]
        assert categoria == "contest"
        assert sessioni == registro
        assert dati["historical_rx_data_contest"]["chars_since_last_report"] == 220
        assert dati["historical_rx_data_contest"]["historical_reports"] == [{"num_sessions_in_block": 3}]
        assert dati["historical_rx_data_qrz"]["historical_reports"] == []

    def test_il_completamento_dice_quanto_manca(self, monkeypatch, capsys):
        self.prepara(monkeypatch, 1000, 400, [])
        cwapu.stampa_completamento_rapporto("contest", 100)
        uscita = capsys.readouterr().out
        assert "(500 / 1000) = 50.00%" in uscita
        assert "ne mancano 500" in uscita
