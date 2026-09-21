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
        self.chiesto = []

    def __call__(self, prompt="", attesa=None, alla_scadenza=""):
        self.chiesto.append(prompt)
        return self.tasti.pop(0) if self.tasti else "\r"


def banco(monkeypatch, *tasti):
    """Mette la tastiera finta e la restituisce, cosi' si leggono anche i prompt."""
    tastiera = Tastiera(*tasti)
    monkeypatch.setattr(cwapu, "key", tastiera)
    monkeypatch.setattr(cwapu, "suona", lambda *a, **k: (None, 0.0))
    monkeypatch.setattr(cwapu, "app_data", copy.deepcopy(cwapu.DEFAULT_DATA), raising=False)
    return tastiera


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


class TestSommario:
    """La riga di riepilogo in fondo al pannello: quadre acceso, angolari spento."""

    def leggi(self, monkeypatch, voci, stati):
        """Il riepilogo sta nel prompt che il pannello passa a key, non a schermo."""
        tastiera = banco(monkeypatch)
        cwapu.pannello_interruttori(voci, stati, "titolo")
        return tastiera.chiesto[-1]

    def test_acceso_fra_quadre_e_spento_fra_angolari(self, monkeypatch):
        letto = self.leggi(monkeypatch, [VOCE_SEMPLICE, VOCE_CON_VALORE], {"acceso": True, "qrm": False, "quante": 2})
        assert "[1]" in letto and "<2>" in letto, letto

    def test_la_voce_di_solo_valore_a_zero_e_spenta(self, monkeypatch):
        """Lo stereo a zero non allarga niente: nel riepilogo si legge spento."""
        assert "<3>" in self.leggi(monkeypatch, [VOCE_SOLO_VALORE], {"stereo": 0})

    def test_la_voce_di_solo_valore_diversa_da_zero_e_accesa(self, monkeypatch):
        assert "[3]" in self.leggi(monkeypatch, [VOCE_SOLO_VALORE], {"stereo": 60})

    def test_il_prompt_sta_fra_due_ritorni_carrello(self, monkeypatch):
        """Cosi' il focus, e quindi il display braille, ci resta sopra."""
        letto = self.leggi(monkeypatch, [VOCE_SEMPLICE], {"acceso": True})
        assert letto.startswith("\r") and letto.endswith("\r")


class TestImpostazioniContest:
    def test_i_predefiniti_riempiono_le_chiavi_che_mancano(self, monkeypatch):
        monkeypatch.setattr(cwapu, "app_data", {"contest_settings": {"pileup": True}}, raising=False)
        stati = cwapu.impostazioni_contest()
        assert stati["pileup"] is True
        assert stati["attivita"] == cwapu.CONTEST_PREDEFINITI["attivita"]
        assert stati["banda"] == 500

    def test_le_chiavi_vecchie_del_manipolo_si_leggono_lo_stesso(self, monkeypatch):
        """Si sono chiamate manipolo per un giorno solo, il 20 settembre 2026:
        un file salvato quel giorno non deve tornare ai predefiniti in silenzio."""
        monkeypatch.setattr(cwapu, "app_data", {"contest_settings": {"manipolo": False, "manipolo_l_min": 44}}, raising=False)
        stati = cwapu.impostazioni_contest()
        assert stati["tasto_verticale"] is False
        assert stati["tasto_l_min"] == 44
        assert "manipolo" not in stati and "manipolo_l_min" not in stati

    def test_le_chiavi_che_non_conosco_non_entrano(self, monkeypatch):
        monkeypatch.setattr(cwapu, "app_data", {"contest_settings": {"roba_vecchia": 7}}, raising=False)
        assert "roba_vecchia" not in cwapu.impostazioni_contest()

    def test_senza_niente_salvato_valgono_i_predefiniti(self, monkeypatch):
        monkeypatch.setattr(cwapu, "app_data", {}, raising=False)
        assert cwapu.impostazioni_contest() == cwapu.CONTEST_PREDEFINITI


class TestPesiDelTasto:
    def test_con_il_tasto_verticale_spento_la_probabilita_e_zero(self):
        stati = dict(cwapu.CONTEST_PREDEFINITI, tasto_verticale=False)
        assert cwapu.pesi_del_tasto(stati)[0] == 0

    def test_acceso_porta_i_valori_del_pannello(self):
        stati = dict(cwapu.CONTEST_PREDEFINITI)
        assert cwapu.pesi_del_tasto(stati) == (30, (30, 60), (25, 75), (15, 50))

    def test_il_massimo_non_puo_scendere_sotto_il_minimo(self, monkeypatch):
        """Il massimo si chiede con il minimo come limite inferiore."""
        chieste = []

        def finto_dgt(**chiavi):
            chieste.append(chiavi)
            return chiavi["imin"]

        monkeypatch.setattr(cwapu, "dgt", finto_dgt)
        stati = dict(cwapu.CONTEST_PREDEFINITI)
        cwapu.chiedi_pesi_tasto(stati)
        assert stati["tasto_l_min"] == 1 and stati["tasto_l_max"] == 1
        # Sette domande: la probabilita' e i tre intervalli.
        assert len(chieste) == 7
        for prima, dopo in zip(chieste[1::2], chieste[2::2], strict=True):
            assert dopo["imin"] == prima["imin"]


class TestPannelloContest:
    def test_gli_effetti_si_accendono_se_gbutils_li_sa_fare(self, monkeypatch):
        for numero, chiave in (("1", "qrn"), ("3", "qsb"), ("4", "flutter")):
            banco(monkeypatch, numero)
            stati = cwapu.pannello_contest()
            assert stati is not None
            assert stati[chiave] is (chiave not in cwapu.CONTEST_NON_DISPONIBILI)

    def test_un_effetto_che_gbutils_non_sa_fare_resta_spento(self, monkeypatch):
        """Con una GBUtils vecchia l'interruttore c'e' e dice che non e' il momento."""
        banco(monkeypatch, "1")
        monkeypatch.setattr(cwapu, "CONTEST_NON_DISPONIBILI", ("qrn",))
        assert cwapu.pannello_contest()["qrn"] is False

    def test_con_la_gbutils_di_oggi_gli_effetti_ci_sono_tutti(self):
        """La V165 porta il qsb di CWzator e il ciclo di Acusticator."""
        assert cwapu.effetti_non_disponibili() == ()

    def test_l_escape_esce_senza_stati(self, monkeypatch):
        banco(monkeypatch, "\x1b")
        assert cwapu.pannello_contest() is None

    def test_cio_che_si_sceglie_si_salva(self, monkeypatch):
        banco(monkeypatch, "5")
        stati = cwapu.pannello_contest()
        assert stati["sbadati"] is False
        assert cwapu.app_data["contest_settings"]["sbadati"] is False


class TestBanda:
    """Il passo di cinquanta della larghezza del filtro."""

    def test_il_mezzo_sale_sempre(self):
        """round di Python manderebbe 325 a 300 e 375 a 400: due valori a
        mezza via che si comportano in modo opposto non si spiegano."""
        assert cwapu.arrotonda_banda(325) == 350
        assert cwapu.arrotonda_banda(375) == 400

    def test_gli_altri_vanno_al_passo_piu_vicino(self):
        assert [cwapu.arrotonda_banda(v) for v in (324, 326, 349, 350, 374)] == [300, 350, 350, 350, 350]

    def test_resta_dentro_i_limiti(self):
        assert cwapu.arrotonda_banda(10) == cwapu.CONTEST_BANDA_MIN
        assert cwapu.arrotonda_banda(9999) == cwapu.CONTEST_BANDA_MAX
        assert cwapu.arrotonda_banda(100) == 100 and cwapu.arrotonda_banda(600) == 600


class TestSelezioneRx:
    """Il pannello degli esercizi Rx dopo il refactoring.

    Sono centosessanta righe che Gabriele usa tutti i giorni e che prima non
    erano coperte da niente: adesso la tecnica sta in pannello_interruttori e
    qui restano le regole degli esercizi, cioe' l'esclusione fra i gruppi, il
    filtro delle parole, il set personalizzato e la lunghezza dei gruppi.
    """

    def prepara(self, monkeypatch, *tasti, lunghezza="5"):
        banco(monkeypatch, *tasti)
        monkeypatch.setattr(cwapu, "words", ["cq", "test", "morse", "radio", "antenna"], raising=False)
        monkeypatch.setattr(cwapu, "overall_speed", 20, raising=False)
        monkeypatch.setattr("builtins.input", lambda: lunghezza)

    def test_con_le_parole_accese_torna_l_elenco_filtrato(self, monkeypatch):
        self.prepara(monkeypatch)
        scelta = cwapu.seleziona_modalita_rx()
        assert scelta is not None
        assert scelta["active_switcher_states"]["parole"] is True
        # Il filtro di serie e' da tre a sette lettere: cq resta fuori.
        assert scelta["parole_filtrate_list"] == ["test", "morse", "radio", "antenna"]
        assert scelta["group_length_for_generated"] == 0

    def test_l_escape_torna_al_menu_senza_scegliere(self, monkeypatch):
        self.prepara(monkeypatch, "\x1b")
        assert cwapu.seleziona_modalita_rx() is None

    def test_accendendo_le_lettere_le_parole_si_spengono(self, monkeypatch):
        """L'esclusione fra i gruppi e' la regola che tiene confrontabili le statistiche."""
        self.prepara(monkeypatch, "2")
        scelta = cwapu.seleziona_modalita_rx()
        assert scelta["active_switcher_states"]["lettere"] is True
        assert scelta["active_switcher_states"]["parole"] is False
        assert scelta["parole_filtrate_list"] is None
        # Con i gruppi generati si chiede la lunghezza, e quella risposta vale.
        assert scelta["group_length_for_generated"] == 5

    def test_una_lunghezza_fuori_intervallo_non_passa(self, monkeypatch):
        """La domanda si ripete finche' la risposta non sta fra uno e sette."""
        risposte = iter(["9", "0", "3"])
        self.prepara(monkeypatch, "2")
        monkeypatch.setattr("builtins.input", lambda: next(risposte))
        assert cwapu.seleziona_modalita_rx()["group_length_for_generated"] == 3

    def test_senza_nessuno_switcher_acceso_non_si_comincia(self, monkeypatch):
        """Il primo Invio viene respinto, il secondo, dopo aver acceso, no."""
        self.prepara(monkeypatch, "1", "\r", "3")
        scelta = cwapu.seleziona_modalita_rx()
        assert scelta["active_switcher_states"]["numeri"] is True
        assert scelta["active_switcher_states"]["parole"] is False

    def test_il_filtro_delle_parole_che_non_pesca_niente_spegne_lo_switcher(self, monkeypatch):
        self.prepara(monkeypatch, "1", "1", "3")
        cwapu.app_data["rx_menu_switcher_states"]["parole_filter_min"] = 30
        cwapu.app_data["rx_menu_switcher_states"]["parole_filter_max"] = 35
        scelta = cwapu.seleziona_modalita_rx()
        assert scelta["active_switcher_states"]["parole"] is False
        assert scelta["parole_filtrate_list"] is None

    def test_il_set_personalizzato_si_chiede_quando_manca(self, monkeypatch):
        self.prepara(monkeypatch, "6")
        monkeypatch.setattr(cwapu, "CustomSet", lambda velocita: "abc")
        scelta = cwapu.seleziona_modalita_rx()
        assert scelta["active_switcher_states"]["custom"] is True
        assert scelta["custom_set_string_active"] == "abc"
        assert cwapu.app_data["rx_menu_switcher_states"]["custom_set_string"] == "abc"

    def test_un_set_personalizzato_troppo_corto_spegne_lo_switcher(self, monkeypatch):
        self.prepara(monkeypatch, "6", "3")
        monkeypatch.setattr(cwapu, "CustomSet", lambda velocita: "a")
        scelta = cwapu.seleziona_modalita_rx()
        assert scelta["active_switcher_states"]["custom"] is False
        assert scelta["custom_set_string_active"] is None

    def test_cio_che_si_sceglie_resta_per_la_volta_dopo(self, monkeypatch):
        self.prepara(monkeypatch, "3")
        cwapu.seleziona_modalita_rx()
        salvati = cwapu.app_data["rx_menu_switcher_states"]
        assert salvati["numeri"] is True and salvati["parole"] is False


@pytest.mark.parametrize("chiave", sorted(cwapu.CONTEST_PREDEFINITI))
def test_ogni_predefinito_sta_nelle_impostazioni_di_serie(chiave):
    assert chiave in cwapu.DEFAULT_DATA["contest_settings"]
