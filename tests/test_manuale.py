# Prove automatiche di CWapu, la guida in linea.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' UltraCode).
# La guida e' un file a parte, quindi puo' sparire da una compilazione senza
# che nessuno se ne accorga finche' un utente non preme g. Queste prove
# verificano che ci sia, che sia leggibile e che la struttura per intestazioni,
# cioe' il modo in cui la si naviga con il lettore di schermo, regga.

import html.parser
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cwapu

PERCORSO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), cwapu.MANUALE_NAME)


def leggi_guida():
    with open(PERCORSO, encoding="utf-8") as f:
        return f.read()


class ContaTag(html.parser.HTMLParser):
    """Raccoglie intestazioni e ancore, e verifica che i tag si chiudano."""

    def __init__(self):
        super().__init__()
        self.aperti = []
        self.intestazioni = []
        self.ancore = set()
        self.rimandi = set()
        self.livello_corrente = None
        self.senza_chiusura = {"meta", "br", "hr", "img", "link", "input"}

    def handle_starttag(self, tag, attrs):
        attributi = dict(attrs)
        if tag not in self.senza_chiusura:
            self.aperti.append(tag)
        if tag in ("h1", "h2", "h3"):
            self.livello_corrente = int(tag[1])
            if "id" in attributi:
                self.ancore.add(attributi["id"])
        if "id" in attributi:
            self.ancore.add(attributi["id"])
        if tag == "a" and attributi.get("href", "").startswith("#"):
            self.rimandi.add(attributi["href"][1:])

    def handle_endtag(self, tag):
        if tag in self.senza_chiusura:
            return
        if self.aperti and self.aperti[-1] == tag:
            self.aperti.pop()
        elif tag in self.aperti:
            while self.aperti and self.aperti.pop() != tag:
                pass

    def handle_data(self, dato):
        if self.livello_corrente and dato.strip():
            self.intestazioni.append((self.livello_corrente, dato.strip()))
            self.livello_corrente = None


def analizza():
    parser = ContaTag()
    parser.feed(leggi_guida())
    return parser


class TestEsistenza:
    def test_la_guida_e_nella_cartella_del_programma(self):
        assert os.path.exists(PERCORSO), f"manca {cwapu.MANUALE_NAME}"

    def test_e_dichiarata_nella_ricetta_di_compilazione(self):
        """Senza questa riga l'eseguibile esce senza guida e il tasto g non
        trova niente da aprire."""
        percorso_spec = os.path.join(os.path.dirname(PERCORSO), "cwapu.spec")
        with open(percorso_spec, encoding="utf-8") as f:
            assert cwapu.MANUALE_NAME in f.read()

    def test_user_file_path_la_trova(self):
        assert os.path.exists(cwapu.user_file_path(cwapu.MANUALE_NAME))


class TestStruttura:
    def test_i_tag_si_chiudono_tutti(self):
        parser = analizza()
        assert parser.aperti == [], f"tag rimasti aperti: {parser.aperti}"

    def test_la_lingua_e_dichiarata_italiana(self):
        """Serve al lettore di schermo per scegliere la voce giusta, e ai
        browser per proporre la traduzione automatica."""
        assert re.search(r'<html[^>]*\blang="it"', leggi_guida())

    def test_c_e_una_sola_intestazione_di_primo_livello(self):
        parser = analizza()
        primo_livello = [t for livello, t in parser.intestazioni if livello == 1]
        assert len(primo_livello) == 1

    def test_le_sezioni_principali_ci_sono_tutte(self):
        parser = analizza()
        titoli = " ".join(t.lower() for _, t in parser.intestazioni)
        for atteso in ("menu principale", "ricezione", "contest", "conteggio", "trasmissione", "appunti", "dizionario", "statistiche", "diario", "glossario"):
            assert atteso in titoli, f"manca la sezione su {atteso}"

    def test_ogni_rimando_interno_ha_la_sua_ancora(self):
        """Un indice che porta nel vuoto e' peggio di nessun indice."""
        parser = analizza()
        rotti = sorted(parser.rimandi - parser.ancore)
        assert rotti == [], f"rimandi senza destinazione: {rotti}"


class TestContenuto:
    def test_dice_che_esiste_solo_in_italiano(self):
        testo = leggi_guida().lower()
        assert "soltanto in italiano" in testo
        assert "traduzione automatica" in testo

    def test_riporta_gli_autori(self):
        testo = leggi_guida()
        assert "IZ4APU" in testo
        assert "ClaudIA" in testo

    def test_la_versione_coincide_con_quella_del_programma(self):
        """Una guida che dichiara una versione diversa da quella che apre
        confonde chi segnala un problema."""
        assert cwapu.VERSION in leggi_guida()

    def test_i_comandi_del_menu_principale_sono_tutti_documentati(self):
        testo = leggi_guida()
        for tasto in cwapu.MNMAIN:
            assert f"<kbd>{tasto}</kbd>" in testo, f"il tasto {tasto} non e' documentato"
