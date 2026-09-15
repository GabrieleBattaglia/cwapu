# Prove automatiche di CWapu, i comandi della sezione tastiera.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Fable 5.1, modalita' auto).
# Nate con la issue 13: ".m 50" con lo spazio non era un comando e veniva
# trasmesso in CW come testo, e nessuna prova poteva accorgersene perche' il
# parser stava dentro il ciclo interattivo.

import os
import sys

import pytest

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)

import cwapu  # noqa: E402


class TestComandoNumerico:
    def test_numero_attaccato_alla_lettera(self):
        assert cwapu.comando_numerico("m50") == ("m", 50)

    def test_numero_dopo_lo_spazio(self):
        """Era la issue 13: questa forma finiva trasmessa in CW."""
        assert cwapu.comando_numerico("m 50") == ("m", 50)

    def test_lettera_maiuscola_e_spazi_di_troppo(self):
        assert cwapu.comando_numerico("  W  25 ") == ("w", 25)

    def test_il_filtro_delle_parole_non_e_un_comando_numerico(self):
        assert cwapu.comando_numerico("t 3-7") is None

    def test_il_salvataggio_non_e_un_comando_numerico(self):
        assert cwapu.comando_numerico("sv 73") is None

    def test_la_sola_lettera_non_basta(self):
        assert cwapu.comando_numerico("y") is None

    def test_il_numero_deve_essere_intero(self):
        assert cwapu.comando_numerico("m 2.5") is None


class TestRampaMassima:
    def test_a_47_wpm_il_punto_la_limita_a_dodici(self):
        """Misurato il 2026-09-15: a 47 wpm i valori 15, 30, 50 e 200
        producono tutti una rampa di 11,7 millesimi sul punto."""
        assert cwapu.rampa_massima_ms(47, 50) == pytest.approx(12.77, abs=0.01)

    def test_a_18_wpm_arriva_a_trentatre(self):
        assert cwapu.rampa_massima_ms(18, 50) == pytest.approx(33.33, abs=0.01)

    def test_il_peso_del_punto_la_scala(self):
        assert cwapu.rampa_massima_ms(18, 25) == pytest.approx(16.67, abs=0.01)
