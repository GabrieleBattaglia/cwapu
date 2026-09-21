# Prove automatiche di CWapu, il ciclo del contest.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' auto).
# Nate con la tappa 3 del piano della issue 7. Il contest e' l'unica parte di
# CWapu che suona, legge la tastiera e conta il tempo tutto insieme: qui si
# fa girare con un orologio finto, una tastiera finta e un motore CW finto,
# cosi' il ciclo si collauda senza toccare ne' la scheda audio ne' il disco.

import contextlib
import copy
import io
import itertools
import os
import sys

import numpy as np
import pytest

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)

import contest as ct  # noqa: E402
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
    "overall_api": None,
    "overall_contest_call": "IZ4APU",
}


class Orologio:
    """Il tempo del contest, che avanza di un passo a ogni sguardo alla tastiera."""

    def __init__(self, passo=0.05):
        self.adesso = 0.0
        self.passo = passo

    def monotonic(self):
        return self.adesso

    def time(self):
        return self.adesso

    def avanza(self):
        self.adesso += self.passo


class Suono:
    """Il finto PlaybackHandle: suona per una durata e poi risulta finito."""

    def __init__(self, orologio, durata, registro=None, fs=44100):
        self.orologio = orologio
        self.fine = orologio.adesso + durata
        self.is_playing = self
        self.errore = None
        self.sample_rate = fs
        self.audio_data = np.zeros(int(durata * fs))
        self._registro = registro

    def is_set(self):
        return self.orologio.adesso < self.fine

    def stop(self):
        if self._registro is not None and self.orologio.adesso < self.fine:
            self._registro.append(self.orologio.adesso)
        self.fine = self.orologio.adesso


class Fondo:
    """La finta maniglia di un ciclo acceso, con il conto degli stop."""

    def __init__(self, score, chiavi, buffer=None):
        self.score = score
        self.chiavi = chiavi
        self.buffer = buffer
        self.fermato = False

    def stop(self):
        self.fermato = True
        return True


class Acustica:
    """Al posto di Acusticator: registra cio' che gli si chiede invece di suonarlo.

    sintetizza restituisce due canali di rumore finto, diversi a ogni
    chiamata, cosi' il fronte stereo si puo' misurare davvero.
    """

    def __init__(self):
        self.cicli = []
        self.score = []
        self.seme = 0

    def sintetizza(self, score, kind=1, adsr=None, fs=44100, pan=None):
        self.score.append(score)
        self.seme += 1
        generatore = np.random.default_rng(self.seme)
        mono = generatore.standard_normal(2048).astype(np.float32)
        return np.stack([mono, mono], axis=1)

    def ciclo_di(self, buffer, fs=None, pan=0.0, dissolvenza=0.05):
        acceso = Fondo(self.score[-1] if self.score else None, {"fs": fs, "pan": pan}, buffer)
        self.cicli.append(acceso)
        return acceso


class MotoreFinto:
    """Al posto di suona: registra cio' che gli si chiede e restituisce un suono."""

    def __init__(self, orologio):
        self.orologio = orologio
        self.testi = []
        self.chiamate = []
        self.zittite = []

    def __call__(self, msg, wpm=None, pitch=None, l=None, s=None, p=None, sync=False, to_file=False, avvisa=True, farnsworth=None, pan=0, vol=None, qsb=None):
        self.testi.append(msg)
        self.chiamate.append({"msg": msg, "wpm": wpm, "pitch": pitch, "pan": pan, "vol": vol, "qsb": qsb})
        if sync:
            return None, 0.0
        # Un carattere ogni sessanta millesimi e' l'ordine di grandezza del CW
        # a venti parole al minuto: basta perche' le scadenze del motore abbiano
        # un senso l'una rispetto all'altra.
        registro = self.zittite if vol is not None else None
        return Suono(self.orologio, max(0.2, len(msg) * 0.06), registro), float(wpm or 20)


class Tastiera:
    """I tasti del copione arrivano quando l'orologio finto passa il loro istante.

    Una voce del copione puo' essere una funzione senza argomenti: quello che
    restituisce viene battuto un carattere alla volta, e serve per scrivere
    cio' che si sa soltanto mentre il contest gira, come il progressivo della
    stazione.
    """

    def __init__(self, orologio, copione):
        self.orologio = orologio
        self.copione = list(copione)
        self.battuti = []

    def __call__(self, prompt="", attesa=None, alla_scadenza=""):
        if attesa is None:
            return "\r"
        self.orologio.avanza()
        if not self.copione or self.orologio.adesso < self.copione[0][0]:
            return alla_scadenza
        istante, tasto = self.copione.pop(0)
        if callable(tasto):
            tasti = tasto() or ""
            if not tasti:
                return alla_scadenza
            for carattere in reversed(tasti[1:]):
                self.copione.insert(0, (istante, carattere))
            tasto = tasti[0]
        self.battuti.append(tasto)
        return tasto


def prepara(monkeypatch, copione, minuti=1, nominativo="DL3XY", contest=None):
    """Mette al posto del mondo esterno le controfigure, e restituisce il banco.

    contest: gli stati del pannello del contest da mettere fra le impostazioni
    salvate, che il pannello poi conferma da solo, perche' la tastiera finta
    risponde Invio a chi la chiama senza attesa.
    """
    for nome, valore in IMPOSTAZIONI.items():
        monkeypatch.setattr(cwapu, nome, valore, raising=False)
    orologio = Orologio()
    cw = MotoreFinto(orologio)
    tastiera = Tastiera(orologio, copione)
    diario = io.StringIO()
    contest_creati = []

    class Spia(ct.Contest):
        """Il motore vero, con un seme fisso e una maniglia per la prova."""

        def __init__(self, *argomenti, **chiavi):
            chiavi.setdefault("seme", 7)
            super().__init__(*argomenti, **chiavi)
            contest_creati.append(self)

    @contextlib.contextmanager
    def finto_diario():
        yield diario

    monkeypatch.setattr(cwapu, "time", orologio)
    monkeypatch.setattr(cwapu, "suona", cw)
    monkeypatch.setattr(cwapu, "key", tastiera)
    monkeypatch.setattr(cwapu, "menu", lambda **chiavi: "2")
    monkeypatch.setattr(cwapu, "dgt", lambda **chiavi: chiavi.get("default") if chiavi.get("kind") == "s" else minuti)
    nominativi = itertools.cycle([nominativo] if isinstance(nominativo, str) else nominativo)
    monkeypatch.setattr(cwapu, "Mkdqrz", lambda scelta: next(nominativi))
    monkeypatch.setattr(cwapu, "apri_diario", finto_diario)
    acustica = Acustica()
    monkeypatch.setattr(cwapu, "Acusticator", acustica)
    monkeypatch.setattr(cwapu.ct, "Contest", Spia)
    dati = copy.deepcopy(cwapu.DEFAULT_DATA)
    dati["contest_settings"].update(contest or {})
    monkeypatch.setattr(cwapu, "app_data", dati, raising=False)
    return {"orologio": orologio, "cw": cw, "tastiera": tastiera, "diario": diario, "contest": contest_creati, "acustica": acustica, "zittite": cw.zittite}


def scrivi(istante, testo):
    """Il testo battuto un carattere alla volta a partire da questo istante."""
    return [(istante, carattere) for carattere in testo]


class TestNumeriTagliati:
    def test_le_abbreviazioni_tornano_cifre(self):
        assert cwapu.numero_dal_taglio("5NNTT1") == "599001"
        assert cwapu.numero_dal_taglio("5nn tt1") == "599 001"

    def test_cio_che_non_e_abbreviazione_passa_com_e(self):
        assert cwapu.numero_dal_taglio("599 27") == "599 27"


class TestScambio:
    def test_il_solo_numero_vale_599(self):
        assert cwapu.leggi_scambio("27") == (599, 27)

    def test_rapporto_e_numero_separati_da_uno_spazio(self):
        """Decisione D8: sono le due forme ammesse nel campo dello scambio."""
        assert cwapu.leggi_scambio("579 27") == (579, 27)

    def test_le_abbreviazioni_si_scrivono_come_si_sentono(self):
        assert cwapu.leggi_scambio("5NN TT1") == (599, 1)
        assert cwapu.leggi_scambio("TT1") == (599, 1)

    def test_il_campo_vuoto_o_illeggibile_non_e_uno_scambio(self):
        assert cwapu.leggi_scambio("") is None
        assert cwapu.leggi_scambio("   ") is None
        assert cwapu.leggi_scambio("DL3XY") is None


class TestNominativoProprio:
    def test_si_ripropone_quello_salvato(self, monkeypatch):
        monkeypatch.setattr(cwapu, "overall_contest_call", "IZ4APU", raising=False)
        monkeypatch.setattr(cwapu, "dgt", lambda **chiavi: chiavi.get("default"))
        assert cwapu.chiedi_nominativo_contest() == "IZ4APU"

    def test_si_scrive_in_maiuscolo(self, monkeypatch):
        monkeypatch.setattr(cwapu, "overall_contest_call", "", raising=False)
        monkeypatch.setattr(cwapu, "dgt", lambda **chiavi: " iz4apu ")
        assert cwapu.chiedi_nominativo_contest() == "IZ4APU"
        assert cwapu.overall_contest_call == "IZ4APU"

    def test_senza_risposta_resta_vuoto(self, monkeypatch):
        monkeypatch.setattr(cwapu, "overall_contest_call", "", raising=False)
        monkeypatch.setattr(cwapu, "dgt", lambda **chiavi: "")
        assert cwapu.chiedi_nominativo_contest() == ""


class TestCicloContest:
    def test_alt_x_chiude_subito_e_non_salva_niente(self, monkeypatch, capsys):
        banco = prepara(monkeypatch, [(1.0, "alt-x")])
        cwapu.RxingContest({})
        uscita = capsys.readouterr().out
        assert "CQ TEST IZ4APU" in banco["cw"].testi
        assert cwapu.app_data["rxing_stats_qrz"]["sessions"] == 0
        assert banco["diario"].getvalue() == ""
        assert "prima del primo QSO" in uscita

    def test_un_qso_intero_dal_cq_al_log(self, monkeypatch, capsys):
        def numero_della_stazione():
            attive = banco["contest"][0].dx_attive() if banco["contest"] else []
            return str(attive[0].nr) if attive else ""

        copione = [
            *scrivi(3.0, "DL3XY"),
            (3.5, "\r"),
            (7.0, numero_della_stazione),
            (7.5, "\r"),
            (9.0, "alt-x"),
        ]
        banco = prepara(monkeypatch, copione)
        cwapu.RxingContest({})
        uscita = capsys.readouterr().out
        testi = banco["cw"].testi
        assert "CQ TEST IZ4APU" in testi
        assert any(t.startswith("DL3XY 5NN") for t in testi), testi
        assert "TU" in testi
        # La riga breve del log: numero, nominativo, scambio e verifica.
        assert "#1 DL3XY 599" in uscita and uscita.count(" ok") >= 1
        assert cwapu.app_data["rxing_stats_qrz"]["sessions"] == 1
        assert cwapu.app_data["rxing_stats_qrz"]["total_calls"] == 1
        assert cwapu.app_data["rxing_stats_qrz"]["total_correct"] == 1
        assert "CONTEST" in banco["diario"].getvalue()
        sessione = cwapu.app_data["historical_rx_data_qrz"]["sessions_log"][-1]
        assert sessione["items_sent_session"] == 1
        assert sessione["items_correct_session"] == 1
        assert sessione["rwpm_avg"] > 0

    def test_il_nominativo_sbagliato_diventa_un_nil(self, monkeypatch, capsys):
        copione = [
            *scrivi(3.0, "DL3XZ"),
            (3.5, "\r"),
            *scrivi(7.0, "1"),
            (7.5, "\r"),
            (9.0, "alt-x"),
        ]
        banco = prepara(monkeypatch, copione)
        cwapu.RxingContest({})
        uscita = capsys.readouterr().out
        assert "NIL" in uscita
        assert cwapu.app_data["rxing_stats_qrz"]["total_correct"] == 0
        assert cwapu.app_data["rxing_stats_qrz"]["total_wrong_items"] == 1
        assert banco["cw"].testi

    def test_i_tasti_dei_valori_cambiano_velocita_tono_e_banda(self, monkeypatch, capsys):
        # Fra l'ultima pressione e Alt+X ci vuole piu' dell'attesa, altrimenti
        # gli annunci restano in sospeso e non escono affatto.
        copione = [(1.0, "f10"), (1.5, "f9"), (2.0, "f9"), (2.5, "alt-up"), (3.0, "shift-up"), (8.0, "alt-x")]
        banco = prepara(monkeypatch, copione)
        cwapu.RxingContest({})
        uscita = capsys.readouterr().out
        assert cwapu.overall_speed == 18
        assert cwapu.overall_pitch == 600
        assert banco["contest"][0].banda == cwapu.CONTEST_BANDA_DEFAULT + cwapu.CONTEST_PASSO_BANDA
        assert banco["contest"][0].mio_wpm == 18
        assert "WPM 18" in uscita and "Tono 600" in uscita and "Banda 550" in uscita

    def test_i_valori_si_annunciano_quando_la_mano_si_ferma(self, monkeypatch, capsys):
        """Annunciare a ogni pressione riempie la voce di numeri che scorrono."""
        copione = [(1.0, "shift-down"), (1.2, "shift-down"), (1.4, "shift-down"), (8.0, "alt-x")]
        prepara(monkeypatch, copione)
        cwapu.RxingContest({})
        uscita = capsys.readouterr().out
        # Tre pressioni, un annuncio solo, e porta l'ultimo valore.
        assert uscita.count("Banda ") == 1
        assert "Banda 350" in uscita

    def test_un_valore_cambiato_e_poi_chiuso_subito_non_resta_muto(self, monkeypatch, capsys):
        """Chi cambia e chiude prima dell'attesa non deve perdere l'annuncio."""
        copione = [(1.0, "shift-down"), (1.5, "alt-x")]
        prepara(monkeypatch, copione)
        cwapu.RxingContest({})
        assert "Banda 450" in capsys.readouterr().out

    def test_esc_ferma_la_trasmissione_e_pulisce_il_campo(self, monkeypatch):
        copione = [
            (0.5, "\x1b"),
            *scrivi(3.0, "DL3"),
            (3.5, "\x1b"),
            (4.0, "alt-x"),
        ]
        banco = prepara(monkeypatch, copione)
        cwapu.RxingContest({})
        # Il primo Esc arriva mentre il CQ suona ancora e lo zittisce; il
        # secondo trova il campo scritto e lo pulisce.
        assert banco["cw"].testi[0] == "CQ TEST IZ4APU"
        assert cwapu.app_data["rxing_stats_qrz"]["sessions"] == 0

    def test_il_campo_e_uno_e_passa_dal_call_al_numero(self, monkeypatch, capsys):
        """Il piano vuole un campo solo: l'Invio lo fa passare da CALL a NR."""
        copione = [
            *scrivi(3.0, "DL3XY"),
            (3.6, "\r"),
            *scrivi(4.0, "27"),
            (4.5, "alt-x"),
        ]
        prepara(monkeypatch, copione)
        cwapu.RxingContest({})
        uscita = capsys.readouterr().out
        assert "+0 -0 =0 CALL: DL3XY" in uscita
        assert "+0 -0 =0 DL3XY 5NN NR: 27" in uscita

    def test_lo_spazio_scrive_solo_nel_numero(self, monkeypatch, capsys):
        """Nel nominativo lo spazio non serve e non si scrive; nel numero separa il rapporto."""
        copione = [
            *scrivi(3.0, "DL"),
            (3.3, " "),
            *scrivi(3.4, "3XY"),
            (3.8, "\r"),
            *scrivi(4.2, "579"),
            (4.6, " "),
            *scrivi(4.7, "27"),
            (5.2, "alt-x"),
        ]
        prepara(monkeypatch, copione)
        cwapu.RxingContest({})
        uscita = capsys.readouterr().out
        assert "+0 -0 =0 CALL: DL3XY" in uscita
        assert "+0 -0 =0 DL3XY 5NN NR: 579 27" in uscita

    def test_il_pile_up_manda_le_stazioni_sul_fronte_stereo(self, monkeypatch):
        """Con il pile-up acceso rispondono in piu' di una, ognuna dal suo posto."""
        banco = prepara(
            monkeypatch,
            [(8.0, "alt-x")],
            nominativo=["DL3XY", "IK2ABC", "W9CF", "F5IN", "JA1ZZZ", "VE3NEA"],
            contest={"pileup": True, "attivita": 8, "stereo": 100},
        )
        cwapu.RxingContest({})
        assert banco["contest"][0].pileup is True
        stazioni = [c for c in banco["cw"].chiamate if c["vol"] is not None]
        assert len(stazioni) >= 2
        assert any(abs(c["pan"]) > 1 for c in stazioni)
        assert all(0.0 <= c["vol"] <= 1.0 for c in stazioni)
        assert all(-100.0 <= c["pan"] <= 100.0 for c in stazioni)

    def test_in_modo_singolo_la_stazione_sta_al_centro_del_pannello(self, monkeypatch):
        banco = prepara(monkeypatch, [(4.0, "alt-x")], contest={"pileup": False, "stereo": 0})
        cwapu.RxingContest({})
        assert banco["contest"][0].pileup is False
        assert all(c["pan"] == 0 for c in banco["cw"].chiamate)

    def test_il_pannello_passa_i_suoi_valori_al_motore(self, monkeypatch):
        banco = prepara(
            monkeypatch,
            [(1.0, "alt-x")],
            contest={"banda": 300, "sbadati": False, "qrm": True, "qrm_massime": 3, "tasto_verticale": False},
        )
        cwapu.RxingContest({})
        motore = banco["contest"][0]
        assert motore.banda == 300
        assert motore.sbadati is False
        assert motore.qrm is True and motore.qrm_massime == 3
        assert motore.pesi_manuali[0] == 0

    def test_con_il_qrn_il_fondo_si_accende_e_si_spegne(self, monkeypatch):
        banco = prepara(monkeypatch, [(2.0, "alt-x")], contest={"qrn": True, "banda": 400})
        cwapu.RxingContest({})
        cicli = banco["acustica"].cicli
        assert len(cicli) == 1
        # Il rumore e' limitato alla banda del filtro attorno al mio tono.
        assert cicli[0].score[0] == "350-750"
        assert cicli[0].fermato is True

    def test_il_fondo_si_allarga_quanto_dice_lo_stereo(self, monkeypatch):
        """Il rumore di fondo di una radio non viene da un punto solo."""
        banco = prepara(monkeypatch, [(2.0, "alt-x")], contest={"qrn": True, "stereo": 100})
        cwapu.RxingContest({})
        largo = banco["acustica"].cicli[0].buffer
        assert abs(float(np.corrcoef(largo[:, 0], largo[:, 1])[0, 1])) < 0.2
        banco = prepara(monkeypatch, [(2.0, "alt-x")], contest={"qrn": True, "stereo": 0})
        cwapu.RxingContest({})
        stretto = banco["acustica"].cicli[0].buffer
        assert np.allclose(stretto[:, 0], stretto[:, 1])

    def test_senza_qrn_non_si_accende_niente(self, monkeypatch):
        banco = prepara(monkeypatch, [(2.0, "alt-x")], contest={"qrn": False})
        cwapu.RxingContest({})
        assert banco["acustica"].cicli == []

    def test_stringendo_la_banda_il_fondo_si_rifa(self, monkeypatch):
        banco = prepara(monkeypatch, [(1.0, "shift-down"), (2.0, "alt-x")], contest={"qrn": True, "banda": 400})
        cwapu.RxingContest({})
        cicli = banco["acustica"].cicli
        assert len(cicli) == 2
        assert cicli[0].score[0] == "350-750" and cicli[1].score[0] == "375-725"
        assert all(c.fermato for c in cicli)

    def test_con_il_qsb_le_stazioni_evanescono(self, monkeypatch):
        banco = prepara(monkeypatch, [(6.0, "alt-x")], contest={"qsb": True})
        cwapu.RxingContest({})
        stazioni = [c for c in banco["cw"].chiamate if c["vol"] is not None]
        assert stazioni
        assert all(c["qsb"] is not None for c in stazioni)
        mie = [c for c in banco["cw"].chiamate if c["vol"] is None]
        assert all(c["qsb"] is None for c in mie)

    def test_il_tono_del_contest_ha_i_limiti_del_comando_h(self, monkeypatch, capsys):
        """Il tono e' quello generale e resta dopo il contest: un tetto piu'
        basso qui lo abbasserebbe in silenzio a chi lo tiene alto."""
        copione = [(1.0, "alt-up"), (1.5, "alt-x")]
        prepara(monkeypatch, copione)
        monkeypatch.setattr(cwapu, "overall_pitch", cwapu.PITCH_MAX, raising=False)
        cwapu.RxingContest({})
        assert cwapu.overall_pitch == cwapu.PITCH_MAX
        copione = [(1.0, "alt-down"), (1.5, "alt-x")]
        prepara(monkeypatch, copione)
        monkeypatch.setattr(cwapu, "overall_pitch", cwapu.PITCH_MIN, raising=False)
        cwapu.RxingContest({})
        assert cwapu.overall_pitch == cwapu.PITCH_MIN

    def test_la_riga_dice_come_sto_andando(self, monkeypatch, capsys):
        """In testa alla riga non c'e' il numero del QSO ma il bilancio."""
        def numero_della_stazione():
            attive = banco["contest"][0].dx_attive() if banco["contest"] else []
            return str(attive[0].nr) if attive else ""

        copione = [*scrivi(3.0, "DL3XY"), (3.6, "\r"), (7.0, numero_della_stazione), (7.5, "\r"), (11.0, "A"), (12.0, "alt-x")]
        banco = prepara(monkeypatch, copione)
        cwapu.RxingContest({})
        uscita = capsys.readouterr().out
        # Prima del QSO il bilancio e' a zero, dopo porta il punto e il prefisso.
        assert "+0 -0 =0 CALL: DL3XY" in uscita
        assert "+1 -0 =1 CALL: A" in uscita

    def test_il_bilancio_conta_anche_gli_sbagliati(self, monkeypatch, capsys):
        copione = [*scrivi(3.0, "DL3XZ"), (3.6, "\r"), *scrivi(7.0, "1"), (7.5, "\r"), (11.0, "A"), (12.0, "alt-x")]
        prepara(monkeypatch, copione)
        cwapu.RxingContest({})
        assert "+0 -1 =0 CALL: A" in capsys.readouterr().out

    def test_mentre_trasmetto_il_ricevitore_tace(self, monkeypatch):
        """In radio non ci si sente addosso ne' il fruscio ne' chi e' gia' in aria."""
        # Il CQ si rilancia mentre le stazioni stanno ancora rispondendo, che
        # e' il momento in cui il difetto si sentiva.
        copione = [(istante, "f1") for istante in (1.1, 1.3, 1.5, 1.7, 2.0, 2.3)] + [(6.0, "alt-x")]
        banco = prepara(monkeypatch, copione, contest={"qrn": True, "pileup": True, "attivita": 9})
        cwapu.RxingContest({})
        cicli = banco["acustica"].cicli
        # Il fruscio si spegne a ogni mia trasmissione e torna quando ho finito.
        assert cicli and all(c.fermato for c in cicli)
        # E nessuna stazione resta a suonare mentre trasmetto.
        assert banco["zittite"], "nessuna stazione e' stata zittita"

    def test_zittire_una_stazione_non_sposta_i_tempi_del_contest(self, monkeypatch):
        """Il motore la considera finita quando il suo messaggio sarebbe finito."""
        banco = prepara(monkeypatch, [(6.0, "f1"), (20.0, "alt-x")], contest={"pileup": True, "attivita": 8})
        cwapu.RxingContest({})
        # Se le zittite non venissero mai dichiarate finite, il motore
        # resterebbe fermo ad aspettarle e non nascerebbe piu' niente.
        assert len(banco["cw"].testi) > 4, banco["cw"].testi

    def test_alt_s_dice_come_va(self, monkeypatch, capsys):
        copione = [(2.0, "alt-s"), (2.5, "alt-x")]
        prepara(monkeypatch, copione)
        cwapu.RxingContest({})
        uscita = capsys.readouterr().out
        assert "QSO 0 PT 0 PFX 0 = 0" in uscita
        assert "00:0" in uscita

    def test_senza_uno_scambio_leggibile_si_manda_il_punto_interrogativo(self, monkeypatch):
        copione = [
            *scrivi(3.0, "DL3XY"),
            (3.6, "\r"),
            (5.0, "\r"),
            (5.5, "alt-x"),
        ]
        banco = prepara(monkeypatch, copione)
        cwapu.RxingContest({})
        assert "?" in banco["cw"].testi


class TestRapporto:
    def test_il_pannello_si_legge_in_una_riga(self):
        stati = dict(cwapu.CONTEST_PREDEFINITI)
        riga = cwapu.descrivi_pannello_contest(stati)
        assert "una stazione alla volta" in riga
        assert "banda 500 hertz" in riga
        assert "manipolazione manuale al 30 per cento" in riga
        assert "QRM" not in riga

    def test_il_pannello_dice_cio_che_e_acceso(self):
        stati = dict(cwapu.CONTEST_PREDEFINITI, pileup=True, attivita=6, qrm=True, qrm_massime=3, tasto_verticale=False)
        riga = cwapu.descrivi_pannello_contest(stati)
        assert "pile-up con attività 6" in riga
        assert "QRM fino a 3" in riga
        assert "tutti in manipolazione automatica" in riga

    def test_il_rapporto_porta_punteggio_errori_e_ritmo(self):
        punteggio = ct.Punteggio()
        punteggio.registra(10.0, "DL3XY", 599, 1, 1, ("DL3XY", 599, 1))
        punteggio.registra(20.0, "IK2ABC", 599, 2, 2, ("IK2ABD", 599, 2))
        punteggio.registra(30.0, "W9CF", 599, 3, 3, ("W9CF", 599, 4))
        punteggio.rinuncia("F5IN")
        righe = cwapu.righe_rapporto_contest(punteggio, dict(cwapu.CONTEST_PREDEFINITI), 600)
        intero = " ".join(righe)
        assert "Punti 3, prefissi 3, punteggio 9." in intero
        assert "Verificati: punti 1, prefissi 1, punteggio 1." in intero
        assert "QSO sbagliati: 66.7%." in intero
        assert "Ritmo:" in intero and "all'ora" in intero
        assert "Nominativi copiati male: IK2ABC." in intero
        assert "Scambi copiati male: W9CF 599 3." in intero
        assert "Se ne sono andate: F5IN." in intero
        assert "Sessione fatta con:" in intero

    def test_senza_errori_il_rapporto_non_elenca_niente(self):
        punteggio = ct.Punteggio()
        punteggio.registra(10.0, "DL3XY", 599, 1, 1, ("DL3XY", 599, 1))
        intero = " ".join(cwapu.righe_rapporto_contest(punteggio, dict(cwapu.CONTEST_PREDEFINITI), 300))
        assert "copiati male" not in intero
        assert "Se ne sono andate" not in intero

    def test_il_rapporto_esce_a_video_e_nel_diario(self, monkeypatch, capsys):
        def numero_della_stazione():
            attive = banco["contest"][0].dx_attive() if banco["contest"] else []
            return str(attive[0].nr) if attive else ""

        copione = [
            *scrivi(3.0, "DL3XY"),
            (3.6, "\r"),
            (7.0, numero_della_stazione),
            (7.5, "\r"),
            (9.0, "alt-x"),
        ]
        banco = prepara(monkeypatch, copione)
        cwapu.RxingContest({})
        uscita = capsys.readouterr().out
        diario = banco["diario"].getvalue()
        for pezzo in ("Punti 1", "Verificati: punti 1", "QSO sbagliati: 0.0%", "Sessione fatta con:"):
            assert pezzo in uscita, pezzo
            assert pezzo in diario, pezzo
        sessione = cwapu.app_data["historical_rx_data_qrz"]["sessions_log"][-1]
        assert sessione["punteggio_verificato"] == 1
        assert sessione["prefissi_verificati"] == 1
        assert sessione["contest_settings"]["banda"] == 500


@pytest.mark.parametrize("tasto", ["f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8"])
def test_ogni_tasto_funzione_manda_qualcosa(monkeypatch, tasto):
    """I tasti di cwsim mandano tutti un messaggio, anche a campo vuoto."""
    copione = [*scrivi(2.0, "DL3XY"), (3.0, tasto), (3.5, "alt-x")]
    banco = prepara(monkeypatch, copione)
    cwapu.RxingContest({})
    assert len(banco["cw"].testi) >= 2
