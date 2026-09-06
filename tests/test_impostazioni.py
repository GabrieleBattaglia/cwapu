# Prove automatiche di CWapu, parte impostazioni e archivio.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' UltraCode).
# Coprono la lettura del file di impostazioni, le due migrazioni dei formati
# vecchi e la ripulitura delle sessioni senza dati. Qui dentro ci sono i dati
# di anni di esercizio, quindi ogni prova lavora su un file temporaneo suo e
# non tocca mai quello vero.

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cwapu


def scrivi_impostazioni(tmp_path, contenuto):
    percorso = tmp_path / "cwapu_settings.json"
    percorso.write_text(json.dumps(contenuto), encoding="utf-8")
    return str(percorso)


class TestCaricamento:
    def test_senza_file_si_parte_dai_valori_di_serie(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cwapu, "SETTINGS_FILE", str(tmp_path / "non_esiste.json"))
        dati = cwapu.load_settings()
        assert dati["app_info"]["launch_count"] == 0
        assert dati["overall_settings"]["speed"] == 18

    def test_i_valori_salvati_hanno_la_precedenza_sui_predefiniti(self, tmp_path, monkeypatch):
        percorso = scrivi_impostazioni(tmp_path, {"overall_settings": {"speed": 42}})
        monkeypatch.setattr(cwapu, "SETTINGS_FILE", percorso)
        dati = cwapu.load_settings()
        assert dati["overall_settings"]["speed"] == 42
        # Le chiavi non salvate devono comunque esserci, prese dai predefiniti.
        assert dati["overall_settings"]["pitch"] == 550

    def test_un_file_illeggibile_non_fa_cadere_l_applicazione(self, tmp_path, monkeypatch):
        percorso = tmp_path / "cwapu_settings.json"
        percorso.write_text("questo non e' JSON", encoding="utf-8")
        monkeypatch.setattr(cwapu, "SETTINGS_FILE", str(percorso))
        dati = cwapu.load_settings()
        assert dati["overall_settings"]["speed"] == 18


class TestMigrazioni:
    def test_le_vecchie_rxing_stats_diventano_quelle_delle_parole(self, tmp_path, monkeypatch):
        percorso = scrivi_impostazioni(tmp_path, {"rxing_stats": {"total_calls": 7, "sessions": 3, "total_correct": 5, "total_wrong_items": 2, "total_time_seconds": 90.0}})
        monkeypatch.setattr(cwapu, "SETTINGS_FILE", percorso)
        dati = cwapu.load_settings()
        assert dati["rxing_stats_words"]["total_calls"] == 7
        assert dati["rxing_stats_words"]["sessions"] == 3
        assert "rxing_stats" not in dati

    def test_il_vecchio_archivio_unico_si_divide_e_lascia_le_impostazioni(self, tmp_path, monkeypatch):
        vecchia = {"items_sent_session": 4, "rwpm_min": 20, "rwpm_max": 22, "rwpm_avg": 21}
        percorso = scrivi_impostazioni(
            tmp_path, {"historical_rx_data": {"max_sessions_to_keep": 400, "report_interval": 2500, "chars_since_last_report": 120, "sessions_log": [vecchia], "historical_reports": []}}
        )
        monkeypatch.setattr(cwapu, "SETTINGS_FILE", percorso)
        dati = cwapu.load_settings()
        assert "historical_rx_data" not in dati
        assert dati["historical_rx_settings"]["max_sessions_to_keep"] == 400
        assert dati["historical_rx_settings"]["report_interval"] == 2500
        assert dati["historical_rx_data_words"]["sessions_log"] == [vecchia]
        assert dati["historical_rx_data_words"]["chars_since_last_report"] == 120
        # Le altre due categorie nascono vuote, non assenti.
        assert dati["historical_rx_data_chars"]["sessions_log"] == []
        assert dati["historical_rx_data_qrz"]["sessions_log"] == []


class TestRipulituraArchivio:
    def test_le_sessioni_senza_item_spariscono(self, tmp_path, monkeypatch):
        """Erano le uscite dal contest prima del primo QSO.

        Restavano nell'archivio con velocita' minima 100 e massima 0, e
        falsavano le medie di tutto il blocco.
        """
        buona = {"items_sent_session": 5, "rwpm_min": 20, "rwpm_max": 24, "rwpm_avg": 22}
        vuota = {"items_sent_session": 0, "rwpm_min": 100, "rwpm_max": 0, "rwpm_avg": 0}
        percorso = scrivi_impostazioni(tmp_path, {"historical_rx_data_qrz": {"chars_since_last_report": 0, "sessions_log": [vuota, buona, vuota], "historical_reports": []}})
        monkeypatch.setattr(cwapu, "SETTINGS_FILE", percorso)
        dati = cwapu.load_settings()
        assert dati["historical_rx_data_qrz"]["sessions_log"] == [buona]

    def test_un_archivio_gia_pulito_resta_intatto(self, tmp_path, monkeypatch):
        buona = {"items_sent_session": 5, "rwpm_min": 20, "rwpm_max": 24, "rwpm_avg": 22}
        percorso = scrivi_impostazioni(tmp_path, {"historical_rx_data_chars": {"chars_since_last_report": 0, "sessions_log": [buona, buona], "historical_reports": []}})
        monkeypatch.setattr(cwapu, "SETTINGS_FILE", percorso)
        dati = cwapu.load_settings()
        assert len(dati["historical_rx_data_chars"]["sessions_log"]) == 2


class TestSalvataggio:
    def test_scrive_e_rilegge_quello_che_ha_scritto(self, tmp_path, monkeypatch):
        percorso = str(tmp_path / "cwapu_settings.json")
        monkeypatch.setattr(cwapu, "SETTINGS_FILE", percorso)
        dati = cwapu.load_settings()
        dati["overall_settings"]["speed"] = 77
        cwapu.save_settings(dati)
        riletti = cwapu.load_settings()
        assert riletti["overall_settings"]["speed"] == 77

    def test_non_scrive_mai_fuori_dal_percorso_indicato(self, tmp_path, monkeypatch):
        percorso = str(tmp_path / "cwapu_settings.json")
        monkeypatch.setattr(cwapu, "SETTINGS_FILE", percorso)
        cwapu.save_settings({"app_info": {"launch_count": 1}})
        assert os.listdir(tmp_path) == ["cwapu_settings.json"]
