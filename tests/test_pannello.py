# Prove automatiche di CWapu, il pannello a interruttori.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' auto).
# Nate con la tappa 5 del piano della issue 7, quando le centosessanta righe
# del pannello degli esercizi Rx sono diventate una funzione sola, usata anche
# dal contest. Prima non le collaudava niente.

import copy
import os
import sys

import pytest

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)

import cwapu  # noqa: E402


class Tastiera:
    """Restituisce i tasti del copione, e poi l'Invio per non restare appesa."""

    def __init__(self, *tasti):
        self.tasti = list(tasti)

    def __call__(self, prompt="", attesa=None, alla_scadenza=""):
        return self.tasti.pop(0) if self.tasti else "\r"


def banco(monkeypatch, *tasti):
    monkeypatch.setattr(cwapu, "key", Tastiera(*tasti))
    monkeypatch.setattr(cwapu, "suona", lambda *a, **k: (None, 0.0))
    monkeypatch.setattr(cwapu, "app_data", copy.deepcopy(cwapu.DEFAULT_DATA), raising=False)


VOCE_SEMPLICE = {"id": "1", "key_state": "acceso", "etichetta": "prova"}
VOCE_CON_VALORE = {
    "id": "2",
    "key_state": "qrm",
    "etichetta": "QRM",
    "valore": "quante",
    "chiedi": lambda salvato: (salvato or 0) + 1,
    "descrivi": lambda stati: f"{stati['quante']} stazioni",
}
VOCE_SOLO_VALORE = {
    "id": "3",
    "etichetta": "stereo",
    "valore": "stereo",
    "chiedi": lambda salvato: 42,
    "descrivi": lambda stati: f"{stati['stereo']} su 100",
}


class TestRiga:
    def test_acceso_e_spento_si_leggono_dal_nome_e_dall_indicatore(self):
        assert cwapu.riga_interruttore(VOCE_SEMPLICE, {"acceso": True}) == "1. PROVA <X> ATTIVATO"
        assert cwapu.riga_interruttore(VOCE_SEMPLICE, {"acceso": False}) == "1. prova < > disattivato"

    def test_il_valore_sta_nella_stessa_frase(self):
        riga = cwapu.riga_interruttore(VOCE_CON_VALORE, {"qrm": True, "quante": 2})
        assert riga == "2. QRM <X> ATTIVATO, 2 stazioni"

    def test_da_spenta_il_valore_non_si_legge(self):
        assert cwapu.riga_interruttore(VOCE_CON_VALORE, {"qrm": False, "quante": 2}) == "2. qrm < > disattivato"

    def test_la_voce_di_solo_valore_non_ha_indicatore(self):
        assert cwapu.riga_interruttore(VOCE_SOLO_VALORE, {"stereo": 100}) == "3. stereo, 100 su 100"

    def test_ogni_riga_del_contest_sta_in_una_frase_breve(self):
        """Il piano vuole righe da leggere di seguito, non paragrafi."""
        stati = dict(cwapu.CONTEST_PREDEFINITI)
        for voce in cwapu.CONTEST_VOCI:
            riga = cwapu.riga_interruttore(voce, stati)
            assert riga.startswith(voce["id"] + ". ")
            assert len(riga) <= 80


class TestPannello:
    def test_l_invio_conferma(self, monkeypatch):
        banco(monkeypatch)
        stati = {"acceso": False}
        assert cwapu.pannello_interruttori([VOCE_SEMPLICE], stati, "titolo") is True
        assert stati == {"acceso": False}

    def test_l_escape_annulla(self, monkeypatch):
        banco(monkeypatch, "\x1b")
        assert cwapu.pannello_interruttori([VOCE_SEMPLICE], {"acceso": False}, "titolo") is False

    def test_il_numero_accende_e_rispegne(self, monkeypatch):
        banco(monkeypatch, "1", "1", "1")
        stati = {"acceso": False}
        cwapu.pannello_interruttori([VOCE_SEMPLICE], stati, "titolo")
        assert stati["acceso"] is True

    def test_accendendo_una_voce_con_valore_lo_si_chiede_subito(self, monkeypatch):
        banco(monkeypatch, "2")
        stati = {"qrm": False, "quante": 1}
        cwapu.pannello_interruttori([VOCE_CON_VALORE], stati, "titolo")
        assert stati["qrm"] is True
        assert stati["quante"] == 2

    def test_spegnendola_il_valore_non_si_chiede(self, monkeypatch):
        banco(monkeypatch, "2")
        stati = {"qrm": True, "quante": 1}
        cwapu.pannello_interruttori([VOCE_CON_VALORE], stati, "titolo")
        assert stati["qrm"] is False
        assert stati["quante"] == 1

    def test_la_voce_di_solo_valore_chiede_e_basta(self, monkeypatch):
        banco(monkeypatch, "3")
        stati = {"stereo": 100}
        cwapu.pannello_interruttori([VOCE_SOLO_VALORE], stati, "titolo")
        assert stati["stereo"] == 42

    def test_un_numero_che_non_c_e_lo_dice(self, monkeypatch):
        banco(monkeypatch, "9")
        stati = {"acceso": False}
        cwapu.pannello_interruttori([VOCE_SEMPLICE], stati, "titolo")
        assert stati["acceso"] is False

    def test_alla_conferma_puo_trattenere(self, monkeypatch):
        banco(monkeypatch, "\r", "1")
        stati = {"acceso": False}
        visti = []

        def alla_conferma(stati, riga):
            visti.append(dict(stati))
            return "" if stati["acceso"] else "serve almeno una voce"

        assert cwapu.pannello_interruttori([VOCE_SEMPLICE], stati, "titolo", alla_conferma=alla_conferma) is True
        # Il primo Invio e' stato respinto, il secondo, dopo aver acceso, no.
        assert [v["acceso"] for v in visti] == [False, True]

    def test_al_cambio_vede_ogni_cambio(self, monkeypatch):
        banco(monkeypatch, "1")
        visti = []
        cwapu.pannello_interruttori([VOCE_SEMPLICE], {"acceso": False}, "titolo", al_cambio=lambda stati, voce: visti.append(voce["id"]) or "")
        assert visti == ["1"]


class TestImpostazioniContest:
    def test_i_predefiniti_riempiono_le_chiavi_che_mancano(self, monkeypatch):
        monkeypatch.setattr(cwapu, "app_data", {"contest_settings": {"pileup": True}}, raising=False)
        stati = cwapu.impostazioni_contest()
        assert stati["pileup"] is True
        assert stati["attivita"] == cwapu.CONTEST_PREDEFINITI["attivita"]
        assert stati["banda"] == 500

    def test_le_chiavi_che_non_conosco_non_entrano(self, monkeypatch):
        monkeypatch.setattr(cwapu, "app_data", {"contest_settings": {"roba_vecchia": 7}}, raising=False)
        assert "roba_vecchia" not in cwapu.impostazioni_contest()

    def test_senza_niente_salvato_valgono_i_predefiniti(self, monkeypatch):
        monkeypatch.setattr(cwapu, "app_data", {}, raising=False)
        assert cwapu.impostazioni_contest() == cwapu.CONTEST_PREDEFINITI


class TestPesiDelManipolo:
    def test_con_il_manipolo_spento_la_probabilita_e_zero(self):
        stati = dict(cwapu.CONTEST_PREDEFINITI, manipolo=False)
        assert cwapu.pesi_del_manipolo(stati)[0] == 0

    def test_acceso_porta_i_valori_del_pannello(self):
        stati = dict(cwapu.CONTEST_PREDEFINITI)
        assert cwapu.pesi_del_manipolo(stati) == (30, (30, 60), (25, 75), (15, 50))

    def test_il_massimo_non_puo_scendere_sotto_il_minimo(self, monkeypatch):
        """Il massimo si chiede con il minimo come limite inferiore."""
        chieste = []

        def finto_dgt(**chiavi):
            chieste.append(chiavi)
            return chiavi["imin"]

        monkeypatch.setattr(cwapu, "dgt", finto_dgt)
        stati = dict(cwapu.CONTEST_PREDEFINITI)
        cwapu.chiedi_pesi_manipolo(stati)
        assert stati["manipolo_l_min"] == 1 and stati["manipolo_l_max"] == 1
        # Sette domande: la probabilita' e i tre intervalli.
        assert len(chieste) == 7
        for prima, dopo in zip(chieste[1::2], chieste[2::2], strict=True):
            assert dopo["imin"] == prima["imin"]


class TestPannelloContest:
    def test_gli_effetti_che_non_ci_sono_ancora_restano_spenti(self, monkeypatch):
        for numero, chiave in (("1", "qrn"), ("3", "qsb"), ("4", "flutter")):
            banco(monkeypatch, numero)
            stati = cwapu.pannello_contest()
            assert stati is not None
            assert stati[chiave] is False

    def test_l_escape_esce_senza_stati(self, monkeypatch):
        banco(monkeypatch, "\x1b")
        assert cwapu.pannello_contest() is None

    def test_cio_che_si_sceglie_si_salva(self, monkeypatch):
        banco(monkeypatch, "5")
        stati = cwapu.pannello_contest()
        assert stati["sbadati"] is False
        assert cwapu.app_data["contest_settings"]["sbadati"] is False


@pytest.mark.parametrize("chiave", sorted(cwapu.CONTEST_PREDEFINITI))
def test_ogni_predefinito_sta_nelle_impostazioni_di_serie(chiave):
    assert chiave in cwapu.DEFAULT_DATA["contest_settings"]
