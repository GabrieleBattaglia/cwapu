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

import cwapu  # noqa: E402
from modules import contest as ct  # noqa: E402

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
        # I miei messaggi tagliati a meta': con la coda non deve
        # succedere piu', e senza registrarli non si vedrebbe.
        self.miei_tagliati = []

    def __call__(self, msg, wpm=None, pitch=None, l=None, s=None, p=None, sync=False, to_file=False, avvisa=True, farnsworth=None, pan=0, vol=None, qsb=None, chirp=None, vibrato=None, ritardo=None, qsb_profondita=None):
        self.testi.append(msg)
        self.chiamate.append(
            {
                "msg": msg,
                "wpm": wpm,
                "pitch": pitch,
                "pan": pan,
                "vol": vol,
                "qsb": qsb,
                "qsb_profondita": qsb_profondita,
                "chirp": chirp,
                "vibrato": vibrato,
                "ritardo": ritardo,
                "quando": self.orologio.adesso,
                "l": l,
                "s": s,
                "p": p,
            }
        )
        if sync:
            return None, 0.0
        # Un carattere ogni sessanta millesimi e' l'ordine di grandezza del CW
        # a venti parole al minuto: basta perche' le scadenze del motore abbiano
        # un senso l'una rispetto all'altra.
        registro = self.zittite if vol is not None else self.miei_tagliati
        # Come il motore vero: la durata di un pezzo ritardato comprende il
        # silenzio che gli sta davanti.
        return Suono(self.orologio, (ritardo or 0.0) + max(0.2, len(msg) * 0.06), registro), float(wpm or 20)


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


def prepara(monkeypatch, copione, minuti=1, nominativo="DL3XY", contest=None, quanti_qso=None):
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
    # Con quanti_qso la durata si conta in QSO invece che in minuti: e' il
    # ramo che nessuna prova aveva mai fatto girare, ed e' proprio quello
    # dove Gabriele ha trovato il contest che finiva dopo due QSO su otto.
    monkeypatch.setattr(cwapu, "menu", lambda **chiavi: "1" if quanti_qso is not None else "2")
    quanto = minuti if quanti_qso is None else quanti_qso
    monkeypatch.setattr(cwapu, "dgt", lambda **chiavi: chiavi.get("default") if chiavi.get("kind") == "s" else quanto)
    nominativi = itertools.cycle([nominativo] if isinstance(nominativo, str) else nominativo)
    monkeypatch.setattr(cwapu, "Mkdqrz", lambda scelta: next(nominativi))
    monkeypatch.setattr(cwapu, "apri_diario", finto_diario)
    # Il banco non tocca il disco. Dal 23 settembre il contest e l'esercizio
    # salvano le impostazioni appena finiscono, invece di aspettare l'uscita
    # dal menu: senza questa sostituzione le prove scriverebbero i loro dati
    # finti sopra l'archivio vero di Gabriele, che e' grande tre megabyte e
    # contiene anni di esercizi. E' successo una volta.
    salvataggi = []
    annunci = []

    def salva(dati, annuncia=True):
        salvataggi.append(dati)
        annunci.append(annuncia)

    monkeypatch.setattr(cwapu, "save_settings", salva)
    acustica = Acustica()
    monkeypatch.setattr(cwapu, "Acusticator", acustica)
    monkeypatch.setattr(cwapu.ct, "Contest", Spia)
    dati = copy.deepcopy(cwapu.DEFAULT_DATA)
    dati["contest_settings"].update(contest or {})
    monkeypatch.setattr(cwapu, "app_data", dati, raising=False)
    return {
        "orologio": orologio,
        "cw": cw,
        "tastiera": tastiera,
        "diario": diario,
        "contest": contest_creati,
        "acustica": acustica,
        "zittite": cw.zittite,
        "salvataggi": salvataggi,
        "annunci": annunci,
    }


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
        assert cwapu.app_data["rxing_stats_contest"]["sessions"] == 0
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
        # Il QSO riuscito non si annuncia: lo dicono i contatori in testa.
        assert "#1 DL3XY 599" not in uscita
        assert " ok" not in uscita
        assert cwapu.app_data["rxing_stats_contest"]["sessions"] == 1
        assert cwapu.app_data["rxing_stats_contest"]["total_calls"] == 1
        assert cwapu.app_data["rxing_stats_contest"]["total_correct"] == 1
        assert "CONTEST" in banco["diario"].getvalue()
        sessione = cwapu.app_data["historical_rx_data_contest"]["sessions_log"][-1]
        assert sessione["items_sent_session"] == 1
        assert sessione["items_correct_session"] == 1
        assert sessione["rwpm_avg"] > 0
        # Issue 15: l'esercizio QRZ non ne sa niente.
        assert cwapu.app_data["rxing_stats_qrz"]["sessions"] == 0
        assert cwapu.app_data["historical_rx_data_qrz"]["sessions_log"] == []
        assert cwapu.app_data["historical_rx_data_qrz"]["chars_since_last_report"] == 0
        assert cwapu.app_data["historical_rx_data_contest"]["chars_since_last_report"] == sessione["chars_sent_session"]

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
        assert cwapu.app_data["rxing_stats_contest"]["total_correct"] == 0
        assert cwapu.app_data["rxing_stats_contest"]["total_wrong_items"] == 1
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

    def con_pesi_larghi(self, monkeypatch, copione, contest=None):
        """Il banco con linee a 60 e spazi a 75: il motore CW finto restituisce
        per i miei messaggi il 66 per cento della velocita' nominale, come
        farebbe CWzator con quei pesi, e per le stazioni la nominale."""
        banco = prepara(monkeypatch, copione, contest=contest)
        monkeypatch.setattr(cwapu, "overall_dashes", 60)
        monkeypatch.setattr(cwapu, "overall_spaces", 75)
        finto = cwapu.suona

        def suona_con_i_miei_pesi(msg, *argomenti, **chiavi):
            handle, rwpm = finto(msg, *argomenti, **chiavi)
            return handle, (rwpm * 0.66 if chiavi.get("vol") is None else rwpm)

        monkeypatch.setattr(cwapu, "suona", suona_con_i_miei_pesi)
        return banco

    def test_il_cq_d_apertura_misura_subito_la_velocita(self, monkeypatch):
        """Il contest comincia con il mio CQ: la stima su PARIS con cui nasce il
        motore vale solo fino a quel momento."""
        banco = self.con_pesi_larghi(monkeypatch, [(8.0, "alt-x")])
        cwapu.RxingContest({})
        assert banco["contest"][0].mio_rwpm == pytest.approx(0.66 * 20)

    def test_la_stima_su_paris_la_fa_cwzator(self):
        assert cwapu.velocita_effettiva(20, 30, 50, 50) == pytest.approx(20.0)
        assert cwapu.velocita_effettiva(25, 60, 75, 50) == pytest.approx(16.44, abs=0.05)

    def test_ogni_mia_trasmissione_rimisura_la_velocita(self, monkeypatch):
        """Scelta di Gabriele del 24 settembre 2026: le stazioni si regolano
        sul rwpm che CWzator restituisce per ogni mio messaggio."""
        banco = self.con_pesi_larghi(monkeypatch, [(1.0, "f1"), (8.0, "alt-x")])
        cwapu.RxingContest({})
        assert banco["contest"][0].mio_rwpm == pytest.approx(0.66 * 20)

    def test_f10_sposta_l_effettiva_in_proporzione(self, monkeypatch):
        banco = self.con_pesi_larghi(monkeypatch, [(1.0, "f1"), (4.0, "f10"), (10.0, "alt-x")])
        cwapu.RxingContest({})
        m = banco["contest"][0]
        assert m.mio_wpm == 22
        assert m.mio_rwpm == pytest.approx(0.66 * 22)

    def test_il_5nn_accelerato_non_falsa_la_mia_velocita(self, monkeypatch):
        """Il mio scambio comincia con il 5NN, che e' il pezzo accelerato: la
        velocita' da misurare e' quella del numero, alla mia velocita'."""
        contest = {"scambio_veloce": True, "scambio_probabilita": 100, "scambio_incremento": 20}
        banco = self.con_pesi_larghi(monkeypatch, [(1.0, "f2"), (8.0, "alt-x")], contest=contest)
        cwapu.RxingContest({})
        pezzi = [c for c in banco["cw"].chiamate if c["vol"] is None and c["wpm"] == 24]
        assert pezzi, "il mio 5NN non e' partito accelerato"
        assert banco["contest"][0].mio_rwpm == pytest.approx(0.66 * 20)

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
        assert cwapu.app_data["rxing_stats_contest"]["sessions"] == 0

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

    def test_lo_spazio_nel_nominativo_passa_al_numero_in_silenzio(self, monkeypatch, capsys):
        """Come nei logger da contest: la stazione ha gia' dato il suo scambio
        prima che io rispondessi, e io scrivo nominativo, spazio, numero."""
        copione = [
            *scrivi(3.0, "DL3XY"),
            (3.4, " "),
            *scrivi(4.2, "579"),
            (4.6, " "),
            *scrivi(4.7, "27"),
            (5.2, "alt-x"),
        ]
        banco = prepara(monkeypatch, copione)
        cwapu.RxingContest({})
        uscita = capsys.readouterr().out
        assert "+0 -0 =0 DL3XY 5NN NR: 579 27" in uscita
        # Passando al numero non si e' trasmesso niente: solo il CQ d'apertura
        # e il saluto d'uscita.
        miei = [c["msg"] for c in banco["cw"].chiamate if c["vol"] is None]
        assert not [m for m in miei if "DL3XY" in m], miei

    def test_nominativo_spazio_numero_e_un_invio_solo(self, monkeypatch):
        """Un Invio solo le manda nominativo, scambio e TU insieme."""
        copione = [*scrivi(3.0, "DL3XY"), (3.4, " "), *scrivi(4.0, "1"), (4.5, "\r"), (12.0, "alt-x")]
        banco = prepara(monkeypatch, copione, minuti=2)
        cwapu.RxingContest({})
        miei = [c["msg"] for c in banco["cw"].chiamate if c["vol"] is None]
        chiusa = [m for m in miei if m.startswith("DL3XY 5NN")]
        assert chiusa, miei
        assert any(chiusa[0].endswith(" " + c) for c in ct.CHIUSURE), chiusa

    def test_il_pile_up_manda_le_stazioni_sul_fronte_stereo(self, monkeypatch):
        """Con il pile-up acceso rispondono in piu' di una, ognuna dal suo posto."""
        banco = prepara(
            monkeypatch,
            [(8.0, "alt-x")],
            nominativo=["DL3XY", "IK2ABC", "W9CF", "F5IN", "JA1ZZZ", "VE3NEA"],
            contest={"pileup": True, "pileup_massime": 8, "stereo": 100},
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
        # e' il momento in cui il difetto si sentiva. Gli istanti sono distanti
        # fra loro perche' dal 23 settembre i tasti funzione si accodano: sei
        # CQ battuti a raffica sarebbero una trasmissione sola e lunga, e
        # nessuna stazione farebbe in tempo a rispondere.
        copione = [(istante, "f1") for istante in (1.1, 6.0, 11.0, 16.0)] + [(22.0, "alt-x")]
        banco = prepara(monkeypatch, copione, minuti=2, contest={"qrn": True, "pileup": True, "pileup_massime": 9})
        cwapu.RxingContest({})
        cicli = banco["acustica"].cicli
        # Il fruscio si spegne a ogni mia trasmissione e torna quando ho finito.
        assert cicli and all(c.fermato for c in cicli)
        # E nessuna stazione resta a suonare mentre trasmetto.
        assert banco["zittite"], "nessuna stazione e' stata zittita"

    def test_zittire_una_stazione_non_sposta_i_tempi_del_contest(self, monkeypatch):
        """Il motore la considera finita quando il suo messaggio sarebbe finito."""
        banco = prepara(monkeypatch, [(6.0, "f1"), (20.0, "alt-x")], contest={"pileup": True, "pileup_massime": 8})
        cwapu.RxingContest({})
        # Se le zittite non venissero mai dichiarate finite, il motore
        # resterebbe fermo ad aspettarle e non nascerebbe piu' niente.
        assert len(banco["cw"].testi) > 4, banco["cw"].testi

    def test_chi_molla_non_si_annuncia_ma_finisce_nel_rapporto(self, monkeypatch, capsys):
        """Decisione D2: a schermo solo cio' che non si sente. Che una stazione
        se ne sia andata si sente, perche' smette di chiamare."""
        prepara(monkeypatch, [(70.0, "alt-x")], minuti=2)
        cwapu.RxingContest({})
        uscita = capsys.readouterr().out
        assert "Se ne sono andate" in uscita, "il rapporto deve elencarle"
        assert "se n\'" not in uscita, "durante il contest non si annunciano"

    def test_il_volume_si_muove_con_alt_e_i_tasti_funzione(self, monkeypatch, capsys):
        """E' il quarto valore che si cambia durante il contest."""
        copione = [(1.0, "alt-f10"), (1.2, "alt-f10"), (8.0, "alt-x")]
        prepara(monkeypatch, copione)
        cwapu.RxingContest({})
        assert round(cwapu.overall_volume * 100) == 60
        assert "Volume 60" in capsys.readouterr().out

    def test_il_volume_non_esce_dai_suoi_limiti(self, monkeypatch):
        copione = [(istante / 10, "alt-f9") for istante in range(10, 22)] + [(8.0, "alt-x")]
        prepara(monkeypatch, copione)
        cwapu.RxingContest({})
        assert cwapu.overall_volume == 0.0

    def test_il_fruscio_segue_il_volume(self, monkeypatch):
        """Se non lo seguisse, abbassando il volume si alzerebbe rispetto alle stazioni."""
        banco = prepara(monkeypatch, [(1.0, "alt-f9"), (8.0, "alt-x")], contest={"qrn": True})
        cwapu.RxingContest({})
        score = banco["acustica"].score
        assert len(score) >= 4, score
        # Il volume dello score e' il quarto campo della quartina.
        assert score[-1][3] < score[0][3], (score[0], score[-1])

    def test_ogni_valore_cambiato_conferma_con_una_r(self, monkeypatch):
        """L'annuncio a voce aspetta che la mano si fermi; la r no."""
        copione = [(1.0, "f10"), (2.0, "alt-up"), (3.0, "shift-up"), (4.0, "alt-f10"), (8.0, "alt-x")]
        banco = prepara(monkeypatch, copione)
        cwapu.RxingContest({})
        assert banco["cw"].testi.count("r") == 4, banco["cw"].testi

    def test_il_backspace_a_riga_vuota_torna_al_nominativo(self, monkeypatch, capsys):
        """DL3BA chiama, io copio DL2BA e lo mando, lui corregge: cosi' rimedio."""
        copione = [
            *scrivi(3.0, "DL2BA"),
            (3.6, "\r"),
            (6.0, "\x08"),
            (6.2, "\x08"),
            (6.3, "\x08"),
            (6.4, "\x08"),
            *scrivi(6.6, "3BA"),
            (7.2, "\r"),
            (9.0, "alt-x"),
        ]
        banco = prepara(monkeypatch, copione, nominativo="DL3BA")
        cwapu.RxingContest({})
        uscita = capsys.readouterr().out
        # Il primo Invio manda il nominativo sbagliato, il secondo quello giusto.
        assert any(t.startswith("DL2BA 5NN") for t in banco["cw"].testi), banco["cw"].testi
        assert any(t.startswith("DL3BA 5NN") for t in banco["cw"].testi), banco["cw"].testi
        # Tornando indietro il nominativo sbagliato e' li' da correggere.
        assert "CALL: DL2BA" in uscita
        assert "CALL: DL3BA" in uscita

    def test_il_backspace_a_riga_vuota_sul_nominativo_non_fa_niente(self, monkeypatch, capsys):
        prepara(monkeypatch, [(3.0, "\x08"), (3.5, "A"), (4.0, "alt-x")])
        cwapu.RxingContest({})
        assert "CALL: A" in capsys.readouterr().out

    def test_il_qso_riuscito_non_si_annuncia_ma_quello_sbagliato_si(self, monkeypatch, capsys):
        """In radio nessuno ti conferma che hai copiato bene; se hai copiato
        male, invece, cosa fosse davvero non lo sapresti mai."""
        copione = [*scrivi(3.0, "DL3XZ"), (3.6, "\r"), *scrivi(7.0, "1"), (7.5, "\r"), (11.0, "alt-x")]
        prepara(monkeypatch, copione)
        cwapu.RxingContest({})
        uscita = capsys.readouterr().out
        assert "NIL" in uscita, "il QSO sbagliato deve dirlo"
        assert "DL3XZ" in uscita, "con il nominativo come l'avevo scritto"

    def test_i_difetti_di_nota_arrivano_al_motore(self, monkeypatch):
        """Il chirp e il vibrato vanno con il flutter, che e' l'interruttore
        dei difetti del segnale."""
        # Il CQ si rilancia spesso, con il tetto del pile-up al massimo, cosi'
        # nascono abbastanza stazioni da vedere due difetti che toccano a una
        # su sei e a una su dieci: dalla 7.1.0 chi e' gia' in aria occupa il
        # suo posto, e con il tetto a nove i CQ in piu' non facevano nascere
        # nessuno.
        copione = [(istante, "f1") for istante in (2.0, 5.0, 8.0, 11.0, 14.0, 17.0, 20.0)] + [(30.0, "alt-x")]
        banco = prepara(
            monkeypatch,
            copione,
            nominativo=["DL3XY", "IK2ABC", "W9CF", "F5IN", "JA1ZZZ", "VE3NEA", "OH2BH", "EA3XY"],
            contest={"pileup": True, "pileup_massime": ct.PILEUP_MASSIME, "qsb": True, "flutter": True},
        )
        cwapu.RxingContest({})
        stazioni = [c for c in banco["cw"].chiamate if c["vol"] is not None]
        assert len(stazioni) >= 15, len(stazioni)
        assert any(c["chirp"] is not None for c in stazioni), "nessun chirp"
        assert any(c["vibrato"] is not None for c in stazioni), "nessun vibrato"
        for c in stazioni:
            if c["chirp"] is not None:
                assert ct.CHIRP_SCARTO[0] <= abs(c["chirp"]) <= ct.CHIRP_SCARTO[1]
            if c["vibrato"] is not None:
                profondita, frequenza = c["vibrato"]
                assert ct.VIBRATO_PROFONDITA[0] <= profondita <= ct.VIBRATO_PROFONDITA[1]
                assert ct.VIBRATO_FREQUENZA[0] <= frequenza <= ct.VIBRATO_FREQUENZA[1]

    def test_senza_flutter_le_note_sono_pulite(self, monkeypatch):
        banco = prepara(monkeypatch, [(12.0, "alt-x")], contest={"pileup": True, "pileup_massime": 9, "qsb": True, "flutter": False})
        cwapu.RxingContest({})
        stazioni = [c for c in banco["cw"].chiamate if c["vol"] is not None]
        assert stazioni
        assert all(c["chirp"] is None and c["vibrato"] is None for c in stazioni)

    def test_il_mio_messaggio_non_ha_difetti_di_nota(self, monkeypatch):
        banco = prepara(monkeypatch, [(6.0, "f1"), (9.0, "alt-x")], contest={"qsb": True, "flutter": True})
        cwapu.RxingContest({})
        miei = [c for c in banco["cw"].chiamate if c["vol"] is None]
        assert miei
        assert all(c["chirp"] is None and c["vibrato"] is None and c["qsb"] is None for c in miei)

    def test_la_durata_a_numero_conta_i_qso_a_log_non_le_stazioni_perdute(self, monkeypatch):
        """Contava anche chi se ne andava senza essere lavorato: una sessione
        da due QSO finiva al primo che mollava, e Gabriele ne faceva due o tre
        su otto."""
        banco = prepara(monkeypatch, [(70.0, "alt-x")], quanti_qso=2, contest={"pileup": True, "pileup_massime": 9})
        cwapu.RxingContest({})
        contest = banco["contest"][0]
        assert contest.punteggio.rinunce, "nessuna stazione se n'e' andata"
        assert contest.punteggio.punti_grezzi == 0
        # Il contest e' arrivato fino ad Alt+X: le rinunce non hanno consumato
        # nemmeno uno dei due QSO chiesti.
        assert banco["orologio"].adesso >= 70.0

    def test_le_stazioni_perdute_restano_fuori_dalle_statistiche(self, monkeypatch, capsys):
        """Erano il denominatore di tutte le percentuali: otto QSO su venticinque
        voleva dire otto a log e diciassette andate via."""
        banco = prepara(monkeypatch, [(70.0, "alt-x")], minuti=2, contest={"pileup": True, "pileup_massime": 9})
        cwapu.RxingContest({})
        uscita = capsys.readouterr().out
        contest = banco["contest"][0]
        assert contest.punteggio.rinunce
        assert f"Se ne sono andate {len(contest.punteggio.rinunce)}:" in uscita
        assert "ti ho inviato 0 QRZ" in uscita, uscita[-800:]
        # Il rapporto si legge, ma su disco non va: sarebbe una media su niente.
        assert cwapu.app_data["rxing_stats_contest"]["sessions"] == 0
        assert not cwapu.app_data["historical_rx_data_contest"]["sessions_log"]
        assert not banco["diario"].getvalue()

    def test_due_tasti_funzione_si_accodano_invece_di_tagliarsi(self, monkeypatch):
        """F5 e poi F7 mandano il nominativo copiato e poi il punto
        interrogativo, che e' il modo di chiedere la ripetizione. Prima il
        primo messaggio non veniva tagliato: spariva del tutto, e le stazioni
        non sapevano di essere state chiamate."""
        copione = [*scrivi(3.0, "DL3XY"), (3.6, "f5"), (3.7, "f7"), (12.0, "alt-x")]
        banco = prepara(monkeypatch, copione, minuti=1)
        cwapu.RxingContest({})
        # Solo i miei messaggi: quelli delle stazioni finiscono nella stessa
        # lista, e una stazione che si chiama DL3XY manda il proprio
        # nominativo esattamente come lo mando io con F5.
        miei = [c for c in banco["cw"].chiamate if c["vol"] is None]
        testi_miei = [c["msg"] for c in miei]
        assert "DL3XY" in testi_miei, testi_miei
        dopo = miei[testi_miei.index("DL3XY") + 1]
        assert dopo["msg"] == "?", testi_miei
        # Parte dopo il silenzio di uno spazio di parola, non attaccato.
        assert dopo["ritardo"] > 0, dopo
        assert not banco["cw"].miei_tagliati, "il primo messaggio e' stato tagliato"

    def test_il_punto_interrogativo_si_attacca_e_il_resto_no(self, monkeypatch):
        """In radio DL3XY? si manda come una parola sola, per fare prima: il ?
        parte dopo il silenzio fra due lettere. Gli altri messaggi accodati
        partono dopo uno spazio di parola."""
        copione = [*scrivi(3.0, "DL3XY"), (3.6, "f5"), (3.7, "f7"), (9.0, "f5"), (9.1, "f4"), (16.0, "alt-x")]
        banco = prepara(monkeypatch, copione, minuti=1)
        cwapu.RxingContest({})
        miei = [c for c in banco["cw"].chiamate if c["vol"] is None]
        testi = [c["msg"] for c in miei]
        wpm = cwapu.overall_speed
        s = cwapu.overall_spaces

        def silenzio_prima(indice):
            # Il silenzio vero: quello gia' trascorso quando il ciclo si e'
            # accorto della fine del messaggio precedente, piu' il ritardo.
            prima, dopo = miei[indice - 1], miei[indice]
            fine_prima = prima["quando"] + (prima["ritardo"] or 0.0) + max(0.2, len(prima["msg"]) * 0.06)
            return dopo["quando"] + (dopo["ritardo"] or 0.0) - fine_prima

        punto = testi.index("?")
        assert testi[punto - 1] == "DL3XY", testi
        assert silenzio_prima(punto) == pytest.approx(cwapu.buco_fra_pezzi(wpm, s, False), abs=1e-6)
        mio = testi.index("IZ4APU")
        assert testi[mio - 1] == "DL3XY", testi
        assert silenzio_prima(mio) == pytest.approx(cwapu.buco_fra_pezzi(wpm, s, True), abs=1e-6)

    def test_la_mia_stazione_manipola_con_i_pesi_della_sezione_k(self, monkeypatch):
        """Nel contest solo il Farnsworth resta fuori: .l .s .p sono il mio modo
        di manipolare. La mia richiesta portava i pesi standard, e con i pesi
        di serie nel banco nessuna prova poteva accorgersene: l'ha sentito
        Gabriele provando l'eseguibile compilato."""
        copione = [*scrivi(3.0, "DL3XY"), (3.6, "\r"), (3.7, "f7"), (12.0, "alt-x")]
        banco = prepara(monkeypatch, copione, minuti=2)
        monkeypatch.setattr(cwapu, "overall_dashes", 42)
        monkeypatch.setattr(cwapu, "overall_spaces", 61)
        monkeypatch.setattr(cwapu, "overall_dots", 47)
        cwapu.RxingContest({})
        miei = [c for c in banco["cw"].chiamate if c["vol"] is None]
        dal_contest = [c for c in miei if c["l"] is not None]
        assert dal_contest, [c["msg"] for c in miei]
        assert all((c["l"], c["s"], c["p"]) == (42, 61, 47) for c in dal_contest), [(c["msg"], c["l"], c["s"], c["p"]) for c in dal_contest]
        # E il silenzio del ? attaccato si calcola con il mio peso degli spazi.
        testi = [c["msg"] for c in miei]
        punto = testi.index("?")
        prima, dopo = miei[punto - 1], miei[punto]
        fine_prima = prima["quando"] + (prima["ritardo"] or 0.0) + max(0.2, len(prima["msg"]) * 0.06)
        silenzio = dopo["quando"] + (dopo["ritardo"] or 0.0) - fine_prima
        assert silenzio == pytest.approx(cwapu.buco_fra_pezzi(cwapu.overall_speed, 61, False), abs=1e-6)

    def test_il_messaggio_accodato_arriva_al_motore_in_un_elenco_solo(self, monkeypatch):
        """Le stazioni devono ricevere nominativo e punto interrogativo
        insieme: due fini di trasmissione costerebbero loro due punti di
        pazienza per una chiamata sola."""
        copione = [*scrivi(3.0, "DL3XY"), (3.6, "f5"), (3.7, "f7"), (12.0, "alt-x")]
        banco = prepara(monkeypatch, copione, minuti=1)
        cwapu.RxingContest({})
        contest = banco["contest"][0]
        assert ct.Msg.SUO in contest.io_messaggi and ct.Msg.QM in contest.io_messaggi, contest.io_messaggi

    def test_esc_svuota_la_coda(self, monkeypatch):
        """Chi si accorge di aver premuto il tasto sbagliato vuole il silenzio
        subito, non il messaggio dopo."""
        copione = [*scrivi(3.0, "DL3XY"), (3.6, "f5"), (3.7, "f7"), (3.8, "\x1b"), (12.0, "alt-x")]
        banco = prepara(monkeypatch, copione, minuti=1)
        cwapu.RxingContest({})
        miei = [c["msg"] for c in banco["cw"].chiamate if c["vol"] is None]
        assert "?" not in miei, miei

    def test_il_fruscio_non_si_riaccende_fra_due_messaggi_accodati(self, monkeypatch):
        """Fra un pezzo e l'altro sto ancora trasmettendo: il ricevitore deve
        restare zitto."""
        copione = [*scrivi(3.0, "DL3XY"), (3.6, "f5"), (3.7, "f7"), (12.0, "alt-x")]
        banco = prepara(monkeypatch, copione, minuti=1, contest={"qrn": True})
        cwapu.RxingContest({})
        # Un ciclo acceso per ogni ritorno in ascolto: se il fondo si fosse
        # riacceso fra i due messaggi ce ne sarebbe uno in piu'.
        assert len(banco["acustica"].cicli) <= len([t for t in banco["cw"].testi if not t.startswith("_ ")])

    def test_le_frecce_muovono_il_cursore_dentro_il_campo(self, monkeypatch, capsys):
        """Il carattere sbagliato si sostituisce dove sta, senza cancellare
        tutto quello che gli viene dopo."""
        copione = [*scrivi(3.0, "DL2XY"), (3.6, "left"), (3.7, "left"), (3.8, "left"), (3.9, "delete"), (4.0, "3"), (6.0, "alt-x")]
        prepara(monkeypatch, copione)
        cwapu.RxingContest({})
        assert "CALL: DL3XY" in capsys.readouterr().out

    def test_home_e_fine_saltano_agli_estremi_del_campo(self, monkeypatch, capsys):
        copione = [*scrivi(3.0, "L3XY"), (3.6, "home"), (3.7, "d"), (3.8, "end"), (3.9, "/"), (6.0, "alt-x")]
        prepara(monkeypatch, copione)
        cwapu.RxingContest({})
        assert "CALL: DL3XY/" in capsys.readouterr().out

    def test_il_backspace_toglie_il_carattere_prima_del_cursore(self, monkeypatch, capsys):
        copione = [*scrivi(3.0, "DLL3XY"), (3.6, "left"), (3.7, "left"), (3.8, "left"), (3.9, "\x08"), (6.0, "alt-x")]
        prepara(monkeypatch, copione)
        cwapu.RxingContest({})
        assert "CALL: DL3XY" in capsys.readouterr().out

    def test_in_testa_al_campo_il_backspace_non_tocca_niente(self, monkeypatch, capsys):
        """Come in un editor: a colonna zero non si cancella all'indietro."""
        copione = [*scrivi(3.0, "DL3XY"), (3.6, "home"), (3.7, "\x08"), (3.8, "\x08"), (6.0, "alt-x")]
        prepara(monkeypatch, copione)
        cwapu.RxingContest({})
        assert "CALL: DL3XY" in capsys.readouterr().out

    def test_la_riga_porta_il_cursore_sulla_cella_del_carattere(self, monkeypatch, capsys):
        """Il cursore di sistema, cioe' quello che il display braille mostra,
        finisce sul carattere su cui sto: la riga si stampa intera e poi si
        riscrive il solo pezzo che lo precede."""
        copione = [*scrivi(3.0, "DL3XY"), (3.6, "left"), (3.7, "left"), (6.0, "alt-x")]
        prepara(monkeypatch, copione)
        cwapu.RxingContest({})
        assert "+0 -0 =0 CALL: DL3XY\r+0 -0 =0 CALL: DL3" in capsys.readouterr().out

    def test_la_velocita_del_qso_non_viene_dalle_stazioni_di_disturbo(self, monkeypatch, capsys):
        """Le stazioni di disturbo nascono fra trenta e cinquanta parole al
        minuto a prescindere dalla mia: con il QRM acceso la riga delle
        velocita' misurava loro invece di chi stavo copiando."""
        copione = [*scrivi(3.0, "DL3XY"), (3.6, "\r"), *scrivi(9.0, "1"), (9.5, "\r"), (20.0, "alt-x")]
        banco = prepara(monkeypatch, copione, minuti=2, contest={"qrm": True, "qrm_massime": 5})
        cwapu.RxingContest({})
        uscita = capsys.readouterr().out
        assert "ti ho inviato 1 QRZ" in uscita, uscita[-600:]
        # La stazione che ho lavorato e' l'unica che manda il mio nominativo.
        sue = {c["wpm"] for c in banco["cw"].chiamate if c["vol"] is not None and "DL3XY" in (c["msg"] or "")}
        assert sue, "la stazione lavorata non ha mai trasmesso"
        dettagli = cwapu.app_data["historical_rx_data_contest"]["sessions_log"][-1]["item_details"]
        assert [d["rwpm"] for d in dettagli] and all(d["rwpm"] in sue for d in dettagli), (dettagli, sue)

    def test_il_rapporto_svelto_esce_in_due_pezzi_allineati(self, monkeypatch):
        """Il messaggio si spezza, ma i pezzi partono tutti nello stesso giro
        di ciclo e con il silenzio giusto in mezzo: aspettare il giro dopo
        aprirebbe un buco di cinquanta millesimi dentro un gruppo."""
        # Lo scambio la stazione lo manda solo dopo che le ho risposto.
        copione = [*scrivi(3.0, "DL3XY"), (3.6, "\r"), (30.0, "alt-x")]
        banco = prepara(
            monkeypatch,
            copione,
            minuti=2,
            contest={"pileup": True, "pileup_massime": 9, "scambio_veloce": True, "scambio_probabilita": 100, "scambio_incremento": 20},
        )
        cwapu.RxingContest({})
        scambi = [c for c in banco["cw"].chiamate if c["vol"] is not None and c["ritardo"]]
        assert scambi, [c["msg"] for c in banco["cw"].chiamate]
        # Il pezzo che segue porta davanti il silenzio di tutto cio' che lo
        # precede, invece di aspettare il giro dopo.
        assert all(c["ritardo"] > 0 for c in scambi)
        # E il primo pezzo e' il rapporto, tre caratteri, piu' svelto del resto.
        rapporti = [c for c in banco["cw"].chiamate if c["vol"] is not None and len(c["msg"]) == 3 and c["msg"][0] == "5"]
        assert rapporti, [c["msg"] for c in banco["cw"].chiamate]
        # Il rapporto va piu' svelto del resto del messaggio.
        lenti = [c["wpm"] for c in banco["cw"].chiamate if c["vol"] is not None and c["msg"].startswith("TT")]
        assert lenti and all(r["wpm"] > min(lenti) for r in rapporti), (rapporti, lenti)

    def test_senza_lo_switcher_nessun_messaggio_si_spezza(self, monkeypatch):
        copione = [*scrivi(3.0, "DL3XY"), (3.6, "\r"), (30.0, "alt-x")]
        banco = prepara(monkeypatch, copione, minuti=2, contest={"pileup": True, "pileup_massime": 9, "scambio_veloce": False})
        cwapu.RxingContest({})
        assert not [c for c in banco["cw"].chiamate if c["ritardo"] and c["vol"] is not None]

    def test_il_buco_fra_i_pezzi_segue_la_misura(self):
        """Misurato su CWzator: fra due lettere 2,9 unita' con i pesi standard,
        fra due parole 6,9."""
        unita = 1.2 / 25
        assert cwapu.buco_fra_pezzi(25, 50, False) == pytest.approx(unita * 2.9)
        assert cwapu.buco_fra_pezzi(25, 50, True) == pytest.approx(unita * 6.9)
        assert cwapu.buco_fra_pezzi(25, 25, False) == pytest.approx(unita * 1.4)
        assert cwapu.buco_fra_pezzi(25, 75, True) == pytest.approx(unita * 10.4)

    def test_un_insieme_di_suoni_si_ferma_tutto_insieme(self):
        """Fermandone uno solo, gli altri continuerebbero a suonare sotto la
        mia trasmissione."""

        class Finto:
            def __init__(self):
                self.fermato = False
                self.is_playing = self

            def is_set(self):
                return not self.fermato

            def stop(self):
                self.fermato = True

        pezzi = [Finto(), Finto(), Finto()]
        insieme = cwapu.InsiemeDiSuoni(pezzi, 1.5)
        assert insieme.is_playing.is_set()
        insieme.stop()
        assert all(p.fermato for p in pezzi)
        assert not insieme.is_playing.is_set()
        assert insieme.durata == 1.5

    def test_le_stazioni_che_nascono_mentre_trasmetto_non_si_sentono(self, monkeypatch):
        """Il ricevitore si zittiva una volta sola, all'inizio della mia
        trasmissione: le stazioni di disturbo, che nascono quando vogliono, mi
        partivano sopra a piena voce."""
        copione = [(1.0, "f1"), (2.0, "f1"), (3.0, "f1"), (30.0, "alt-x")]
        banco = prepara(monkeypatch, copione, minuti=2, contest={"qrm": True, "qrm_massime": 5, "pileup": True, "pileup_massime": 9})
        cwapu.RxingContest({})
        assert banco["zittite"], "nessuna stazione e' stata zittita"

    def test_esc_sulla_mia_risposta_riporta_la_riga_al_nominativo(self, monkeypatch, capsys):
        """La stazione ha sentito spazzatura e non parlera' piu': restando sul
        numero, l'Invio metteva a log un QSO che lei non aveva concluso, e
        usciva NIL ogni volta."""
        copione = [*scrivi(3.0, "DL3XY"), (3.6, "\r"), (3.9, "\x1b"), (8.0, "alt-x")]
        prepara(monkeypatch, copione)
        cwapu.RxingContest({})
        uscita = capsys.readouterr().out
        assert "CALL: DL3XY" in uscita
        assert uscita.rindex("CALL: DL3XY") > uscita.rindex("5NN NR:")

    def test_esc_senza_trasmettere_lascia_la_riga_dov_e(self, monkeypatch, capsys):
        """Li' la mia risposta e' andata in aria davvero: azzerare il numero mal
        copiato e riscriverlo e' il gesto giusto."""
        copione = [*scrivi(3.0, "DL3XY"), (3.6, "\r"), *scrivi(9.0, "12"), (9.6, "\x1b"), (12.0, "alt-x")]
        prepara(monkeypatch, copione)
        cwapu.RxingContest({})
        uscita = capsys.readouterr().out
        assert "5NN NR:" in uscita[uscita.rindex("DL3XY") :] or "5NN NR:" in uscita

    def test_le_rinunce_a_schermo_solo_quando_il_diario_non_le_avra(self, monkeypatch, capsys):
        """L'elenco dei nominativi a schermo e' rumore che scorre via. Ma una
        sessione senza QSO a log nel diario non ci finisce, quindi li' l'unico
        posto dove dirlo e' lo schermo."""
        # Un QSO a log e poi qualche CQ a vuoto, cosi' nascono stazioni che
        # si stancano di aspettare.
        copione = [*scrivi(3.0, "DL3XY"), (3.6, "\r"), *scrivi(9.0, "1"), (9.5, "\r"), (20.0, "f1"), (40.0, "f1"), (110.0, "alt-x")]
        banco = prepara(monkeypatch, copione, minuti=3, contest={"pileup": True, "pileup_massime": 9})
        cwapu.RxingContest({})
        uscita = capsys.readouterr().out
        contest = banco["contest"][0]
        assert contest.punteggio.rinunce, "nessuna stazione se n'e' andata"
        assert contest.punteggio.punti_grezzi >= 1
        assert "Se ne sono andate" not in uscita
        assert "Se ne sono andate" in banco["diario"].getvalue()

    def test_alt_s_resta_sotto_le_dita(self, monkeypatch, capsys):
        """La riga finisce con un ritorno a capo senza andare a capo davvero:
        il cursore resta li' e il display braille la mostra da solo."""
        prepara(monkeypatch, [(5.0, "alt-s"), (7.0, "alt-x")])
        cwapu.RxingContest({})
        uscita = capsys.readouterr().out
        assert "QSO 0 PT 0" in uscita
        inizio = uscita.index("QSO 0 PT 0")
        assert "\r" in uscita[inizio : inizio + 120], repr(uscita[inizio : inizio + 120])

    def test_alt_s_dice_quanto_manca(self, monkeypatch, capsys):
        prepara(monkeypatch, [(5.0, "alt-s"), (7.0, "alt-x")], quanti_qso=8)
        cwapu.RxingContest({})
        assert "-8 QSO" in capsys.readouterr().out

    def test_alt_s_dice_quanto_manca_anche_a_tempo(self, monkeypatch, capsys):
        prepara(monkeypatch, [(5.0, "alt-s"), (7.0, "alt-x")], minuti=2)
        cwapu.RxingContest({})
        uscita = capsys.readouterr().out
        assert "-1:" in uscita, uscita[-300:]

    def test_il_contest_salva_appena_finisce(self, monkeypatch):
        """Le impostazioni si salvavano una volta sola, uscendo dal menu: chi
        faceva sette contest in un pomeriggio li aveva tutti nel diario e
        nessuno nell'archivio finche' non chiudeva."""
        copione = [*scrivi(3.0, "DL3XY"), (3.6, "\r"), *scrivi(9.0, "1"), (9.5, "\r"), (14.0, "alt-x")]
        banco = prepara(monkeypatch, copione, minuti=2)
        cwapu.RxingContest({})
        assert banco["salvataggi"], "la sessione non e' stata salvata su disco"

    def test_il_salvataggio_non_si_annuncia(self, monkeypatch, capsys):
        """Issue 18: a fine contest arrivavano la riga del diario, quella della
        sessione salvata e quella delle impostazioni. Il salvataggio riuscito
        si da' per scontato; restano numero e durata della sessione."""
        copione = [*scrivi(3.0, "DL3XY"), (3.6, "\r"), *scrivi(9.0, "1"), (9.5, "\r"), (14.0, "alt-x")]
        banco = prepara(monkeypatch, copione, minuti=2)
        cwapu.RxingContest({})
        uscita = capsys.readouterr().out
        assert banco["annunci"] == [False]
        assert "Sessione 1, durata attiva" in uscita
        assert "salvat" not in uscita.lower(), uscita[-400:]

    def test_il_banco_non_scrive_mai_sul_file_vero(self, monkeypatch):
        """Regola della casa: il collaudo sostituisce le funzioni che toccano
        il sistema. Senza, queste prove riscrivono l'archivio di Gabriele, che
        e' di tre megabyte e contiene anni di esercizi."""
        import os

        percorso = cwapu.SETTINGS_FILE
        prima = os.path.getmtime(percorso) if os.path.exists(percorso) else None
        banco = prepara(monkeypatch, [(5.0, "alt-x")])
        cwapu.RxingContest({})
        dopo = os.path.getmtime(percorso) if os.path.exists(percorso) else None
        assert prima == dopo, "il banco ha toccato il file di impostazioni vero"
        assert banco["salvataggi"] is not None

    def test_l_invio_non_ripete_cio_che_ho_gia_detto(self, monkeypatch):
        """Il primo Invio manda il suo nominativo con il mio scambio; il
        secondo, quando ho copiato il suo, chiude e basta. Prima rimandava
        tutto da capo ogni volta."""
        copione = [*scrivi(3.0, "DL3XY"), (3.6, "\r"), *scrivi(12.0, "1"), (12.5, "\r"), (20.0, "alt-x")]
        banco = prepara(monkeypatch, copione, minuti=2)
        cwapu.RxingContest({})
        miei = [c["msg"] for c in banco["cw"].chiamate if c["vol"] is None]
        # Il nominativo con lo scambio una volta sola, e poi il solo TU.
        assert any(m.startswith("DL3XY 5NN") for m in miei), miei
        # L'ultimo messaggio del contest e' il saluto d'uscita.
        assert miei[-2] in ct.CHIUSURE, miei
        assert sum(1 for m in miei if m.startswith("DL3XY 5NN")) == 1, miei

    def test_dopo_f2_l_invio_non_rimanda_lo_scambio(self, monkeypatch):
        """Se il DX mi chiede il progressivo io glielo mando con F2: l'Invio
        poi chiude e basta, senza ripetere tutto."""
        copione = [*scrivi(3.0, "DL3XY"), (3.6, "\r"), (12.0, "f2"), *scrivi(20.0, "1"), (20.5, "\r"), (28.0, "alt-x")]
        banco = prepara(monkeypatch, copione, minuti=2)
        cwapu.RxingContest({})
        miei = [c["msg"] for c in banco["cw"].chiamate if c["vol"] is None]
        assert miei[-2] in ct.CHIUSURE, miei

    def test_dopo_f5_l_invio_rimanda_lo_scambio(self, monkeypatch):
        """Se sono tornato a ripetere il suo nominativo, vuol dire che il primo
        scambio non e' arrivato: va rimandato."""
        copione = [*scrivi(3.0, "DL3XY"), (3.6, "\r"), (12.0, "f5"), *scrivi(20.0, "1"), (20.5, "\r"), (28.0, "alt-x")]
        banco = prepara(monkeypatch, copione, minuti=2)
        cwapu.RxingContest({})
        miei = [c["msg"] for c in banco["cw"].chiamate if c["vol"] is None]
        # L'ultimo messaggio porta lo scambio, non il solo TU.
        assert any("5NN" in m for m in miei[-3:]), miei

    def test_dopo_il_punto_interrogativo_l_invio_non_rimanda_lo_scambio(self, monkeypatch):
        """Riprova AB, passo 4: chiedere il suo numero non vuol dire che lei non
        abbia il mio. Dopo il ? e il suo numero, l'Invio chiude e basta."""
        copione = [*scrivi(3.0, "DL3XY"), (3.6, "\r"), (10.0, "\r"), *scrivi(16.0, "1"), (16.5, "\r"), (24.0, "alt-x")]
        banco = prepara(monkeypatch, copione, minuti=2)
        cwapu.RxingContest({})
        miei = [c["msg"] for c in banco["cw"].chiamate if c["vol"] is None]
        assert "?" in miei, miei
        dopo = miei[miei.index("?") + 1]
        assert dopo in ct.CHIUSURE, miei

    def test_dopo_f5_l_invio_manda_solo_lo_scambio(self, monkeypatch):
        """Il nominativo gliel'ho appena dato: basta lo scambio."""
        copione = [*scrivi(3.0, "DL3XY"), (3.6, "f5"), (8.0, "\r"), (16.0, "alt-x")]
        banco = prepara(monkeypatch, copione, minuti=2)
        cwapu.RxingContest({})
        miei = [c["msg"] for c in banco["cw"].chiamate if c["vol"] is None]
        assert "DL3XY" in miei, miei
        dopo = miei[miei.index("DL3XY") + 1]
        assert dopo.startswith("5NN"), miei

    def test_dopo_f5_e_f2_l_invio_passa_al_numero_in_silenzio(self, monkeypatch, capsys):
        """Riprova AB, passo 2: le ho gia' detto tutto, e l'Invio mandava un ?
        che la costringeva a ripetere un numero gia' copiato."""
        copione = [*scrivi(3.0, "DL3XY"), (3.6, "f5"), (8.0, "f2"), (13.0, "\r"), (16.0, "alt-x")]
        banco = prepara(monkeypatch, copione, minuti=2)
        cwapu.RxingContest({})
        miei = [c["msg"] for c in banco["cw"].chiamate if c["vol"] is None]
        assert "?" not in miei, miei
        assert "DL3XY 5NN NR:" in capsys.readouterr().out

    def test_le_spie_valgono_solo_per_il_nominativo_a_cui_ho_parlato(self, monkeypatch):
        """F5 e F2 a DL3XY, poi nella riga il nominativo diventa DL3XZ: a lui non
        ho detto niente, e l'Invio deve mandargli nominativo e scambio invece di
        passare al numero in silenzio."""
        copione = [
            *scrivi(3.0, "DL3XY"),
            (3.6, "f5"),
            (8.0, "f2"),
            (13.0, "\x08"),
            (13.1, "Z"),
            (13.5, "\r"),
            (20.0, "alt-x"),
        ]
        banco = prepara(monkeypatch, copione, minuti=2)
        cwapu.RxingContest({})
        miei = [c["msg"] for c in banco["cw"].chiamate if c["vol"] is None]
        assert any(m.startswith("DL3XZ 5NN") for m in miei), miei

    def test_senza_lo_scambio_l_invio_chiede_la_ripetizione(self, monkeypatch):
        """Le ho gia' detto tutto e non ho il suo numero: il punto interrogativo
        e' il modo di chiederglielo."""
        copione = [*scrivi(3.0, "DL3XY"), (3.6, "\r"), (14.0, "\r"), (20.0, "alt-x")]
        banco = prepara(monkeypatch, copione, minuti=2)
        cwapu.RxingContest({})
        miei = [c["msg"] for c in banco["cw"].chiamate if c["vol"] is None]
        assert "?" in miei, miei

    def test_alt_w_dimentica_cio_che_avevo_detto(self, monkeypatch):
        copione = [*scrivi(3.0, "DL3XY"), (3.6, "\r"), (12.0, "alt-w"), *scrivi(14.0, "DL3XY"), (14.6, "\r"), (22.0, "alt-x")]
        banco = prepara(monkeypatch, copione, minuti=2)
        cwapu.RxingContest({})
        miei = [c["msg"] for c in banco["cw"].chiamate if c["vol"] is None]
        assert sum(1 for m in miei if m.startswith("DL3XY 5NN")) == 2, miei

    def test_il_mio_5nn_e_accelerato_sempre_quando_l_interruttore_e_acceso(self, monkeypatch):
        """Il mio non tira la probabilita': se l'interruttore e' acceso il mio
        rapporto e' sempre piu' veloce, perche' e' una mia abitudine."""
        copione = [*scrivi(3.0, "DL3XY"), (3.6, "\r"), (20.0, "alt-x")]
        banco = prepara(monkeypatch, copione, minuti=2, contest={"scambio_veloce": True, "scambio_probabilita": 1, "scambio_incremento": 25})
        cwapu.RxingContest({})
        miei = [c for c in banco["cw"].chiamate if c["vol"] is None]
        rapporti = [c for c in miei if c["msg"] == "5NN"]
        assert rapporti, [c["msg"] for c in miei]
        lenti = [c["wpm"] for c in miei if c["msg"] == "DL3XY"]
        assert lenti and all(r["wpm"] > min(lenti) for r in rapporti), (rapporti, lenti)

    def test_con_l_interruttore_spento_il_mio_5nn_e_normale(self, monkeypatch):
        copione = [*scrivi(3.0, "DL3XY"), (3.6, "\r"), (20.0, "alt-x")]
        banco = prepara(monkeypatch, copione, minuti=2, contest={"scambio_veloce": False})
        cwapu.RxingContest({})
        miei = [c for c in banco["cw"].chiamate if c["vol"] is None]
        assert not [c for c in miei if c["ritardo"]], [c["msg"] for c in miei]

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
        assert "manipolazione manuale al 30%" in riga
        assert "QRM" not in riga

    def test_il_pannello_dice_cio_che_e_acceso(self):
        stati = dict(cwapu.CONTEST_PREDEFINITI, pileup=True, pileup_massime=6, qrm=True, qrm_massime=3, tasto_verticale=False)
        riga = cwapu.descrivi_pannello_contest(stati)
        assert "pile-up fino a 6 stazioni, propagazione 50" in riga
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
        assert "Se ne sono andate 1: F5IN." in intero
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
        sessione = cwapu.app_data["historical_rx_data_contest"]["sessions_log"][-1]
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


class TestChiusure:
    """Non si chiude sempre con TU, ne' io ne' loro."""

    def test_la_mia_chiusura_varia_con_il_tu_prevalente(self):
        m = ct.Contest("IZ4APU", 25, 600, lambda: "DL3XY", seme=5)
        m.suo_nominativo = "DL3XY"
        chiusure = [m.testo_mio([ct.Msg.TU]) for _ in range(1000)]
        assert set(chiusure) <= set(ct.CHIUSURE)
        assert len(set(chiusure)) == len(ct.CHIUSURE), set(chiusure)
        quota = chiusure.count("TU") / len(chiusure)
        assert 0.55 < quota < 0.65, quota

    def test_una_stazione_su_cinque_saluta(self):
        salutano = 0
        prove = 400
        for seme in range(prove):
            m = ct.Contest("IZ4APU", 25, 600, lambda: "DL3XY", seme=seme)
            s = ct.StazioneDX(m, 0.0, singola=True)
            m.stazioni.append(s)
            s.oper.stato = ct.StatoOp.FATTO
            esito = m.avanza(1.0)
            saluti = [r for r in esito.richieste if r.stazione == s.id]
            if saluti:
                salutano += 1
                r = saluti[0]
                assert r.testo in ct.SALUTI
                assert ct.RITARDO_SALUTO[0] <= r.ritardo <= ct.RITARDO_SALUTO[1]
                # Il saluto non porta la velocita' del QSO, gia' presa.
                assert r.dx is False
        assert 0.15 < salutano / prove < 0.25, salutano / prove
