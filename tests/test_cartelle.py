# Prove automatiche di CWapu, le sottocartelle.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5.5, modalita' auto).
# Nate con la 8.0.0 e la issue 21. Chi aggiorna dalla 7.x ha impostazioni,
# diario e rapporti accanto all'eseguibile, e l'aggiornamento non li tocca:
# li sposta riordina_cartella al primo avvio. Qui lavora su una cartella
# temporanea, mai su quella vera.

import os
import sys

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)

import cwapu  # noqa: E402

VECCHI = {
    "cwapu_settings.json": "data",
    "CWapu_Diary.txt": "data",
    "selected_language.json": "data",
    "words.txt": "data",
    "words_updated.txt": "data",
    "auto_updater_error.log": "data",
    "CWapu_Historical_Statistics_Words_G_400_X_3500.html": "reports",
    "CWapu_Timeline_Report_Qrz.txt": "reports",
    "CWapu_Historical_Statistics_Words_G_400_X_3500.svg": "graphics",
    "Morse 20260924120000.wav": "audio",
}


def cartella_7x(tmp_path):
    """Una cartella come la lascia la 7.x: tutto accanto all'eseguibile."""
    for nome in VECCHI:
        (tmp_path / nome).write_text(f"contenuto di {nome}", encoding="utf-8")
    (tmp_path / "cwapu.exe").write_text("eseguibile", encoding="utf-8")
    (tmp_path / "Manuale_CWapu.html").write_text("manuale", encoding="utf-8")
    return tmp_path


class TestRiordino:
    def test_i_file_della_7x_vanno_nelle_sottocartelle(self, tmp_path):
        cartella = cartella_7x(tmp_path)
        spostati, rimasti = cwapu.riordina_cartella(str(cartella))
        assert spostati == len(VECCHI)
        assert rimasti == []
        for nome, sottocartella in VECCHI.items():
            assert not (cartella / nome).exists(), nome
            assert (cartella / sottocartella / nome).read_text(encoding="utf-8") == f"contenuto di {nome}"

    def test_l_eseguibile_e_il_manuale_restano_dove_sono(self, tmp_path):
        """Il manuale accanto all'eseguibile e' la copia visibile, scelta di
        Gabriele: resta li', e si riscrive quando cambia."""
        cartella = cartella_7x(tmp_path)
        cwapu.riordina_cartella(str(cartella))
        assert (cartella / "cwapu.exe").exists()
        assert (cartella / "Manuale_CWapu.html").exists()

    def test_la_seconda_volta_non_sposta_niente(self, tmp_path):
        cartella = cartella_7x(tmp_path)
        cwapu.riordina_cartella(str(cartella))
        assert cwapu.riordina_cartella(str(cartella)) == (0, [])

    def test_non_sovrascrive_mai(self, tmp_path):
        """Se nella sottocartella c'e' gia' un file con lo stesso nome, per
        esempio perche' la 8.0.0 e' gia' partita una volta, il vecchio resta
        dov'e' e lo si dice."""
        cartella = cartella_7x(tmp_path)
        (cartella / "data").mkdir()
        (cartella / "data" / "cwapu_settings.json").write_text("quello nuovo", encoding="utf-8")
        spostati, rimasti = cwapu.riordina_cartella(str(cartella))
        assert rimasti == ["cwapu_settings.json"]
        assert spostati == len(VECCHI) - 1
        assert (cartella / "data" / "cwapu_settings.json").read_text(encoding="utf-8") == "quello nuovo"
        assert (cartella / "cwapu_settings.json").read_text(encoding="utf-8") == "contenuto di cwapu_settings.json"

    def test_crea_le_sottocartelle_anche_vuote(self, tmp_path):
        cwapu.riordina_cartella(str(tmp_path))
        for nome in cwapu.SOTTOCARTELLE:
            assert (tmp_path / nome).is_dir(), nome

    def test_una_cartella_che_si_chiama_come_un_file_non_si_tocca(self, tmp_path):
        (tmp_path / "words.txt").mkdir()
        assert cwapu.riordina_cartella(str(tmp_path)) == (0, [])
        assert (tmp_path / "words.txt").is_dir()


class TestPercorsi:
    def test_i_dati_stanno_in_data(self):
        assert os.path.dirname(cwapu.SETTINGS_FILE) == cwapu.DATA_PATH
        assert os.path.dirname(cwapu.DIARY_FILE) == cwapu.DATA_PATH

    def test_le_risorse_di_serie_stanno_in_resources(self):
        assert os.path.exists(os.path.join(RADICE, "resources", "words.txt"))
        assert os.path.exists(cwapu.MASTER_SCP_PATH)
        assert os.path.join("resources", "MASTER.SCP") in cwapu.MASTER_SCP_PATH

    def test_la_copia_personale_in_data_ha_la_precedenza(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cwapu, "DATA_PATH", str(tmp_path))
        assert os.path.join("resources", "words.txt") in cwapu.user_file_path("words.txt")
        (tmp_path / "words.txt").write_text("mio", encoding="utf-8")
        assert cwapu.user_file_path("words.txt") == str(tmp_path / "words.txt")


class TestCopiaDelManuale:
    def test_da_sorgente_non_si_copia_niente(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cwapu, "USER_DATA_PATH", str(tmp_path))
        assert cwapu.aggiorna_copia_manuale() is None
        assert not (tmp_path / cwapu.MANUALE_NAME).exists()

    def test_da_eseguibile_nasce_e_si_riscrive_quando_cambia(self, tmp_path, monkeypatch):
        """Fino alla 7.x la copia nasceva una volta e non si aggiornava piu'."""
        monkeypatch.setattr(sys, "frozen", True, raising=False)
        # Da eseguibile le risorse stanno nel pacchetto, _internal: qui fa da
        # pacchetto la radice del sorgente, che ha la stessa cartella resources.
        monkeypatch.setattr(sys, "_MEIPASS", RADICE, raising=False)
        monkeypatch.setattr(cwapu, "USER_DATA_PATH", str(tmp_path))
        copia = tmp_path / cwapu.MANUALE_NAME
        with open(os.path.join(RADICE, "docs", cwapu.MANUALE_NAME), "rb") as f:
            originale = f.read()
        assert cwapu.aggiorna_copia_manuale() == str(copia)
        assert copia.read_bytes() == originale
        copia.write_text("la versione di prima", encoding="utf-8")
        cwapu.aggiorna_copia_manuale()
        assert copia.read_bytes() == originale


class TestAudio:
    def test_il_wav_di_sv_va_in_audio(self, monkeypatch):
        chiamate = []

        def motore(**parametri):
            chiamate.append(parametri)
            return object(), 20.0

        for nome, valore in {"overall_speed": 20, "overall_pitch": 550, "overall_dashes": 30, "overall_spaces": 50, "overall_dots": 50, "overall_volume": 0.5, "overall_ms": 1, "overall_fs": 5, "overall_wave": 1, "overall_farnsworth": 0, "overall_api": None}.items():
            monkeypatch.setattr(cwapu, nome, valore, raising=False)
        monkeypatch.setattr(cwapu, "CWzator", motore)
        cwapu.suona("cq", to_file=True)
        assert chiamate[-1]["wave_output_path_file"] == cwapu.AUDIO_PATH + os.sep
        cwapu.suona("cq")
        assert "wave_output_path_file" not in chiamate[-1]
