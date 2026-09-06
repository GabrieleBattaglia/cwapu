# Prove automatiche di CWapu, intervallo di Wilson.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' UltraCode).
# Il punteggio di Wilson decide quali dieci caratteri finiscono nel gruppo
# personalizzato, e quale intervallo di errore compare nel diario. Con pochi
# invii la media semplice mente, e mente in modo asimmetrico: e' esattamente
# il caso di chi si allena, che sui caratteri rari ha una manciata di prove.

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wilson import wilson_score_lower_bound, wilson_score_upper_bound


class TestCasiLimite:
    def test_senza_invii_non_si_esclude_niente(self):
        """Zero invii vuol dire nessuna informazione, non zero errori."""
        assert wilson_score_lower_bound(0, 0) == 0
        assert wilson_score_upper_bound(0, 0) == 1.0

    def test_gli_errori_non_possono_superare_gli_invii(self):
        """Un conteggio sballato produrrebbe la radice di un numero negativo."""
        inferiore = wilson_score_lower_bound(30, 10)
        superiore = wilson_score_upper_bound(30, 10)
        assert inferiore == wilson_score_lower_bound(10, 10)
        assert superiore == wilson_score_upper_bound(10, 10)

    def test_i_limiti_restano_fra_zero_e_uno(self):
        for invii in (1, 5, 20, 500):
            for errori in range(invii + 1):
                inferiore = wilson_score_lower_bound(errori, invii)
                superiore = wilson_score_upper_bound(errori, invii)
                assert 0 <= inferiore <= 1
                assert 0 <= superiore <= 1


class TestOrdinamento:
    def test_l_inferiore_non_supera_mai_il_superiore(self):
        for invii in (1, 3, 10, 100):
            for errori in range(invii + 1):
                assert wilson_score_lower_bound(errori, invii) <= wilson_score_upper_bound(errori, invii)

    def test_piu_errori_alza_entrambi_i_limiti(self):
        assert wilson_score_lower_bound(2, 20) < wilson_score_lower_bound(8, 20)
        assert wilson_score_upper_bound(2, 20) < wilson_score_upper_bound(8, 20)

    def test_piu_prove_stringono_l_intervallo(self):
        """E' il motivo per cui si usa Wilson invece della media semplice."""
        stretto = wilson_score_upper_bound(20, 200) - wilson_score_lower_bound(20, 200)
        largo = wilson_score_upper_bound(2, 20) - wilson_score_lower_bound(2, 20)
        assert stretto < largo

    def test_due_su_due_non_batte_dodici_su_quindici(self):
        """Il caso che la media semplice sbaglia: cento per cento su due prove
        non e' una certezza, e il limite inferiore lo sa."""
        pochi = wilson_score_lower_bound(2, 2)
        molti = wilson_score_lower_bound(12, 15)
        assert pochi < molti


class TestValoriNoti:
    def test_intervallo_di_wilson_su_un_caso_calcolato_a_mano(self):
        """Due errori su venti, confidenza al novantacinque per cento.

        I valori attesi vengono dalla formula standard con z uguale 1,96.
        """
        inferiore = wilson_score_lower_bound(2, 20)
        superiore = wilson_score_upper_bound(2, 20)
        assert abs(inferiore - 0.027860) < 1e-5
        assert abs(superiore - 0.301047) < 1e-5

    def test_la_stima_puntuale_cade_dentro_l_intervallo(self):
        for errori, invii in ((1, 10), (5, 40), (33, 100)):
            stima = errori / invii
            assert wilson_score_lower_bound(errori, invii) <= stima <= wilson_score_upper_bound(errori, invii)
