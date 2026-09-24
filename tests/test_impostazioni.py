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
        assert dati["historical_rx_data_contest"]["sessions_log"] == []


def sessione(quando, items, giuste, caratteri, durata, contest=False):
    voce = {
        "timestamp_iso": quando,
        "duration_seconds": durata,
        "items_sent_session": items,
        "items_correct_session": giuste,
        "chars_sent_session": caratteri,
        "rwpm_min": 20,
        "rwpm_max": 24,
        "rwpm_avg": 22,
    }
    if contest:
        voce["punteggio_grezzo"] = 12
    return voce


class TestArchivioDelContest:
    """Issue 15: fino alla 7.0.4 il contest scriveva nelle chiavi del QRZ."""

    def file_misto(self, tmp_path):
        qrz_1 = sessione("2026-09-01T10:00:00", 10, 8, 60, 300.0)
        contest_1 = sessione("2026-09-21T18:00:00", 4, 3, 40, 200.0, contest=True)
        qrz_2 = sessione("2026-09-22T09:00:00", 12, 12, 70, 320.0)
        contest_2 = sessione("2026-09-23T21:00:00", 6, 2, 55, 250.0, contest=True)
        contenuto = {
            "rxing_stats_qrz": {"total_calls": 32, "sessions": 5, "total_correct": 25, "total_wrong_items": 7, "total_time_seconds": 1200.0},
            "historical_rx_data_qrz": {"chars_since_last_report": 300, "sessions_log": [qrz_1, contest_1, qrz_2, contest_2], "historical_reports": []},
        }
        return scrivi_impostazioni(tmp_path, contenuto), (qrz_1, qrz_2), (contest_1, contest_2)

    def test_le_sessioni_del_contest_passano_al_loro_archivio(self, tmp_path, monkeypatch, capsys):
        percorso, qrz, contest = self.file_misto(tmp_path)
        monkeypatch.setattr(cwapu, "SETTINGS_FILE", percorso)
        dati = cwapu.load_settings()
        assert dati["historical_rx_data_qrz"]["sessions_log"] == list(qrz)
        assert dati["historical_rx_data_contest"]["sessions_log"] == list(contest)
        assert "2 sessioni del contest spostate" in capsys.readouterr().out

    def test_i_contatori_passano_con_le_sessioni(self, tmp_path, monkeypatch):
        percorso, _, _ = self.file_misto(tmp_path)
        monkeypatch.setattr(cwapu, "SETTINGS_FILE", percorso)
        dati = cwapu.load_settings()
        conta_contest = dati["rxing_stats_contest"]
        assert conta_contest == {"total_calls": 10, "sessions": 2, "total_correct": 5, "total_wrong_items": 5, "total_time_seconds": 450.0}
        conta_qrz = dati["rxing_stats_qrz"]
        assert conta_qrz == {"total_calls": 22, "sessions": 3, "total_correct": 20, "total_wrong_items": 2, "total_time_seconds": 750.0}
        assert dati["historical_rx_data_qrz"]["chars_since_last_report"] == 205
        assert dati["historical_rx_data_contest"]["chars_since_last_report"] == 95

    def test_la_seconda_volta_non_sposta_niente(self, tmp_path, monkeypatch, capsys):
        percorso, _, _ = self.file_misto(tmp_path)
        monkeypatch.setattr(cwapu, "SETTINGS_FILE", percorso)
        cwapu.save_settings(cwapu.load_settings(), annuncia=False)
        capsys.readouterr()
        dati = cwapu.load_settings()
        assert "spostate" not in capsys.readouterr().out
        assert len(dati["historical_rx_data_contest"]["sessions_log"]) == 2
        assert dati["rxing_stats_contest"]["sessions"] == 2
        assert dati["rxing_stats_qrz"]["sessions"] == 3

    def test_i_contatori_non_scendono_sotto_zero(self, tmp_path, monkeypatch):
        """Un contatore gia' piu' basso del dovuto, per esempio dopo una
        ripulitura, non diventa negativo: si ferma a zero, e le sessioni a
        quelle che il registro tiene ancora."""
        qrz = sessione("2026-09-01T10:00:00", 10, 8, 60, 300.0)
        contest = sessione("2026-09-21T18:00:00", 40, 30, 400, 2000.0, contest=True)
        contenuto = {
            "rxing_stats_qrz": {"total_calls": 5, "sessions": 1, "total_correct": 5, "total_wrong_items": 0, "total_time_seconds": 10.0},
            "historical_rx_data_qrz": {"chars_since_last_report": 50, "sessions_log": [qrz, contest], "historical_reports": []},
        }
        monkeypatch.setattr(cwapu, "SETTINGS_FILE", scrivi_impostazioni(tmp_path, contenuto))
        dati = cwapu.load_settings()
        assert dati["rxing_stats_qrz"] == {"total_calls": 0, "sessions": 1, "total_correct": 0, "total_wrong_items": 0, "total_time_seconds": 0.0}
        assert dati["historical_rx_data_qrz"]["chars_since_last_report"] == 0

    def test_il_contest_vecchio_resta_dov_e(self, tmp_path, monkeypatch):
        """Le sessioni del contest di prima della 7.0.0 non portano il
        punteggio e non si distinguono con certezza da quelle del QRZ."""
        vecchia = sessione("2025-12-18T20:12:00", 10, 7, 80, 400.0)
        percorso = scrivi_impostazioni(tmp_path, {"historical_rx_data_qrz": {"chars_since_last_report": 0, "sessions_log": [vecchia], "historical_reports": []}})
        monkeypatch.setattr(cwapu, "SETTINGS_FILE", percorso)
        dati = cwapu.load_settings()
        assert dati["historical_rx_data_qrz"]["sessions_log"] == [vecchia]
        assert dati["historical_rx_data_contest"]["sessions_log"] == []

    def test_l_archivio_nuovo_non_divide_il_registro_con_i_predefiniti(self, tmp_path, monkeypatch):
        """Con la copia di superficie la prima sessione archiviata in una
        sezione che il file non aveva finiva anche in DEFAULT_DATA."""
        monkeypatch.setattr(cwapu, "SETTINGS_FILE", scrivi_impostazioni(tmp_path, {"overall_settings": {"speed": 30}}))
        dati = cwapu.load_settings()
        dati["historical_rx_data_contest"]["sessions_log"].append({"items_sent_session": 1})
        assert cwapu.DEFAULT_DATA["historical_rx_data_contest"]["sessions_log"] == []
        monkeypatch.setattr(cwapu, "SETTINGS_FILE", str(tmp_path / "non_esiste.json"))
        nuovi = cwapu.load_settings()
        nuovi["historical_rx_data_words"]["sessions_log"].append({"items_sent_session": 1})
        assert cwapu.DEFAULT_DATA["historical_rx_data_words"]["sessions_log"] == []

    def test_ogni_categoria_ha_il_suo_nome(self):
        assert [cwapu.nome_categoria(c) for c in cwapu.CATEGORIE_ARCHIVIO] == ["parole", "caratteri/misto", "QRZ", "contest"]


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

    def test_uscendo_lo_dice(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(cwapu, "SETTINGS_FILE", str(tmp_path / "cwapu_settings.json"))
        cwapu.save_settings({"app_info": {"launch_count": 1}})
        assert "Impostazioni generali salvate" in capsys.readouterr().out

    def test_dopo_un_esercizio_salva_in_silenzio(self, tmp_path, monkeypatch, capsys):
        """Issue 18: il salvataggio riuscito alla fine di un esercizio si da'
        per scontato, e il file si scrive lo stesso."""
        percorso = tmp_path / "cwapu_settings.json"
        monkeypatch.setattr(cwapu, "SETTINGS_FILE", str(percorso))
        cwapu.save_settings({"app_info": {"launch_count": 1}}, annuncia=False)
        assert percorso.exists()
        assert capsys.readouterr().out == ""

    def test_l_errore_si_dice_anche_in_silenzio(self, tmp_path, monkeypatch, capsys):
        """Il silenzio vale per il salvataggio riuscito: uno che fallisce si
        deve leggere, altrimenti l'archivio si perde senza che nessuno lo sappia."""
        monkeypatch.setattr(cwapu, "SETTINGS_FILE", str(tmp_path / "manca" / "cwapu_settings.json"))
        cwapu.save_settings({"app_info": {"launch_count": 1}}, annuncia=False)
        assert "Errore nel salvare" in capsys.readouterr().out

    def test_non_scrive_mai_fuori_dal_percorso_indicato(self, tmp_path, monkeypatch):
        percorso = str(tmp_path / "cwapu_settings.json")
        monkeypatch.setattr(cwapu, "SETTINGS_FILE", percorso)
        cwapu.save_settings({"app_info": {"launch_count": 1}})
        assert os.listdir(tmp_path) == ["cwapu_settings.json"]
