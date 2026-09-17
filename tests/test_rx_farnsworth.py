# Prove automatiche di CWapu, l'esercizio di ricezione con il Farnsworth.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Fable 5.1, modalita' auto).
# La regola della issue 11: con un Farnsworth impostato l'esercizio si fa e
# il rapporto si legge, ma niente finisce su disco. Rxing e' interattiva,
# quindi qui si pilota con dei sostituti: chi sceglie il tipo di esercizio,
# chi genera gli item, chi suona, chi legge la risposta. Diario e
# impostazioni stanno in una cartella temporanea e non si tocca mai il
# file vero. La tecnica viene dalla riproduzione della revisione del
# 2026-09-17.

import copy
import os
import sys

import pytest

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)

import cwapu  # noqa: E402

SCELTA = {
    "active_switcher_states": {"parole": False, "lettere": True, "numeri": False, "lettere e numeri": False, "simboli": False, "qrz": False, "custom": False, "contest": False},
    "parole_filtrate_list": None,
    "custom_set_string_active": None,
    "group_length_for_generated": 5,
}


def esercizio(monkeypatch, tmp_path, capsys, farnsworth, risposte_giuste=10, velocita_risposta=None, spazi=50):
    """Fa un esercizio di lettere con dieci item e restituisce (uscita, app_data, domande)."""
    app = copy.deepcopy(cwapu.DEFAULT_DATA)
    monkeypatch.setattr(cwapu, "app_data", app, raising=False)
    monkeypatch.setattr(cwapu, "DIARY_FILE", str(tmp_path / "diario.txt"))
    monkeypatch.setattr(cwapu, "SETTINGS_FILE", str(tmp_path / "impostazioni.json"))
    for nome, valore in {
        "overall_speed": 20,
        "overall_pitch": 550,
        "overall_dashes": 30,
        "overall_spaces": spazi,
        "overall_dots": 50,
        "overall_volume": 0.5,
        "overall_ms": 1,
        "overall_fs": 5,
        "overall_wave": 1,
        "overall_farnsworth": farnsworth,
    }.items():
        monkeypatch.setattr(cwapu, nome, valore, raising=False)
    stato = {"date": 0}
    domande = []

    def dgt(prompt="", kind="s", default=None, **altri):
        domande.append({"prompt": prompt, "kind": kind, "default": default, **altri})
        if kind == "i":
            return velocita_risposta if velocita_risposta is not None else default
        if "Nota su questo esercizio" in prompt:
            return "nota di prova"
        if stato["date"] >= risposte_giuste:
            return "."
        stato["date"] += 1
        return "abcde"

    monkeypatch.setattr(cwapu, "seleziona_modalita_rx", lambda: SCELTA)
    monkeypatch.setattr(cwapu, "genera_singolo_item_esercizio_misto", lambda *a, **k: "abcde")
    monkeypatch.setattr(cwapu, "suona", lambda msg, *a, **k: (None, float(cwapu.overall_speed)))
    monkeypatch.setattr(cwapu, "dgt", dgt)
    monkeypatch.setattr(cwapu, "key", lambda *a, **k: None)
    monkeypatch.setattr(cwapu, "enter_escape", lambda *a, **k: False)
    monkeypatch.setattr(cwapu, "_clear_screen_ansi", lambda: None)
    monkeypatch.setattr(cwapu, "generate_historical_rx_report", lambda *a, **k: None)
    cwapu.Rxing()
    return capsys.readouterr().out, app, domande


class TestSenzaFarnsworth:
    def test_la_sessione_si_salva_e_il_diario_si_scrive(self, monkeypatch, tmp_path, capsys):
        uscita, app, _ = esercizio(monkeypatch, tmp_path, capsys, farnsworth=0)
        assert app["rxing_stats_chars"]["sessions"] == 1
        assert len(app["historical_rx_data_chars"]["sessions_log"]) == 1
        assert app["historical_rx_data_chars"]["chars_since_last_report"] == 50
        assert (tmp_path / "diario.txt").exists()
        assert "salvata su disco" in uscita
        assert "Farnsworth" not in uscita


class TestConFarnsworth:
    def test_niente_finisce_su_disco(self, monkeypatch, tmp_path, capsys):
        uscita, app, _ = esercizio(monkeypatch, tmp_path, capsys, farnsworth=8)
        assert app["rxing_stats_chars"]["sessions"] == 0
        assert app["historical_rx_data_chars"]["sessions_log"] == []
        assert app["historical_rx_data_chars"]["chars_since_last_report"] == 0
        assert not (tmp_path / "diario.txt").exists()
        assert "salvata su disco" not in uscita

    def test_lo_dice_all_inizio_e_alla_fine(self, monkeypatch, tmp_path, capsys):
        uscita, _, _ = esercizio(monkeypatch, tmp_path, capsys, farnsworth=8)
        assert "Farnsworth a 8" in uscita
        assert "niente nel diario" in uscita
        assert "non entra nell'archivio" in uscita

    def test_il_rapporto_si_legge_intero(self, monkeypatch, tmp_path, capsys):
        uscita, _, _ = esercizio(monkeypatch, tmp_path, capsys, farnsworth=8)
        assert "ti ho inviato 10" in uscita
        assert "Durata attiva" in uscita

    def test_non_dice_che_i_report_sono_disabilitati(self, monkeypatch, tmp_path, capsys):
        """Era il primo rilievo della revisione: con x a 3500 la generazione e' accesa, e' solo questa sessione a non contare."""
        uscita, app, _ = esercizio(monkeypatch, tmp_path, capsys, farnsworth=8)
        assert app["historical_rx_settings"]["report_interval"] > 0
        assert "disabilitata" not in uscita
        assert "Completamento sezione" not in uscita

    def test_la_velocita_di_partenza_non_scende_sotto_il_farnsworth(self, monkeypatch, tmp_path, capsys):
        """Era il secondo rilievo: la domanda accettava 10 con Farnsworth 15, e il motore rifiutava ogni item."""
        _, _, domande = esercizio(monkeypatch, tmp_path, capsys, farnsworth=15)
        velocita = [d for d in domande if d["kind"] == "i" and "WPM" in d["prompt"]]
        assert len(velocita) == 1
        assert velocita[0]["imin"] == 15
        assert velocita[0]["default"] >= 15
        assert "da 15 a" in velocita[0]["prompt"]

    def test_con_gli_spazi_larghi_il_minimo_sale_oltre_il_farnsworth(self, monkeypatch, tmp_path, capsys):
        """Seconda revisione: con s a 75 il tetto dei pesi scende con la velocita', e a 19 wpm un Farnsworth di 15 non regge piu'.
        Qui il motore vero risponde a vuoto, senza suonare."""
        _, _, domande = esercizio(monkeypatch, tmp_path, capsys, farnsworth=15, spazi=75)
        velocita = [d for d in domande if d["kind"] == "i" and "WPM" in d["prompt"]]
        assert velocita[0]["imin"] > 15
        assert velocita[0]["default"] >= velocita[0]["imin"]

    def test_senza_farnsworth_il_minimo_resta_quello_del_motore(self, monkeypatch, tmp_path, capsys):
        _, _, domande = esercizio(monkeypatch, tmp_path, capsys, farnsworth=0)
        velocita = [d for d in domande if d["kind"] == "i" and "WPM" in d["prompt"]]
        assert velocita[0]["imin"] == cwapu.WPM_MIN


class TestReportDisabilitati:
    def test_con_x_a_zero_lo_dice_anche_senza_farnsworth(self, monkeypatch, tmp_path, capsys):
        app_base = copy.deepcopy(cwapu.DEFAULT_DATA)
        app_base["historical_rx_settings"]["report_interval"] = 0
        monkeypatch.setattr(cwapu, "DEFAULT_DATA", app_base)
        uscita, _, _ = esercizio(monkeypatch, tmp_path, capsys, farnsworth=0)
        assert "disabilitata" in uscita


@pytest.fixture(autouse=True)
def _nessun_file_vero(monkeypatch, tmp_path):
    """Rete di sicurezza: anche se una prova sbagliasse, il diario vero non si tocca."""
    monkeypatch.setattr(cwapu, "DIARY_FILE", str(tmp_path / "mai_usato.txt"))
