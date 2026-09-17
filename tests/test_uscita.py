# Prove automatiche di CWapu, la scelta dell'uscita audio.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Fable 5.1, modalita' auto).
# Nate con la issue 5. L'elenco dei dispositivi e' finto, cosi' le prove non
# dipendono dalla scheda audio della macchina e non aprono niente.

import os
import sys
from types import SimpleNamespace

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)

import cwapu  # noqa: E402


def voce(indice, breve, dispositivo, **altri):
    base = {
        "indice": indice,
        "breve": breve,
        "dispositivo": dispositivo,
        "interfaccia": f"Windows {breve}",
        "canali": 2,
        "frequenza": 48000.0,
        "latenza": 3.0,
        "predefinito": False,
        "stessa_scheda": False,
        "esclusiva": False,
        "apribile": True,
        "motivo": None,
    }
    base.update(altri)
    return base


ELENCO = [
    voce(18, "WASAPI", "Altoparlanti (Realtek)", stessa_scheda=True),
    voce(4, "MME", "Altoparlanti (Realtek)", latenza=90.0, predefinito=True, stessa_scheda=True),
    voce(9, "WDM-KS", "Speakers", latenza=10.0, apribile=False, motivo="PaErrorCode -9999"),
    voce(7, "DirectSound", "Cuffie USB", latenza=120.0),
]

GLOBALI_SUONA = {
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


def prepara(monkeypatch, interfaccia="", dispositivo="", api=None):
    monkeypatch.setattr(cwapu, "overall_uscita_interfaccia", interfaccia, raising=False)
    monkeypatch.setattr(cwapu, "overall_uscita_dispositivo", dispositivo, raising=False)
    monkeypatch.setattr(cwapu, "overall_api", api, raising=False)


def prepara_suona(monkeypatch, motore):
    monkeypatch.setattr(cwapu, "CWzator", motore)
    for nome, valore in GLOBALI_SUONA.items():
        monkeypatch.setattr(cwapu, nome, valore, raising=False)


def motore_finto(scelta=(18, "Windows WASAPI")):
    """Un CWzator finto con i due elenchi e la scelta automatica, senza suonare."""
    return SimpleNamespace(scegli_dispositivo=lambda: scelta, elenco_dispositivi=lambda prova="nessuno": ELENCO)


class TestDescrizione:
    def test_la_riga_dice_tutto_a_parole(self):
        riga = cwapu.descrivi_uscita(ELENCO[0])
        assert riga.startswith("WASAPI, Altoparlanti (Realtek), 3 ms, 48000 Hz")
        assert "stessa scheda" in riga

    def test_il_predefinito_di_sistema_e_segnato(self):
        assert "predefinito" in cwapu.descrivi_uscita(ELENCO[1])

    def test_chi_non_si_apre_lo_dice_con_il_motivo(self):
        riga = cwapu.descrivi_uscita(ELENCO[2])
        assert "non si apre" in riga
        assert "-9999" in riga

    def test_l_esclusiva_dice_cosa_comporta(self):
        """Con una scheda sola, l'esclusiva zittisce anche il lettore di schermo: la parola da sola non basta."""
        riga = cwapu.descrivi_uscita(voce(30, "ASIO", "Realtek ASIO", esclusiva=True))
        assert "NVDA" in riga

    def test_un_nome_con_il_ritorno_a_capo_dentro_sta_su_una_riga(self):
        """Certi driver Bluetooth mettono un ritorno a capo vero nel nome: la riga del menu si spezzerebbe in due."""
        brutta = voce(34, "WDM-KS", "Output (@System32\\drivers\\bthhfenum.sys,#4;%1 Hands-Free HF Audio%0\r\n;(iPhone))")
        riga = cwapu.descrivi_uscita(brutta)
        assert "\n" not in riga and "\r" not in riga
        assert "(iPhone))" in riga
        assert "\n" not in cwapu.descrizione_uscita("WDM-KS", brutta["dispositivo"])

    def test_la_scelta_automatica_si_legge_come_tale(self):
        assert cwapu.descrizione_uscita("", "") == "automatica"
        assert cwapu.descrizione_uscita("WASAPI", "Cuffie") == "WASAPI, Cuffie"


class TestDescrizioneCorrente:
    def test_con_una_scelta_esplicita_dice_quella(self, monkeypatch):
        prepara(monkeypatch, "DirectSound", "Cuffie USB", 7)
        assert cwapu.descrizione_uscita_corrente(ELENCO) == "DirectSound, Cuffie USB"

    def test_in_automatico_dice_anche_dove_va_il_suono(self, monkeypatch):
        """Chi legge "automatica" deve sapere quale riga dell'elenco sta sentendo."""
        prepara(monkeypatch)
        monkeypatch.setattr(cwapu, "CWzator", motore_finto())
        assert cwapu.descrizione_uscita_corrente(ELENCO) == "automatica: WASAPI, Altoparlanti (Realtek)"

    def test_con_la_coppia_salvata_assente_oggi_dice_l_automatica(self, monkeypatch):
        prepara(monkeypatch, "DirectSound", "Scheda staccata", None)
        monkeypatch.setattr(cwapu, "CWzator", motore_finto())
        assert cwapu.descrizione_uscita_corrente(ELENCO).startswith("automatica: WASAPI")

    def test_quando_cwzator_lascia_fare_al_sistema_resta_automatica(self, monkeypatch):
        prepara(monkeypatch)
        monkeypatch.setattr(cwapu, "CWzator", motore_finto(scelta=(None, None)))
        assert cwapu.descrizione_uscita_corrente(ELENCO) == "automatica"


class TestOrdine:
    def test_chi_non_si_apre_va_in_fondo_ma_non_sparisce(self):
        ordinate = cwapu.ordina_uscite(ELENCO)
        assert [v["indice"] for v in ordinate] == [18, 4, 7, 9]


class TestRisoluzione:
    def test_la_coppia_salvata_ritrova_l_indice_di_oggi(self):
        assert cwapu.risolvi_uscita_audio("DirectSound", "Cuffie USB", ELENCO) == 7

    def test_una_periferica_staccata_torna_all_automatica(self):
        """Gli indici cambiano quando si attacca o stacca qualcosa: si salvano i nomi, e se oggi mancano si lascia fare a CWapu."""
        assert cwapu.risolvi_uscita_audio("WASAPI", "Scheda che non c'e'", ELENCO) is None

    def test_la_scelta_automatica_non_cerca_niente(self):
        assert cwapu.risolvi_uscita_audio("", "", ELENCO) is None


class TestScelta:
    def test_scegliere_una_voce_imposta_nomi_e_indice(self, monkeypatch, capsys):
        prepara(monkeypatch)
        esito = cwapu.scegli_uscita_audio(elenco=ELENCO, chiedi=lambda **k: 3, automatica=18)
        assert esito == ("DirectSound", "Cuffie USB")
        assert cwapu.overall_api == 7
        assert cwapu.overall_uscita_interfaccia == "DirectSound"
        uscita = capsys.readouterr().out
        assert "0. Lascia scegliere" in uscita
        assert "4. WDM-KS" in uscita

    def test_in_automatico_l_elenco_segna_la_riga_che_si_sta_sentendo(self, monkeypatch, capsys):
        prepara(monkeypatch)
        cwapu.scegli_uscita_audio(elenco=ELENCO, chiedi=lambda **k: 0, automatica=18)
        righe = capsys.readouterr().out.splitlines()
        assert any(r.startswith("1. WASAPI") and "sceglie adesso" in r for r in righe)
        assert not any("scelta adesso" in r for r in righe)

    def test_lo_zero_torna_all_automatica(self, monkeypatch):
        prepara(monkeypatch, "WASAPI", "Altoparlanti (Realtek)", 18)
        esito = cwapu.scegli_uscita_audio(elenco=ELENCO, chiedi=lambda **k: 0, automatica=18)
        assert esito == ("", "")
        assert cwapu.overall_api is None
        assert cwapu.overall_uscita_interfaccia == ""

    def test_lo_zero_cancella_anche_una_coppia_salvata_che_oggi_non_c_e(self, monkeypatch, capsys):
        """Era un rilievo della revisione: con l'uscita salvata assente, lo zero non faceva niente e l'avviso tornava a ogni avvio."""
        prepara(monkeypatch, "DirectSound", "Scheda staccata", None)
        esito = cwapu.scegli_uscita_audio(elenco=ELENCO, chiedi=lambda **k: 0, automatica=18)
        assert esito == ("", "")
        assert cwapu.overall_uscita_interfaccia == ""
        uscita = capsys.readouterr().out
        assert "oggi non c'è" in uscita
        assert "scelta adesso" not in uscita

    def test_lo_zero_con_l_automatica_gia_attiva_non_cambia_niente(self, monkeypatch):
        prepara(monkeypatch)
        assert cwapu.scegli_uscita_audio(elenco=ELENCO, chiedi=lambda **k: 0, automatica=18) is None

    def test_la_scelta_di_adesso_e_il_predefinito_della_domanda(self, monkeypatch, capsys):
        prepara(monkeypatch, "MME", "Altoparlanti (Realtek)", 4)
        domande = []

        def chiedi(**k):
            domande.append(k)
            return k["default"]

        assert cwapu.scegli_uscita_audio(elenco=ELENCO, chiedi=chiedi, automatica=18) is None
        assert domande[0]["default"] == 2
        assert domande[0]["imin"] == 0 and domande[0]["imax"] == 4
        assert "Invio per 2" in domande[0]["prompt"]
        assert "scelta adesso" in capsys.readouterr().out

    def test_senza_uscite_lo_dice(self, monkeypatch, capsys):
        prepara(monkeypatch)
        assert cwapu.scegli_uscita_audio(elenco=[], chiedi=lambda **k: 0, automatica=18) is None
        assert "Nessuna uscita" in capsys.readouterr().out


class TestSuona:
    def test_passa_l_indice_scelto_come_api(self, monkeypatch):
        chiamate = []

        def motore(**parametri):
            chiamate.append(parametri)
            return object(), 20.0

        prepara_suona(monkeypatch, motore)
        prepara(monkeypatch, "WASAPI", "Altoparlanti (Realtek)", 18)
        cwapu.suona("paris")
        assert chiamate[0]["api"] == 18
        prepara(monkeypatch)
        cwapu.suona("paris")
        assert chiamate[1]["api"] is None

    def test_un_mixer_che_non_apre_l_uscita_viene_detto(self, monkeypatch, capsys):
        class HandleRotto:
            errore = "apertura del dispositivo audio non riuscita: Invalid sample rate"
            file_salvato = None

        prepara_suona(monkeypatch, lambda **p: (HandleRotto(), 20.0))
        prepara(monkeypatch)
        handle, rwpm = cwapu.suona("paris")
        assert handle is None and rwpm == 0.0
        assert "Invalid sample rate" in capsys.readouterr().out

    def test_un_wav_non_scritto_non_e_un_messaggio_non_trasmesso(self, monkeypatch, capsys):
        """CWzator mette nello stesso attributo anche il salvataggio fallito, quando il CW e' gia' uscito: lo dice gia' chi ha chiesto il file."""

        class HandleSuonato:
            errore = "salvataggio del file non riuscito: permesso negato"
            file_salvato = None

        prepara_suona(monkeypatch, lambda **p: (HandleSuonato(), 20.0))
        prepara(monkeypatch)
        handle, rwpm = cwapu.suona("paris", to_file=True)
        assert handle is not None and rwpm == 20.0
        assert "non ha trasmesso" not in capsys.readouterr().out


class TestImpostazioni:
    def test_i_predefiniti_sono_la_scelta_automatica(self):
        assert cwapu.DEFAULT_DATA["overall_settings"]["uscita_interfaccia"] == ""
        assert cwapu.DEFAULT_DATA["overall_settings"]["uscita_dispositivo"] == ""

    def test_un_file_vecchio_riceve_la_scelta_automatica(self, tmp_path, monkeypatch):
        percorso = tmp_path / "cwapu_settings.json"
        percorso.write_text('{"overall_settings": {"speed": 42}}', encoding="utf-8")
        monkeypatch.setattr(cwapu, "SETTINGS_FILE", str(percorso))
        dati = cwapu.load_settings()
        assert dati["overall_settings"]["uscita_interfaccia"] == ""
