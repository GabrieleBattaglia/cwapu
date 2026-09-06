# Prove automatiche di CWapu, parte esercizi.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' UltraCode).
# Coprono il tetto della velocita', la mutua esclusione degli switcher, la
# generazione dei gruppi e la ripulitura del testo copiato dagli appunti.
# Nessuna di queste prove suona: il motore CW non viene mai chiamato.

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cwapu


class TestTettoVelocita:
    def test_i_valori_dentro_l_intervallo_non_si_toccano(self):
        for velocita in (5, 18, 85, 110, 120):
            assert cwapu.limita_wpm(velocita) == velocita

    def test_sopra_il_massimo_si_ferma_al_massimo(self):
        """Oltre il tetto il motore CW rifiutava il messaggio e non suonava.

        Era il muro contro cui andava F10 nel contest: niente errore, niente
        avviso, semplicemente il silenzio.
        """
        assert cwapu.limita_wpm(200) == cwapu.WPM_MAX
        assert cwapu.limita_wpm(121) == cwapu.WPM_MAX

    def test_sotto_il_minimo_si_ferma_al_minimo(self):
        assert cwapu.limita_wpm(1) == cwapu.WPM_MIN
        assert cwapu.limita_wpm(-30) == cwapu.WPM_MIN

    def test_il_tetto_non_supera_quello_del_motore(self):
        """Se un domani CWzator abbassasse il proprio limite, questa prova
        avviserebbe prima che l'utente si ritrovi muto."""
        assert cwapu.WPM_MAX <= 120
        assert cwapu.WPM_MIN >= 5


class TestEsclusioneSwitcher:
    def stato(self, accesi):
        stati = {v["key_state"]: False for v in cwapu.RX_SWITCHER_ITEMS}
        for chiave in accesi:
            stati[chiave] = True
        return stati

    def accesi_dopo(self, gia_accesi, chiave):
        stati = self.stato([*gia_accesi, chiave])
        cwapu.applica_esclusione_switcher(stati, chiave)
        return {k for k, v in stati.items() if v}

    def test_i_gruppi_di_caratteri_stanno_insieme(self):
        """Lettere, numeri, misto, simboli e il gruppo personalizzato sono
        oggetti confrontabili: mescolarli non svuota di senso la statistica."""
        assert self.accesi_dopo(["lettere"], "numeri") == {"lettere", "numeri"}
        assert self.accesi_dopo(["lettere", "numeri"], "custom") == {"lettere", "numeri", "custom"}
        assert self.accesi_dopo(["custom"], "simboli") == {"custom", "simboli"}

    def test_le_parole_escludono_tutto_il_resto(self):
        assert self.accesi_dopo(["lettere", "numeri"], "parole") == {"parole"}
        assert self.accesi_dopo(["parole"], "lettere") == {"lettere"}

    def test_qrz_e_contest_escludono_tutto_il_resto_e_fra_loro(self):
        assert self.accesi_dopo(["lettere", "custom"], "qrz") == {"qrz"}
        assert self.accesi_dopo(["qrz"], "contest") == {"contest"}
        assert self.accesi_dopo(["contest"], "qrz") == {"qrz"}

    def test_una_chiave_sconosciuta_non_spegne_niente(self):
        stati = self.stato(["lettere", "numeri"])
        cwapu.applica_esclusione_switcher(stati, "inesistente")
        assert {k for k, v in stati.items() if v} == {"lettere", "numeri"}

    def test_le_chiavi_degli_switcher_sono_quelle_salvate_su_disco(self):
        """La chiave non si traduce mai, l'etichetta sempre.

        Erano la stessa cosa: finche' il catalogo inglese e' rimasto vuoto non
        si e' visto niente, ma alla prima traduzione vera la chiave sarebbe
        diventata 'words' e la lettura di rx_menu_switcher_states, che ha le
        chiavi in italiano, sarebbe finita in KeyError.
        """
        salvate = set(cwapu.DEFAULT_DATA["rx_menu_switcher_states"])
        for voce in cwapu.RX_SWITCHER_ITEMS:
            assert voce["key_state"] in salvate, f"{voce['key_state']} non e' fra le chiavi salvate"
            assert voce["etichetta"], f"{voce['key_state']} non ha etichetta"

    def test_ogni_switcher_ha_un_gruppo_e_un_numero_suo(self):
        numeri = [v["id"] for v in cwapu.RX_SWITCHER_ITEMS]
        assert len(numeri) == len(set(numeri))
        for voce in cwapu.RX_SWITCHER_ITEMS:
            assert voce["category_group"]


class TestGenerazioneGruppi:
    def test_lunghezza_richiesta_rispettata(self):
        for tipo in ("1", "2", "3", "S"):
            gruppo = cwapu.GeneratingGroup(kind=tipo, length=5, wpm=20)
            assert len(gruppo) == 5, f"tipo {tipo}"

    def test_solo_lettere_e_solo_numeri(self):
        lettere = cwapu.GeneratingGroup(kind="1", length=20, wpm=20)
        assert lettere.isalpha()
        numeri = cwapu.GeneratingGroup(kind="2", length=20, wpm=20)
        assert numeri.isdigit()

    def test_il_gruppo_personalizzato_pesca_solo_dal_suo_insieme(self):
        gruppo = cwapu.GeneratingGroup(kind="4", length=30, wpm=20, customized_set_param="kmq")
        assert set(gruppo) <= set("kmq")

    def test_il_gruppo_personalizzato_vuoto_lo_dice(self):
        assert cwapu.GeneratingGroup(kind="4", length=5, wpm=20, customized_set_param="") == "ERR_CS"


class TestRipulituraAppunti:
    def test_i_caratteri_ammessi_passano(self):
        assert cwapu.StringCleaning("CQ de IZ4APU") == "cq de iz4apu"

    def test_gli_spazi_multipli_diventano_uno(self):
        assert cwapu.StringCleaning("  cq    de   ") == "cq de"

    def test_i_simboli_fuori_elenco_vengono_tolti(self):
        """La classe conteneva un intervallo scritto per sbaglio, e lasciava
        passare cifre e simboli che nessuno aveva elencato."""
        ripulito = cwapu.StringCleaning("a<b>c#d")
        assert "<" not in ripulito
        assert ">" not in ripulito
        assert "#" not in ripulito
        assert ripulito == "abcd"

    def test_i_simboli_elencati_restano(self):
        ripulito = cwapu.StringCleaning("prova (uno) = due - tre")
        for simbolo in "()=-":
            assert simbolo in ripulito
