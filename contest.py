# contest.py - Il motore del contest di CWapu: stazioni, operatori, pile-up e punteggio.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Fable 5.1, modalita' auto).
# Nato il 18 settembre 2026 con la issue 7 di cwapu.
# La macchina a stati delle stazioni, il QRM, il prefisso e il punteggio sono
# portati da cwsim di Kevin Schmidt, W9CF, https://github.com/w9cf/cwsim, che
# e' la traduzione in Python di Morse Runner di Alex Shovkoplyas, VE3NEA.
# Tutti e due sono sotto GPL, e questo file resta sotto la GPL-3 di CWapu.
"""Il motore del contest, senza audio e senza tastiera.

Qui dentro non c'e' una stampa, una lettura di tasti, un suono ne' una
variabile globale di cwapu.py: il motore riceve gli eventi e restituisce cio'
che va suonato, come richieste con stazione, testo, velocita', tono, pesi,
volume e panoramica. E' questo che lo rende collaudabile: si prova con un
orologio finto e un generatore casuale a seme fisso.

Il tempo e' in secondi, letti da chi chiama e passati ad avanza(). cwsim
contava in buffer audio da 46 millesimi; qui ogni giro del ciclo di cwapu e'
un tick, e le scadenze sono istanti assoluti.

Chi usa il motore, cioe' il ciclo del contest in cwapu.py, fa tre cose: chiama
avanza(adesso, finite) a ogni giro, dicendo quali trasmissioni sono finite
dall'ultimo giro; suona le richieste che riceve; e chiama io_trasmetti quando
l'operatore manda qualcosa, io_finito quando la sua trasmissione e' finita,
registra_qso quando mette un QSO a log.
"""

import enum
import math
import random
from dataclasses import dataclass, field

IO = "io"
PAZIENZA_PIENA = 5
ABILITA = 2
SCALA_RAYLEIGH = 3.191538  # media 4, cioe' 4 per radice di 2 su pi greco
SKILLS_ATTESA = 6
INTERVALLO_QRM = 240.0  # il tqrm di cwsim: un disturbo ogni quattro minuti
PESO_STANDARD = (30, 50, 50)
PAN_MASSIMO = 100.0


def numero_come_testo(rng, rst, nr, errore=False):
    """Rapporto e numero come li manda un operatore vero: 5NN, T e O per lo zero, N per il nove.

    Con l'errore chiesto il numero esce sbagliato di uno o di dieci e viene
    corretto con la serie di e e la ripetizione, come in cwsim. La usano le
    stazioni e la uso io: il mio scambio esce nella stessa forma del loro,
    non con il numero nudo accanto al rapporto.
    """
    testo = f"{int(rst)}{int(nr):03d}"
    if errore:
        if testo[-1] in "234567":
            sbagliato = nr - 1 if rng.random() < 0.5 else nr + 1
            testo = f"{int(rst)}{sbagliato:03d}eeeee {int(nr):03d}"
        elif testo[-2] in "234567":
            sbagliato = nr - 10 if rng.random() < 0.5 else nr + 10
            testo = f"{int(rst)}{sbagliato:03d}eeeee {int(nr):03d}"
    testo = testo.replace("599", "5NN").replace("000", "TTT").replace("00", "TT")
    if rng.random() < 0.4:
        testo = testo.replace("0", "O")
    elif rng.random() < 0.97:
        testo = testo.replace("0", "T")
    if rng.random() < 0.97:
        testo = testo.replace("9", "N")
    return testo


class Msg(enum.Enum):
    """I messaggi che le stazioni sanno mandare e riconoscere, come in cwsim."""

    NESSUNO = enum.auto()
    CQ = enum.auto()
    NR = enum.auto()
    TU = enum.auto()
    MIO = enum.auto()
    SUO = enum.auto()
    B4 = enum.auto()
    QM = enum.auto()
    NIL = enum.auto()
    SPAZZATURA = enum.auto()
    R_NR = enum.auto()
    R_NR2 = enum.auto()
    DE_MIO1 = enum.auto()
    DE_MIO2 = enum.auto()
    DE_MIO_NR1 = enum.auto()
    DE_MIO_NR2 = enum.auto()
    NR_QM = enum.auto()
    CQ_LUNGO = enum.auto()
    MIO_NR2 = enum.auto()
    QRL = enum.auto()
    QRL2 = enum.auto()
    QSY = enum.auto()
    AGN = enum.auto()


# Il testo di ogni messaggio: <my> e' chi trasmette, <his> il corrispondente,
# <#> il rapporto con il numero. Per la stazione DX <my> e' il suo nominativo
# e <his> il mio; per me e' il contrario.
TESTI = {
    Msg.CQ: "CQ TEST <my>",
    Msg.NR: "<#>",
    Msg.TU: "TU",
    Msg.MIO: "<my>",
    Msg.SUO: "<his>",
    Msg.B4: "QSO B4",
    Msg.QM: "?",
    Msg.NIL: "NIL",
    Msg.R_NR: "R <#>",
    Msg.R_NR2: "R <#> <#>",
    Msg.DE_MIO1: "DE <my>",
    Msg.DE_MIO2: "DE <my> <my>",
    Msg.DE_MIO_NR1: "DE <my> <#>",
    Msg.DE_MIO_NR2: "DE <my> <my> <#>",
    Msg.MIO_NR2: "<my> <my> <#>",
    Msg.NR_QM: "NR?",
    Msg.CQ_LUNGO: "CQ CQ TEST <my> <my> TEST",
    Msg.QRL: "QRL?",
    Msg.QRL2: "QRL? QRL?",
    Msg.QSY: "<his> QSY QSY",
    Msg.AGN: "AGN",
}


class Stato(enum.Enum):
    """Lo stato di una stazione: ascolta, copia cio' che dico, prepara la risposta, trasmette, o va tolta."""

    ASCOLTA = enum.auto()
    COPIA = enum.auto()
    PREPARA = enum.auto()
    TRASMETTE = enum.auto()
    DA_TOGLIERE = enum.auto()


class Evento(enum.Enum):
    SCADENZA = enum.auto()
    MESSAGGIO_INVIATO = enum.auto()
    IO_INIZIO = enum.auto()
    IO_FINE = enum.auto()


class StatoOp(enum.Enum):
    """Cosa l'operatore della stazione DX sta aspettando da me."""

    ATTENDE_FINE = enum.auto()
    VUOLE_QSO = enum.auto()
    VUOLE_NR = enum.auto()
    VUOLE_CALL = enum.auto()
    VUOLE_CALL_NR = enum.auto()
    VUOLE_FINE = enum.auto()
    FATTO = enum.auto()
    FALLITO = enum.auto()


class Copia(enum.Enum):
    """Quanto il nominativo che ho mandato somiglia a quello della stazione."""

    SI = enum.auto()
    QUASI = enum.auto()
    NO = enum.auto()


@dataclass
class Richiesta:
    """Un messaggio da suonare: chi lo manda e con quale voce."""

    stazione: str
    testo: str
    wpm: int
    pitch: int
    l: int
    s: int
    p: int
    volume: float
    pan: float
    messaggi: tuple


@dataclass
class Esito:
    """Cio' che un giro di avanza() restituisce: le richieste di suono e gli eventi da riferire."""

    richieste: list = field(default_factory=list)
    eventi: list = field(default_factory=list)


def poisson(rng, media):
    """Un'estrazione di Poisson con l'algoritmo di Knuth: le medie qui sono piccole."""
    if media <= 0:
        return 0
    limite = math.exp(-media)
    conteggio = 0
    prodotto = rng.random()
    while prodotto > limite:
        conteggio += 1
        prodotto *= rng.random()
    return conteggio


def rayleigh(rng, scala):
    """Un'estrazione di Rayleigh, come la pazienza iniziale di Morse Runner."""
    return scala * math.sqrt(-2.0 * math.log(1.0 - rng.random()))


def guadagno_filtro(banda_hz, scarto_hz):
    """Quanto il filtro del ricevitore lascia passare un tono a questa distanza dal centro.

    Le voci CW sono toni puri, quindi il filtro di banda del ricevitore di
    cwsim, che lavorava sulla somma dei segnali, qui diventa un volume per
    stazione: piena dentro meta' banda, poi un fianco a coseno che si spegne
    a una banda intera dal centro.
    """
    meta = max(1.0, float(banda_hz)) / 2.0
    fuori = (abs(float(scarto_hz)) - meta) / meta
    if fuori <= 0.0:
        return 1.0
    if fuori >= 1.0:
        return 0.0
    return 0.5 * (1.0 + math.cos(math.pi * fuori))


def prefisso(nominativo):
    """Il prefisso di un nominativo secondo le regole WPX, portato da prefix.py di cwsim.

    E' il moltiplicatore del punteggio: un punto per QSO, un moltiplicatore
    per ogni prefisso distinto.
    """

    def senza_barra(call):
        if not call.isalnum():
            return ""
        if call.isalpha() or (len(call) == 2 and call[0].isdigit()):
            return call + "0"
        ultima_cifra = max(i for i, c in enumerate(call) if c.isdigit()) + 1
        return call[:ultima_cifra] if ultima_cifra > 1 else ""

    parti = nominativo.strip().upper().split("/")
    pfx = senza_barra(parti[0])
    if len(parti) < 2 or (len(parti[1]) > 2 and parti[1].isalpha()):
        return pfx
    if len(parti[1]) == 1:
        if parti[1].isdigit():
            pfx = pfx[:-1] + parti[1]
        return pfx
    if len(parti[0]) > len(parti[1]):
        pfx = senza_barra(parti[1])
    if pfx and pfx[-1].isdigit():
        return pfx
    return pfx + "0"


class Operatore:
    """La macchina a stati dell'operatore di una stazione DX, portata da dxoper.py di cwsim.

    Nasce in ATTENDE_FINE e aspetta un CQ o un TU; a quel punto vuole il QSO
    con una pazienza estratta da una Rayleigh di media 4, e nel dieci per
    cento dei casi chiamera' due volte di fila. Ogni mio messaggio non per
    lui gli costa un punto di pazienza; a zero e' FALLITO e sparisce.
    """

    def __init__(self, rng, motore, nominativo, minuti, singola):
        self.rng = rng
        self.motore = motore
        self.mio = nominativo
        self.stato = StatoOp.ATTENDE_FINE
        self.pazienza = None
        self.ripetizioni = 1
        self.minuti = minuti
        self.singola = singola
        self.sbadati = motore.sbadati
        self.prob_ripeti = 0.1

    def ritardo_invio(self):
        """Quanto aspetta prima di rispondere, in secondi; None se non deve rispondere."""
        if self.stato == StatoOp.ATTENDE_FINE:
            return None
        return 0.1 + 0.5 * self.rng.random()

    def velocita(self, mia):
        """La sua velocita', fra il novanta e il centodieci per cento della mia, arrotondata e non troncata."""
        return round(mia * (0.9 + 0.2 * self.rng.random()))

    def numero(self):
        """Il suo progressivo, che cresce con i minuti di contest e la sua abilita'."""
        return round(1 + self.rng.random() * self.minuti * ABILITA)

    def attesa_risposta(self):
        """Quanto aspetta la mia risposta, in secondi: quattro, piu' o meno il venticinque per cento, fra due e sei."""
        base = float(SKILLS_ATTESA - ABILITA)
        return min(1.5 * base, max(0.5 * base, self.rng.gauss(0.0, 0.25 * base) + base))

    def perdi_pazienza(self):
        if self.stato != StatoOp.FATTO:
            self.pazienza -= 1
            if self.pazienza < 1:
                self.stato = StatoOp.FALLITO

    def imposta_stato(self, stato):
        self.stato = stato
        if stato == StatoOp.VUOLE_QSO:
            self.pazienza = round(rayleigh(self.rng, SCALA_RAYLEIGH))
        else:
            self.pazienza = PAZIENZA_PIENA
        if stato == StatoOp.VUOLE_QSO and not self.singola and self.rng.random() < 0.1:
            self.ripetizioni = 2
        else:
            self.ripetizioni = 1

    def distanza(self, mandato):
        """La distanza di edit fra cio' che ho mandato e il suo nominativo, con il jolly.

        E' la matrice di Morse Runner come sta nell'upstream di cwsim. Nella
        riga finale il passo orizzontale non costa: le lettere del mio
        nominativo che non sono arrivate restano gratuite, e a segnalarle e'
        il confronto di lunghezza dentro confronta(), che declassa a QUASI.
        Il ramo di Gabriele ha perso anche il piu' uno sul passo verticale,
        ed e' il rilievo 8 dell'analisi di cwsim: con quella forma diventava
        gratuita pure l'ultima lettera sbagliata, e DL3XZ valeva DL3XY.
        """
        c0 = self.mio
        c = mandato
        righe = len(c) + 1
        colonne = len(c0) + 1
        m = [[0.0] * colonne for _ in range(righe)]
        for x in range(righe):
            m[x][0] = float(x)
        for x in range(1, len(c)):
            if c[x - 1] != "?":
                for y in range(1, colonne):
                    d = m[x - 1][y - 1] + (0 if c[x - 1] == c0[y - 1] else 1)
                    m[x][y] = min(m[x][y - 1] + 1, m[x - 1][y] + 1, d)
            else:
                for y in range(1, colonne):
                    m[x][y] = min(m[x][y - 1], m[x - 1][y], m[x - 1][y - 1])
        x = len(c)
        if x >= 1:
            if c[x - 1] != "?":
                for y in range(1, colonne):
                    d = m[x - 1][y - 1] + (0 if c[x - 1] == c0[y - 1] else 1)
                    # Riga finale: il passo orizzontale e' gratis, come a monte.
                    m[x][y] = min(m[x][y - 1], m[x - 1][y] + 1, d)
            else:
                for y in range(1, colonne):
                    m[x][y] = min(m[x][y - 1], m[x - 1][y], m[x - 1][y - 1])
        return m[-1][-1]

    def confronta(self, mandato):
        """Se il nominativo che ho mandato e' il suo, quasi, o no, come ismycall di cwsim."""
        c = mandato
        if not c:
            return Copia.NO
        d = self.distanza(c)
        if d == 0:
            esito = Copia.SI
        elif d == 1:
            esito = Copia.QUASI
        else:
            esito = Copia.NO
        if not self.sbadati and len(c) == 2 and esito == Copia.QUASI:
            esito = Copia.NO
        if esito == Copia.SI and (len(c) != len(self.mio) or "?" in c):
            esito = Copia.QUASI
        if len(c.replace("?", "")) < 2:
            esito = Copia.NO
        if self.sbadati and len(c) > 3:
            if esito == Copia.SI:
                if self.rng.random() < 0.01:
                    esito = Copia.QUASI
            elif esito == Copia.QUASI and self.rng.random() < 0.04:
                esito = Copia.SI
        return esito

    def e_il_mio(self):
        """Il confronto con cio' che ho mandato, con la regola di Gabriele sui parziali.

        Decisione D9 del 2026-09-15: un parziale di almeno due caratteri senza
        jolly vale come se finisse con il jolly, cosi' DL3 vale DL3? e la
        stazione ripete il nominativo invece di tacere.
        """
        mandato = (self.motore.suo_nominativo or "").upper()
        esito = self.confronta(mandato)
        if esito == Copia.NO and "?" not in mandato and len(mandato) >= 2:
            con_jolly = self.confronta(mandato + "?")
            if con_jolly != Copia.NO:
                esito = Copia.QUASI
        return esito

    def ricevuto(self, messaggi):
        """Cambia stato in base a cio' che ho mandato: msgReceived di cwsim, modo contest."""
        S = StatoOp
        if Msg.CQ in messaggi:
            if self.stato == S.ATTENDE_FINE:
                self.imposta_stato(S.VUOLE_QSO)
            elif self.stato == S.VUOLE_QSO:
                self.perdi_pazienza()
            elif self.stato in (S.VUOLE_NR, S.VUOLE_CALL, S.VUOLE_CALL_NR):
                self.stato = S.FALLITO
            elif self.stato == S.VUOLE_FINE:
                self.stato = S.FATTO
            return
        if Msg.NIL in messaggi:
            if self.stato == S.ATTENDE_FINE:
                self.imposta_stato(S.VUOLE_QSO)
            elif self.stato == S.VUOLE_QSO:
                self.perdi_pazienza()
            elif self.stato in (S.VUOLE_NR, S.VUOLE_CALL, S.VUOLE_CALL_NR, S.VUOLE_FINE):
                self.stato = S.FALLITO
            return
        if Msg.SUO in messaggi:
            copia = self.e_il_mio()
            if copia == Copia.SI:
                if self.stato in (S.ATTENDE_FINE, S.VUOLE_QSO, S.VUOLE_CALL_NR):
                    self.imposta_stato(S.VUOLE_NR)
                elif self.stato == S.VUOLE_CALL:
                    self.imposta_stato(S.VUOLE_FINE)
            elif copia == Copia.QUASI:
                if self.stato in (S.ATTENDE_FINE, S.VUOLE_QSO, S.VUOLE_NR):
                    self.imposta_stato(S.VUOLE_CALL_NR)
                elif self.stato == S.VUOLE_FINE:
                    self.imposta_stato(S.VUOLE_CALL)
            elif copia == Copia.NO:
                if self.stato == S.VUOLE_QSO:
                    self.stato = S.ATTENDE_FINE
                elif self.stato in (S.VUOLE_NR, S.VUOLE_CALL, S.VUOLE_CALL_NR):
                    self.stato = S.FALLITO
                elif self.stato == S.VUOLE_FINE:
                    self.stato = S.FATTO
        if Msg.B4 in messaggi:
            if self.stato in (S.ATTENDE_FINE, S.VUOLE_QSO):
                self.imposta_stato(S.VUOLE_QSO)
            elif self.stato in (S.VUOLE_NR, S.VUOLE_FINE):
                self.stato = S.FALLITO
        if Msg.NR in messaggi:
            if self.stato == S.VUOLE_QSO:
                self.stato = S.ATTENDE_FINE
            elif self.stato == S.VUOLE_NR:
                if self.rng.random() >= self.prob_ripeti:
                    self.imposta_stato(S.VUOLE_FINE)
            elif self.stato == S.VUOLE_CALL_NR and self.rng.random() >= self.prob_ripeti:
                self.imposta_stato(S.VUOLE_CALL)
        if Msg.TU in messaggi:
            if self.stato == S.ATTENDE_FINE:
                self.imposta_stato(S.VUOLE_QSO)
            elif self.stato == S.VUOLE_FINE:
                self.stato = S.FATTO
        if not self.sbadati and list(messaggi) == [Msg.SPAZZATURA]:
            self.stato = S.ATTENDE_FINE
        if self.stato != S.ATTENDE_FINE:
            self.perdi_pazienza()

    def risposta(self):
        """Cosa manda adesso, dato lo stato, la pazienza e un po' di sorte: getReply di cwsim."""
        S = StatoOp
        if self.stato in (S.ATTENDE_FINE, S.FATTO, S.FALLITO):
            return Msg.NESSUNO
        if self.stato == S.VUOLE_QSO:
            return Msg.MIO
        if self.stato == S.VUOLE_NR:
            if self.pazienza == PAZIENZA_PIENA - 1 or self.rng.random() < 0.3:
                return Msg.NR_QM
            return Msg.AGN
        if self.stato == S.VUOLE_CALL:
            r = self.rng.random()
            if r < 0.5:
                return Msg.DE_MIO_NR1
            if r < 0.625:
                return Msg.DE_MIO_NR2
            return Msg.MIO_NR2
        if self.stato == S.VUOLE_CALL_NR:
            return Msg.DE_MIO1 if self.rng.random() < 0.5 else Msg.DE_MIO2
        if self.pazienza == PAZIENZA_PIENA - 1 or self.rng.random() < 0.9:
            return Msg.R_NR
        return Msg.R_NR2


class Stazione:
    """Una stazione sull'aria: sa comporre i suoi messaggi e sa quando e' il suo turno."""

    def __init__(self, motore, nominativo, wpm, pitch, pan, volume, pesi=PESO_STANDARD):
        self.motore = motore
        self.rng = motore.rng
        self.id = motore.nuovo_id()
        self.mio = nominativo
        self.wpm = int(wpm)
        self.pitch = int(pitch)
        self.pan = float(pan)
        self.volume = float(volume)
        self.l, self.s, self.p = pesi
        self.stato = Stato.ASCOLTA
        self.scadenza = None
        self.messaggi = []
        self.rst = 599
        self.nr = 1
        self.errore_nr = False

    @property
    def suo(self):
        """Il corrispondente della stazione, cioe' io."""
        return self.motore.mio_nominativo

    def testo_numero(self):
        """Rapporto e numero della stazione, con l'errore dello sbadato quando tocca."""
        testo = numero_come_testo(self.rng, self.rst, self.nr, self.errore_nr)
        self.errore_nr = False
        return testo

    def testo_di(self, messaggio):
        testo = TESTI[messaggio]
        while "<#>" in testo:
            testo = testo.replace("<#>", self.testo_numero(), 1)
        return testo.replace("<my>", self.mio).replace("<his>", self.suo)

    def trasmetti(self, messaggi, adesso):
        """Comincia una trasmissione con questi messaggi e restituisce la richiesta di suono."""
        del adesso
        self.messaggi = [m for m in messaggi if m != Msg.NESSUNO]
        if not self.messaggi:
            self.stato = Stato.ASCOLTA
            return None
        self.stato = Stato.TRASMETTE
        self.scadenza = None
        testo = " ".join(self.testo_di(m) for m in self.messaggi)
        # Il volume della richiesta e' gia' filtrato: la forza della stazione
        # attenuata da quanto il suo tono e' lontano dal mio, cioe' il filtro
        # del ricevitore reso voce per voce, come dice il piano.
        return Richiesta(self.id, testo, self.wpm, self.pitch, self.l, self.s, self.p, self.motore.guadagno(self), self.pan, tuple(self.messaggi))

    def tick(self, adesso, finita):
        """Un giro di orologio: chiude la trasmissione finita o fa scattare la scadenza."""
        if self.stato == Stato.TRASMETTE:
            if finita:
                self.stato = Stato.ASCOLTA
                return self.processa(Evento.MESSAGGIO_INVIATO, adesso)
            return None
        if self.scadenza is not None and adesso >= self.scadenza:
            self.scadenza = None
            return self.processa(Evento.SCADENZA, adesso)
        return None

    def processa(self, evento, adesso):
        raise NotImplementedError


class StazioneDX(Stazione):
    """Una stazione che risponde al mio CQ e vuole il QSO, portata da dxstation.py di cwsim."""

    def __init__(self, motore, adesso, singola):
        rng = motore.rng
        nominativo = motore.nominativi()
        oper = Operatore(rng, motore, nominativo, motore.minuti(adesso), singola)
        wpm = oper.velocita(motore.mio_wpm)
        # Il tono a piu' o meno trecento hertz dal mio, come oggi; la panoramica
        # entro l'ampiezza stereo scelta; la forza fra un quinto e il pieno.
        scarto = math.fmod(rng.gauss(0.0, 150.0), 300.0)
        pitch = max(200, min(2000, round(motore.mio_pitch + scarto)))
        pan = rng.uniform(-motore.ampiezza_stereo, motore.ampiezza_stereo)
        volume = 0.2 + 0.8 * (1.0 + math.sin(math.pi * (rng.random() - 0.5))) / 2.0
        super().__init__(motore, nominativo, wpm, pitch, pan, volume, motore.pesi_stazione())
        self.oper = oper
        self.scarto_tono = scarto
        self.chiamato = False
        self.nr = oper.numero()
        if motore.sbadati and rng.random() < motore.prob_rst_sbagliato:
            self.rst = 559 + 10 * rng.randrange(4)
        self.errore_nr = motore.sbadati and rng.random() < motore.prob_nr_sbagliato
        self.stato = Stato.COPIA

    def processa(self, evento, adesso):
        if self.oper.stato == StatoOp.FATTO:
            return None
        if evento == Evento.MESSAGGIO_INVIATO:
            self.scadenza = None if self.motore.io_trasmette else adesso + self.oper.attesa_risposta()
        elif evento == Evento.SCADENZA:
            if self.stato == Stato.ASCOLTA:
                self.oper.ricevuto([Msg.NESSUNO])
                if self.oper.stato == StatoOp.FALLITO:
                    self.stato = Stato.DA_TOGLIERE
                    return None
                self.stato = Stato.PREPARA
            if self.stato == Stato.PREPARA:
                risposte = [self.oper.risposta() for _ in range(self.oper.ripetizioni)]
                self.chiamato = self.chiamato or any(r != Msg.NESSUNO for r in risposte)
                return self.trasmetti(risposte, adesso)
        elif evento == Evento.IO_FINE:
            if self.stato != Stato.TRASMETTE:
                miei = self.motore.io_messaggi
                if self.stato == Stato.COPIA:
                    self.oper.ricevuto(miei)
                elif self.stato in (Stato.ASCOLTA, Stato.PREPARA):
                    if Msg.CQ in miei or Msg.TU in miei or Msg.NIL in miei:
                        self.oper.ricevuto(miei)
                    else:
                        self.oper.ricevuto([Msg.SPAZZATURA])
                if self.oper.stato == StatoOp.FALLITO:
                    self.stato = Stato.DA_TOGLIERE
                    return None
                ritardo = self.oper.ritardo_invio()
                self.scadenza = None if ritardo is None else adesso + ritardo
                self.stato = Stato.PREPARA
        elif evento == Evento.IO_INIZIO:
            if self.stato != Stato.TRASMETTE:
                self.stato = Stato.COPIA
            self.scadenza = None
        return None

    def verita(self):
        """Nominativo, rapporto e numero veri, per il confronto con cio' che ho messo a log."""
        self.stato = Stato.DA_TOGLIERE
        return (self.mio, int(self.rst), int(self.nr))


class StazioneQRM(Stazione):
    """Una stazione che disturba: chiede QRL?, lancia il suo CQ o mi manda a QSY, portata da qrmstation.py."""

    MESSAGGI = (Msg.QRL, Msg.QRL2, Msg.QRL2, Msg.CQ_LUNGO, Msg.CQ_LUNGO, Msg.CQ_LUNGO, Msg.QSY)

    def __init__(self, motore, adesso):
        rng = motore.rng
        pitch = max(200, min(2000, motore.mio_pitch + rng.randint(-300, 300)))
        pan = rng.uniform(-motore.ampiezza_stereo, motore.ampiezza_stereo)
        volume = 0.2 + 0.8 * rng.random()
        super().__init__(motore, motore.nominativi(), rng.randint(30, 50), pitch, pan, volume)
        self.scarto_tono = pitch - motore.mio_pitch
        self.pazienza = rng.randint(1, 5)
        self.prima = rng.choice(self.MESSAGGI)
        self.stato = Stato.PREPARA
        self.scadenza = adesso

    def processa(self, evento, adesso):
        if evento == Evento.MESSAGGIO_INVIATO:
            self.pazienza -= 1
            if self.pazienza > 0:
                self.scadenza = adesso + self.rng.uniform(2.0, 6.0)
            else:
                self.stato = Stato.DA_TOGLIERE
        elif evento == Evento.SCADENZA:
            messaggio = self.prima if self.prima is not None else Msg.CQ_LUNGO
            self.prima = None
            return self.trasmetti([messaggio], adesso)
        return None


@dataclass
class VoceLog:
    """Una riga del log: cio' che ho scritto, cio' che ho mandato, la verita' e la verifica."""

    quando: float
    nominativo: str
    rst_ricevuto: int
    nr_ricevuto: int
    nr_mandato: int
    verifica: str
    prefisso: str


class Punteggio:
    """Il punteggio di Morse Runner, che e' un CQ WPX semplificato.

    Un punto per QSO, un moltiplicatore per ogni prefisso distinto, punteggio
    uguale punti per prefissi. Ogni QSO a log si confronta subito con la
    verita': NIL se il nominativo e' sbagliato, NR se il numero, RST se il
    rapporto. Si tengono i conti grezzi, come li vede il log, e quelli
    verificati.
    """

    def __init__(self):
        self.log = []
        self.prefissi_grezzi = set()
        self.prefissi_verificati = set()
        self.rinunce = []
        self.qso_per_intervallo = {}

    @property
    def punti_grezzi(self):
        return len(self.log)

    @property
    def punti_verificati(self):
        return sum(1 for v in self.log if v.verifica == "")

    @property
    def punteggio_grezzo(self):
        return self.punti_grezzi * len(self.prefissi_grezzi)

    @property
    def punteggio_verificato(self):
        return self.punti_verificati * len(self.prefissi_verificati)

    @property
    def percentuale_errore(self):
        if not self.log:
            return 0.0
        return (1.0 - self.punti_verificati / self.punti_grezzi) * 100.0

    @staticmethod
    def verifica(nominativo, rst, nr, verita):
        if verita is None or nominativo != verita[0]:
            return "NIL"
        if nr != verita[2]:
            return "NR"
        if rst != verita[1]:
            return "RST"
        return ""

    def registra(self, quando, nominativo, rst, nr, nr_mandato, verita):
        """Mette a log un QSO e restituisce la verifica: stringa vuota se e' tutto giusto."""
        nominativo = nominativo.strip().upper()
        esito = self.verifica(nominativo, rst, nr, verita)
        pfx = prefisso(nominativo)
        self.prefissi_grezzi.add(pfx)
        if esito == "":
            self.prefissi_verificati.add(pfx)
        self.log.append(VoceLog(quando, nominativo, rst, nr, nr_mandato, esito, pfx))
        intervallo = int(quando // 300)
        self.qso_per_intervallo[intervallo] = self.qso_per_intervallo.get(intervallo, 0) + 1
        return esito

    def rinuncia(self, nominativo):
        self.rinunce.append(nominativo)

    def nominativi_sbagliati(self):
        return [v.nominativo for v in self.log if v.verifica == "NIL"]

    def scambi_sbagliati(self):
        return [v for v in self.log if v.verifica in ("NR", "RST")]

    def qso_all_ora(self, durata_secondi):
        """Per ogni intervallo di cinque minuti, i QSO fatti riportati all'ora."""
        intervalli = max(1, math.ceil(max(durata_secondi, 1.0) / 300.0))
        return [(i * 5, i * 5 + 4, self.qso_per_intervallo.get(i, 0) * 12) for i in range(intervalli)]


class Contest:
    """Il pile-up: le stazioni nascono, chiamano, aspettano, perdono la pazienza e se ne vanno.

    Parametri:
      mio_nominativo, mio_wpm, mio_pitch: come trasmetto io.
      nominativi: una funzione senza argomenti che da' un nominativo, veri e inventati con le percentuali di cwapu.
      pileup: falso e' il modo singolo, una stazione alla volta; vero e' il pile-up.
      attivita: quante stazioni rispondono in media a ogni chiamata, il doppio della media di Poisson come in cwsim.
      sbadati: gli operatori che sbagliano rapporto e numero e chiamano fuori turno.
      qrm, qrm_massime: le stazioni che disturbano, e quante al massimo insieme.
      ampiezza_stereo: da 0 a 100, quanto le stazioni si allargano fra gli altoparlanti.
      banda: la larghezza del filtro del ricevitore in hertz, che attenua i toni lontani dal mio.
      pesi_sporchi: (probabilita', intervallo l, intervallo s, intervallo p) del manipolo sporco, dalle impostazioni.
      seme: per le prove, un generatore casuale ripetibile.
    """

    def __init__(
        self,
        mio_nominativo,
        mio_wpm,
        mio_pitch,
        nominativi,
        *,
        pileup=False,
        attivita=4,
        sbadati=True,
        qrm=False,
        qrm_massime=1,
        ampiezza_stereo=100,
        banda=500,
        pesi_sporchi=(0.3, (30, 60), (25, 75), (15, 50)),
        seme=None,
    ):
        self.rng = random.Random(seme)
        self.mio_nominativo = mio_nominativo.strip().upper()
        self.mio_wpm = int(mio_wpm)
        self.mio_pitch = int(mio_pitch)
        self.nominativi = nominativi
        self.pileup = bool(pileup)
        self.attivita = max(1, int(attivita))
        self.sbadati = bool(sbadati)
        self.qrm = bool(qrm)
        self.qrm_massime = max(1, int(qrm_massime))
        self.ampiezza_stereo = max(0.0, min(PAN_MASSIMO, float(ampiezza_stereo)))
        self.banda = int(banda)
        self.pesi_sporchi = pesi_sporchi
        self.prob_rst_sbagliato = 0.03
        self.prob_nr_sbagliato = 0.1
        self.stazioni = []
        self.punteggio = Punteggio()
        self.mio_nr = 1
        self.suo_nominativo = ""
        self.io_messaggi = []
        self.io_trasmette = False
        self.inizio = None
        self.ultimo_tick = None
        self.verita_pendenti = []
        self.in_attesa = None
        self.attesa_annullata = False
        self.eventi_rimandati = []
        self._contatore = 0

    def nuovo_id(self):
        self._contatore += 1
        return f"s{self._contatore}"

    def minuti(self, adesso):
        if self.inizio is None:
            return 0.0
        return max(0.0, (adesso - self.inizio) / 60.0)

    def pesi_stazione(self):
        """I pesi di una stazione: standard, oppure sporchi con la probabilita' e gli intervalli delle impostazioni."""
        probabilita, (l0, l1), (s0, s1), (p0, p1) = self.pesi_sporchi
        if self.rng.random() < probabilita / (100.0 if probabilita > 1 else 1.0):
            return (self.rng.randint(l0, l1), self.rng.randint(s0, s1), self.rng.randint(p0, p1))
        return PESO_STANDARD

    def guadagno(self, stazione):
        """Il volume con cui la stazione arriva: la sua forza per il filtro di banda."""
        return stazione.volume * guadagno_filtro(self.banda, getattr(stazione, "scarto_tono", 0.0))

    def dx_attive(self):
        return [s for s in self.stazioni if isinstance(s, StazioneDX) and s.oper.stato != StatoOp.FATTO]

    def qrm_attive(self):
        return [s for s in self.stazioni if isinstance(s, StazioneQRM)]

    def testo_mio(self, messaggi):
        """Il testo che trasmetto io per questi messaggi."""
        pezzi = []
        for m in messaggi:
            testo = TESTI[m]
            testo = testo.replace("<#>", numero_come_testo(self.rng, 599, self.mio_nr))
            testo = testo.replace("<my>", self.mio_nominativo).replace("<his>", self.suo_nominativo)
            pezzi.append(testo)
        return " ".join(pezzi)

    def io_trasmetti(self, messaggi, adesso, suo_nominativo=None, testo=None):
        """Comincio a trasmettere: le stazioni smettono di aspettare e si mettono a copiare."""
        if self.inizio is None:
            self.inizio = adesso
        if suo_nominativo is not None:
            self.suo_nominativo = suo_nominativo.strip().upper()
        self.io_messaggi = list(messaggi)
        self.io_trasmette = True
        if Msg.TU in self.io_messaggi:
            self.attesa_annullata = False
        for s in self.stazioni:
            s.processa(Evento.IO_INIZIO, adesso)
        return Richiesta(IO, testo if testo is not None else self.testo_mio(self.io_messaggi), self.mio_wpm, self.mio_pitch, *PESO_STANDARD, 1.0, 0.0, tuple(self.io_messaggi))

    def io_finito(self, adesso):
        """Ho finito di trasmettere: nel pile-up nascono le stazioni nuove, e tutte decidono cosa fare.

        Dopo un Esc la trasmissione e' gia' chiusa, e chi mi usa puo' dirmi
        lo stesso che e' finita: la seconda volta non conta, altrimenti le
        stazioni perderebbero due punti di pazienza per una chiamata sola.
        """
        if not self.io_trasmette:
            return
        self.io_trasmette = False
        if self.pileup and (Msg.CQ in self.io_messaggi or (Msg.TU in self.io_messaggi and Msg.MIO in self.io_messaggi)):
            for _ in range(poisson(self.rng, 0.5 * self.attivita)):
                self.stazioni.append(StazioneDX(self, adesso, singola=False))
        for s in list(self.stazioni):
            s.processa(Evento.IO_FINE, adesso)

    def annulla_trasmissione(self, adesso):
        """Esc mentre trasmetto: le stazioni hanno sentito spazzatura.

        Il QSO gia' messo a log resta in sospeso: la stazione non ha sentito
        il mio TU e non dira' la sua verita', quindi chiuderlo adesso lo
        marcherebbe NIL per colpa dell'interruzione. Lo chiude il TU
        rimandato, o la fine del contest.
        """
        self.io_messaggi = [Msg.SPAZZATURA]
        if self.in_attesa is not None:
            self.attesa_annullata = True
        self.io_finito(adesso)

    def prendi_verita(self, nominativo):
        """La verita' della stazione che ho messo a log, o la piu' vecchia se nessuna corrisponde.

        Due stazioni possono finire nello stesso giro: prendendo l'ultima
        arrivata, un QSO giusto diventerebbe NIL per colpa dell'altra. Si
        cerca prima quella che torna con il nominativo a log; se nessuna
        torna, il NIL e' meritato.
        """
        for i, verita in enumerate(self.verita_pendenti):
            if verita[0] == nominativo:
                return self.verita_pendenti.pop(i)
        return self.verita_pendenti.pop(0) if self.verita_pendenti else None

    def chiudi_attesa(self):
        """Porta a log il QSO in sospeso e restituisce l'evento da riferire."""
        quando, nominativo, rst, nr, nr_mandato = self.in_attesa
        self.in_attesa = None
        self.attesa_annullata = False
        verita = self.prendi_verita(nominativo)
        self.verita_pendenti.clear()
        verifica = self.punteggio.registra(quando, nominativo, rst, nr, nr_mandato, verita)
        return ("log", self.punteggio.log[-1], verifica)

    def chiudi_contest(self):
        """Fine del contest: il QSO eventualmente in sospeso va a log com'e'."""
        return [self.chiudi_attesa()] if self.in_attesa is not None else []

    def avanza(self, adesso, finite=()):
        """Un giro di orologio: scadenze, trasmissioni finite, nascite e rinunce."""
        if self.inizio is None:
            self.inizio = adesso
        finite = set(finite)
        esito = Esito()
        if self.eventi_rimandati:
            esito.eventi.extend(self.eventi_rimandati)
            self.eventi_rimandati.clear()
        if IO in finite:
            self.io_finito(adesso)
        for s in list(self.stazioni):
            richiesta = s.tick(adesso, s.id in finite)
            if richiesta is not None:
                esito.richieste.append(richiesta)
        for s in list(self.stazioni):
            if s.stato == Stato.DA_TOGLIERE:
                if isinstance(s, StazioneDX) and s.oper.stato != StatoOp.FATTO and s.chiamato:
                    self.punteggio.rinuncia(s.mio)
                    esito.eventi.append(("rinuncia", s.mio))
                self.stazioni.remove(s)
        for s in list(self.stazioni):
            if isinstance(s, StazioneDX) and s.oper.stato == StatoOp.FATTO:
                verita = s.verita()
                self.verita_pendenti.append(verita)
                esito.eventi.append(("qso", verita))
                self.stazioni.remove(s)
        if self.in_attesa is not None and not self.io_trasmette and not self.attesa_annullata:
            # Il QSO messo a log con l'Invio si chiude quando la mia trasmissione
            # di TU e' finita e la stazione ha detto la sua verita', o non l'ha
            # detta: cosi' la verifica e' una sola e non dipende da chi arriva
            # prima, come invece in cwsim, che aggiornava la riga a posteriori.
            esito.eventi.append(self.chiudi_attesa())
        if not self.pileup and not self.dx_attive():
            nuova = StazioneDX(self, adesso, singola=True)
            self.stazioni.append(nuova)
            esito.eventi.append(("nasce", nuova.mio))
            if not self.io_trasmette:
                nuova.processa(Evento.IO_FINE, adesso)
            # Se nasce mentre trasmetto e' gia' in COPIA: sente la mia chiamata
            # dal mezzo e risponde quando ho finito, non sopra di me.
        if self.qrm and self.ultimo_tick is not None:
            dt = max(0.0, adesso - self.ultimo_tick)
            if len(self.qrm_attive()) < self.qrm_massime and self.rng.random() < dt / INTERVALLO_QRM:
                self.stazioni.append(StazioneQRM(self, adesso))
        self.ultimo_tick = adesso
        return esito

    def registra_qso(self, adesso, nominativo, nr, rst=599):
        """Metto a log il QSO con cio' che ho copiato, insieme al TU.

        La verifica arriva con l'evento "log" del primo avanza() dopo la fine
        del mio TU, quando la stazione ha detto la sua verita': vuota se e'
        tutto giusto, NIL, NR o RST altrimenti, come la colonna Chk di cwsim.
        Il mio progressivo avanza subito, perche' il prossimo QSO e' un altro.
        Se il TU era stato interrotto con Esc e lo rimando, la riga resta
        quella di prima, con il suo istante e il suo progressivo.
        """
        nominativo = nominativo.strip().upper()
        if self.in_attesa is not None and self.in_attesa[1] == nominativo:
            quando, _, _, _, nr_mandato = self.in_attesa
        else:
            if self.in_attesa is not None:
                self.eventi_rimandati.append(self.chiudi_attesa())
            quando = adesso - (adesso if self.inizio is None else self.inizio)
            nr_mandato = self.mio_nr
            self.mio_nr += 1
        self.in_attesa = (quando, nominativo, int(rst), int(nr), nr_mandato)
        self.attesa_annullata = False
