# Prove automatiche di CWapu, il Farnsworth della sezione tastiera.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Fable 5.1, modalita' auto).
# Nate con la issue 11. Il motore CW non si tocca: al suo posto c'e' una
# funzione finta che registra con quali parametri e' stata chiamata, cosi'
# le prove dicono cosa suona senza suonare. Le prove sull'esercizio di
# ricezione, che con il Farnsworth non deve scrivere niente, stanno in
# test_rx_farnsworth.py.

import inspect
import os
import re
import sys

import pytest

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)

import cwapu  # noqa: E402

IMPOSTAZIONI = {
    "overall_speed": 20,
    "overall_pitch": 550,
    "overall_dashes": 30,
    "overall_spaces": 50,
    "overall_dots": 50,
    "overall_volume": 0.5,
    "overall_ms": 1,
    "overall_fs": 5,
    "overall_wave": 1,
    "overall_farnsworth": 0,
}


def prepara(monkeypatch, **cambi):
    """Imposta i globali che suona() legge, come farebbe main()."""
    for nome, valore in {**IMPOSTAZIONI, **cambi}.items():
        monkeypatch.setattr(cwapu, nome, valore, raising=False)


class MotoreFinto:
    """Registra le chiamate e rifiuta secondo le regole che gli si danno.

    farnsworth_massimo: oltre questo valore il Farnsworth viene rifiutato con
    un messaggio che lo nomina, come fa CWzator con i pesi larghi.
    rifiuta_sempre: rifiuta tutto con un messaggio che non parla di Farnsworth.
    """

    def __init__(self, farnsworth_massimo=None, rifiuta_sempre=False, wpm_minimo_col_farnsworth=None):
        self.chiamate = []
        self.farnsworth_massimo = farnsworth_massimo
        self.rifiuta_sempre = rifiuta_sempre
        # Come i pesi larghi: sotto questa velocita' dei caratteri il
        # Farnsworth non regge piu'.
        self.wpm_minimo_col_farnsworth = wpm_minimo_col_farnsworth
        self.ultimo_errore = None

    def __call__(self, **parametri):
        self.chiamate.append(parametri)
        fw = parametri.get("farnsworth")
        if self.rifiuta_sempre:
            self.ultimo_errore = "pitch (5000) sopra il massimo [2800]."
            return None, None
        if fw is not None and self.farnsworth_massimo is not None and fw > self.farnsworth_massimo:
            self.ultimo_errore = f"farnsworth ({fw}) non raggiungibile: con questi pesi la velocita' effettiva non puo' superare {self.farnsworth_massimo}.00 wpm"
            return None, None
        if fw is not None and self.wpm_minimo_col_farnsworth is not None and parametri["wpm"] < self.wpm_minimo_col_farnsworth:
            self.ultimo_errore = f"farnsworth ({fw}) non raggiungibile a {parametri['wpm']} wpm con questi pesi"
            return None, None
        return object(), float(fw or parametri["wpm"])


class TestLimitaFarnsworth:
    def test_zero_spegne(self):
        assert cwapu.limita_farnsworth(0, 20) == 0

    def test_un_valore_negativo_spegne(self):
        assert cwapu.limita_farnsworth(-3, 20) == 0

    def test_sotto_il_minimo_del_motore_sale_al_minimo(self):
        assert cwapu.limita_farnsworth(3, 20) == cwapu.WPM_MIN

    def test_non_supera_la_velocita_dei_caratteri(self):
        """Il Farnsworth allarga le spaziature: la velocita' effettiva sta sotto, mai sopra."""
        assert cwapu.limita_farnsworth(25, 20) == 20

    def test_dentro_l_intervallo_resta_com_e(self):
        assert cwapu.limita_farnsworth(8, 20) == 8


class TestPavimentoVelocita:
    def test_senza_farnsworth_e_il_minimo_del_motore(self):
        assert cwapu.pavimento_velocita(0) == cwapu.WPM_MIN

    def test_con_il_farnsworth_e_il_farnsworth(self):
        """Deciso il 2026-09-17: la velocita' variabile non scende mai sotto il Farnsworth."""
        assert cwapu.pavimento_velocita(8) == 8

    def test_non_scende_comunque_sotto_il_minimo(self):
        assert cwapu.pavimento_velocita(3) == cwapu.WPM_MIN


class TestPavimentoAmmesso:
    def test_senza_farnsworth_e_il_minimo_del_motore_senza_interrogarlo(self, monkeypatch):
        motore = MotoreFinto()
        monkeypatch.setattr(cwapu, "CWzator", motore)
        assert cwapu.pavimento_ammesso(0, 20, 30, 50, 50) == cwapu.WPM_MIN
        assert motore.chiamate == []

    def test_con_i_pesi_standard_e_il_farnsworth(self, monkeypatch):
        monkeypatch.setattr(cwapu, "CWzator", MotoreFinto())
        assert cwapu.pavimento_ammesso(15, 20, 30, 50, 50) == 15

    def test_con_gli_spazi_larghi_sale_alla_velocita_che_lo_regge(self, monkeypatch):
        """Era il rilievo della seconda revisione: con s a 75 un Farnsworth di 15 regge a 20 wpm e non a 19."""
        monkeypatch.setattr(cwapu, "CWzator", MotoreFinto(wpm_minimo_col_farnsworth=20))
        assert cwapu.pavimento_ammesso(15, 20, 30, 75, 50) == 20

    def test_non_supera_la_velocita_dei_caratteri(self, monkeypatch):
        monkeypatch.setattr(cwapu, "CWzator", MotoreFinto(wpm_minimo_col_farnsworth=40))
        assert cwapu.pavimento_ammesso(15, 20, 30, 75, 50) == 20

    def test_con_il_motore_vero_i_pesi_standard_non_cambiano_niente(self):
        """Il motore vero a vuoto: con i pesi standard il Farnsworth uguale alla velocita' e' ammesso a ogni velocita'."""
        assert cwapu.pavimento_ammesso(8, 20, 30, 50, 50) == 8

    def test_con_il_motore_vero_gli_spazi_larghi_alzano_il_pavimento(self):
        assert cwapu.pavimento_ammesso(15, 20, 30, 75, 50) > 15


class TestValoreComandoFw:
    def test_numero_attaccato(self):
        assert cwapu.valore_comando_fw(".fw8 ") == 8

    def test_numero_dopo_lo_spazio(self):
        assert cwapu.valore_comando_fw(".fw 12 ") == 12

    def test_maiuscole(self):
        """Come .W 25, anche .FW 8 e' un comando e non un testo da trasmettere."""
        assert cwapu.valore_comando_fw(".FW 8 ") == 8

    def test_senza_numero(self):
        assert cwapu.valore_comando_fw(".fw ") is None

    def test_con_lettere(self):
        assert cwapu.valore_comando_fw(".fw abc ") is None

    def test_le_cifre_che_int_rifiuta_non_passano(self):
        """L'apice due e' una cifra per isdigit ma non per int: un ValueError qui farebbe cadere l'applicazione."""
        assert cwapu.valore_comando_fw(".fw ² ") is None


class TestImpostazioni:
    def test_il_predefinito_e_spento(self):
        assert cwapu.DEFAULT_DATA["overall_settings"]["farnsworth"] == 0

    def test_un_file_vecchio_senza_la_chiave_la_riceve_spenta(self, tmp_path, monkeypatch):
        percorso = tmp_path / "cwapu_settings.json"
        percorso.write_text('{"overall_settings": {"speed": 42}}', encoding="utf-8")
        monkeypatch.setattr(cwapu, "SETTINGS_FILE", str(percorso))
        dati = cwapu.load_settings()
        assert dati["overall_settings"]["farnsworth"] == 0
        assert dati["overall_settings"]["speed"] == 42

    def test_impostato_vuol_dire_diverso_da_zero(self, monkeypatch):
        prepara(monkeypatch, overall_farnsworth=8)
        assert cwapu.farnsworth_impostato() is True
        prepara(monkeypatch, overall_farnsworth=0)
        assert cwapu.farnsworth_impostato() is False


class TestAllineaFarnsworth:
    def test_spento_non_fa_niente(self, monkeypatch, capsys):
        monkeypatch.setattr(cwapu, "CWzator", MotoreFinto())
        prepara(monkeypatch, overall_farnsworth=0)
        assert cwapu.allinea_farnsworth() is None
        assert capsys.readouterr().out == ""

    def test_coerente_resta_com_e(self, monkeypatch, capsys):
        monkeypatch.setattr(cwapu, "CWzator", MotoreFinto())
        prepara(monkeypatch, overall_farnsworth=8)
        assert cwapu.allinea_farnsworth() is None
        assert cwapu.overall_farnsworth == 8
        assert capsys.readouterr().out == ""

    def test_scende_con_la_velocita_dei_caratteri(self, monkeypatch, capsys):
        """Era il difetto di F9 nel contest e della domanda di Rxing: la velocita' scendeva e il Farnsworth restava sopra."""
        monkeypatch.setattr(cwapu, "CWzator", MotoreFinto())
        prepara(monkeypatch, overall_speed=10, overall_farnsworth=15)
        assert cwapu.allinea_farnsworth() == 10
        assert cwapu.overall_farnsworth == 10
        assert "FW portato a 10" in capsys.readouterr().out

    def test_scende_al_massimo_che_i_pesi_consentono(self, monkeypatch, capsys):
        """Era il difetto di .s: uno spazio piu' largo lasciava un Farnsworth che il motore rifiutava a ogni messaggio."""
        monkeypatch.setattr(cwapu, "CWzator", MotoreFinto(farnsworth_massimo=16))
        prepara(monkeypatch, overall_speed=20, overall_farnsworth=18)
        assert cwapu.allinea_farnsworth() == 16
        assert "FW portato a 16" in capsys.readouterr().out

    def test_si_spegne_se_nessun_valore_e_ammesso(self, monkeypatch, capsys):
        monkeypatch.setattr(cwapu, "CWzator", MotoreFinto(farnsworth_massimo=2))
        prepara(monkeypatch, overall_speed=20, overall_farnsworth=18)
        assert cwapu.allinea_farnsworth() == 0
        assert cwapu.overall_farnsworth == 0
        assert "FW spento" in capsys.readouterr().out


class TestFarnsworthAmmesso:
    def test_prova_a_vuoto_senza_suonare(self, monkeypatch):
        motore = MotoreFinto()
        monkeypatch.setattr(cwapu, "CWzator", motore)
        assert cwapu.farnsworth_ammesso(8, 20, 30, 50, 50) is True
        assert motore.chiamate[0]["play"] is False
        assert motore.chiamate[0]["farnsworth"] == 8

    def test_dice_no_quando_il_motore_rifiuta(self, monkeypatch):
        monkeypatch.setattr(cwapu, "CWzator", MotoreFinto(farnsworth_massimo=6))
        assert cwapu.farnsworth_ammesso(8, 20, 30, 75, 50) is False


class TestSuona:
    def test_passa_il_farnsworth_impostato(self, monkeypatch):
        motore = MotoreFinto()
        monkeypatch.setattr(cwapu, "CWzator", motore)
        prepara(monkeypatch, overall_farnsworth=8)
        handle, rwpm = cwapu.suona("paris")
        assert handle is not None
        assert motore.chiamate[0]["farnsworth"] == 8
        assert rwpm == pytest.approx(8.0)

    def test_spento_in_k_passa_none(self, monkeypatch):
        motore = MotoreFinto()
        monkeypatch.setattr(cwapu, "CWzator", motore)
        prepara(monkeypatch)
        cwapu.suona("paris")
        assert motore.chiamate[0]["farnsworth"] is None

    def test_zero_esplicito_lo_spegne_anche_se_impostato(self, monkeypatch):
        """E' la strada del contest, dove il Farnsworth non esiste per decisione presa."""
        motore = MotoreFinto()
        monkeypatch.setattr(cwapu, "CWzator", motore)
        prepara(monkeypatch, overall_farnsworth=8)
        cwapu.suona("cq", farnsworth=0)
        assert motore.chiamate[0]["farnsworth"] is None

    def test_se_il_motore_rifiuta_il_farnsworth_lo_dice_e_suona_senza(self, monkeypatch, capsys):
        motore = MotoreFinto(farnsworth_massimo=6)
        monkeypatch.setattr(cwapu, "CWzator", motore)
        prepara(monkeypatch, overall_farnsworth=8)
        handle, rwpm = cwapu.suona("paris")
        assert handle is not None
        assert [c["farnsworth"] for c in motore.chiamate] == [8, None]
        assert "Farnsworth" in capsys.readouterr().out
        assert rwpm == pytest.approx(20.0)

    def test_un_rifiuto_che_non_riguarda_il_farnsworth_non_si_ritenta(self, monkeypatch, capsys):
        """Con un Farnsworth impostato, un errore d'altra natura non gli va attribuito: una chiamata sola e il messaggio generico."""
        motore = MotoreFinto(rifiuta_sempre=True)
        monkeypatch.setattr(cwapu, "CWzator", motore)
        prepara(monkeypatch, overall_farnsworth=8)
        handle, _rwpm = cwapu.suona("paris")
        assert handle is None
        assert len(motore.chiamate) == 1
        uscita = capsys.readouterr().out
        assert "Farnsworth non applicato" not in uscita
        assert "non ha trasmesso" in uscita

    def test_gli_altri_parametri_non_cambiano(self, monkeypatch):
        motore = MotoreFinto()
        monkeypatch.setattr(cwapu, "CWzator", motore)
        prepara(monkeypatch)
        cwapu.suona("paris", wpm=30, pitch=700)
        chiamata = motore.chiamate[0]
        assert chiamata["wpm"] == 30
        assert chiamata["pitch"] == 700
        assert chiamata["l"] == 30 and chiamata["s"] == 50 and chiamata["p"] == 50


class TestContest:
    def test_ogni_messaggio_del_contest_spegne_il_farnsworth(self):
        """Decisione presa: nel contest il Farnsworth non esiste. Ogni suona() dentro RxingContest deve dirlo."""
        sorgente = inspect.getsource(cwapu.RxingContest)
        chiamate = re.findall(r"suona\((.*)\)", sorgente)
        assert chiamate, "nessuna chiamata a suona nel contest?"
        for argomenti in chiamate:
            assert "farnsworth=0" in argomenti, argomenti
