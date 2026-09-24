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
# Le bande dell'evanescenza, da Morse Runner: l'inverso del tempo di
# correlazione, in hertz. Il QSB delle propagazioni normali e' lento, il
# flutter di quelle polari e' rapido, e tocca a tre stazioni su dieci fra
# quelle che hanno gia' il QSB.
QSB_BANDA = (0.03, 0.6)
FLUTTER_BANDA = (3.0, 33.0)
PROB_FLUTTER = 0.3
# Lo scarto del tono di una stazione dal mio. cwsim usa una gaussiana di
# centocinquanta ripiegata a trecento, e con il filtro a cinquecento le
# stazioni restavano tutte dentro la banda passante: Gabriele, provandolo,
# le ha sentite tutte piuttosto centrate, mentre in radio si chiama anche da
# molto fuori banda. Morse Runner sparge le stazioni con una gaussiana di
# centocinquanta hertz ripiegata a trecento, quindi nemmeno li' esiste una
# stazione piu' lontana di trecento hertz: con il filtro a seicento non ce
# n'e' una sola attenuata di piu' di 5,6 decibel. Gabriele, che con la banda
# larga si aspetta di trovarne ovunque, ha scelto di staccarsi dall'originale
# e allargare: settecento hertz di ripiegamento coprono tutta la banda piu'
# larga. Il filtro se le mangia, che e' poi il suo mestiere, ma senza mai
# mangiarsele del tutto: sotto c'e' il pavimento, e una stazione lontana si
# sente debole, non sparisce.
TONO_SCARTO = 300.0
TONO_MASSIMO = 700.0
# I toni che una stazione puo' avere. Il tetto e' quello che CWzator accetta,
# perche' oltre rifiuta il messaggio e lo dice. Il pavimento no: e' piu' alto
# del suo, perche' sotto i duecentocinquanta hertz la nota e' cupa e si copia
# male, e con il tono proprio basso le stazioni ci finivano dentro.
TONO_STAZIONE = (250, 2800)
# Quanto il filtro lascia passare fuori dalla sua banda. Non e' zero: nessun
# filtro ha reiezione infinita, e soprattutto una stazione muta chiamerebbe,
# aspetterebbe e rinuncerebbe senza che nessuno possa sentirla, finendo fra
# le rinunce del rapporto come un'occasione persa che non c'e' mai stata. A
# meno ventiquattro decibel si sente che c'e' traffico e non si copia niente,
# che e' poi cio' che fa un filtro stretto.
FILTRO_PAVIMENTO = 0.06
# La nota ruvida: una modulazione cosi' rapida da non sentirsi piu' come
# un andirivieni ma come sporcizia sulla nota. Non sta in Morse Runner: la
# chiede Gabriele, che in radio di difetti ne sente molti di piu' di uno. Il
# tetto e' cento perche' e' quanto il motore CW accetta: chiedendo di piu'
# rifiutava il messaggio, e quelle stazioni non suonavano affatto.
RUVIDO_BANDA = (40.0, 100.0)
PROB_RUVIDO = 0.1
# I due difetti di nota che il motore CW sa fare dalla V167: il tono che
# scivola dentro l'elemento, cioe' il trasmettitore con l'alimentazione
# debole, e il tono che oscilla. Vanno con il flutter, che e'
# l'interruttore dei difetti del segnale, e sono indipendenti fra loro e
# dall'evanescenza: in radio una stazione puo' avere tutto insieme.
CHIRP_SCARTO = (10.0, 40.0)
PROB_CHIRP = 0.15
VIBRATO_PROFONDITA = (3.0, 12.0)
VIBRATO_FREQUENZA = (2.0, 9.0)
PROB_VIBRATO = 0.1
# Il segno con cui si marca, dentro il testo, il pezzo da mandare piu'
# accelerato. Non e' un carattere che il motore CW sappia suonare: serve solo a
# dire dove tagliare, e dal testo della richiesta sparisce sempre.
MARCA_VELOCE = "\x00"
# Quanti caratteri del gruppo dello scambio sono il rapporto: 599 diventa
# 5NN, e restano tre anche con le abbreviazioni.
LUNGHEZZA_RAPPORTO = 3
# Come chiudo io un QSO: la prima e' la piu' frequente, le altre arrivano
# ogni tanto. In radio non si chiude sempre con TU, e sentire sempre la
# stessa parola non allena l'orecchio a niente. Le stazioni capiscono la
# chiusura dal messaggio, non dal testo, quindi per il motore sono tutte
# la stessa cosa.
CHIUSURE = ("TU", "R TU", "TU 73", "TU GL", "73", "GL")
PROB_CHIUSURA_TU = 0.6
# Come saluta una stazione dopo il mio TU, quando saluta: una su cinque,
# scelta di Gabriele. Le altre chiudono e spariscono, come si fa in un
# contest affollato.
SALUTI = ("TU", "73", "GL", "R", "EE", "TU 73", "GL 73", "R TU")
PROB_SALUTO = 0.2
# Quanto aspetta a salutare, in secondi: nessuno risponde nello stesso
# istante in cui l'altro ha smesso.
RITARDO_SALUTO = (0.15, 0.5)
# Il tetto del pile-up, issue 17: quante stazioni al massimo chiamano
# insieme. Il mixer di GBUtils ha trentadue voci, e quando e' pieno chiude la
# piu' vecchia, che nel contest e' quasi sempre il fruscio: ventiquattro
# stazioni, cinque di QRM, il QRN, la mia trasmissione e un saluto fanno
# trentadue.
PILEUP_MASSIME = 24
# La propagazione, issue 16, da 0 a 100: a 50 il contest e' quello di Morse
# Runner. Le curve sono quelle decise da Gabriele il 24 settembre 2026, di
# partenza: si ritoccano al collaudo d'ascolto.
PROPAGAZIONE_NEUTRA = 50
# La frazione del tetto che risponde in media a un CQ, a 0 e a 100: a 50 e'
# la meta', cioe' la media di Poisson di cwsim con l'attivita' al posto del
# tetto.
RISPOSTA_CQ = (0.15, 0.85)
# Sopra 50 le stazioni arrivano anche da sole e riempiono i posti liberi:
# questa e' la costante di tempo a 100, in secondi, e raddoppia a 75.
RIEMPIMENTO_SPONTANEI = 5.0
# Chi arriva da solo a frequenza libera aspetta un poco prima di chiamare.
ATTESA_SPONTANEI = (0.3, 1.5)
# Il volume minimo con cui nasce una stazione a 0, a 50 e a 100: il massimo
# resta uno, e a 50 e' la forza di oggi.
VOLUME_MINIMO = (0.1, 0.2, 0.5)
# La profondita' del QSB lento a 100, in percento: da 50 in giu' e' piena.
# CWzator la accetta dalla V169 di GBUtils, issue 44; senza, chi suona la
# richiesta la lascia cadere e cambia soltanto la banda.
QSB_PROFONDITA_PIENA = 40.0


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
    # La banda dell'evanescenza di questa stazione, None se non ne ha.
    qsb: float = None
    # I due difetti di nota, None se la stazione non ne ha.
    chirp: float = None
    vibrato: tuple = None
    # Vero se chi trasmette e' una stazione che posso lavorare. Serve a chi
    # tiene le statistiche: la velocita' del QSO e' la sua, non quella di
    # una stazione di disturbo, che nasce fra trenta e cinquanta parole al
    # minuto a prescindere dalla mia.
    dx: bool = False
    # Il messaggio diviso in pezzi, ognuno con la sua velocita', quando una
    # parte va mandata piu' svelta del resto: e' il 5NN dei contest, che
    # tutti si aspettano e quindi molti accelerano. None vuol dire tutto il
    # testo alla velocita' della richiesta, che e' il caso normale.
    pezzi: tuple = None
    # I secondi di silenzio prima che il messaggio cominci. Zero per tutto,
    # tranne il saluto di una stazione dopo il mio TU.
    ritardo: float = 0.0
    # Quanto scende l'evanescenza lenta, in percento; None e' la profondita'
    # piena di sempre. La cambia la propagazione sopra 50.
    qsb_profondita: float = None


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
    stazione: una campana che comincia a scendere subito e arriva al
    pavimento a una banda intera dal centro.

    Subito, non dopo meta' banda. Prima il guadagno restava pieno fino a
    meta' banda, e due stazioni, una centrata e una a duecentocinquanta
    hertz, arrivavano con lo stesso identico volume: spariva l'unico
    segnale che dice all'orecchio quanto una stazione e' fuori, e il
    pile-up sembrava tutto ammassato al centro. Il filtro di cwsim, tre
    medie mobili in cascata, a meta' banda e' gia' sceso di 5,6 decibel:
    questa campana lo insegue da vicino, misurata a banda 600, prima il
    nostro poi il suo: a 100 hertz -0,6 contro -0,6; a 200 -2,3 contro
    -2,4; a 300 -5,5 contro -5,6; a 400 -10,6 contro -10,3.
    """
    banda = max(1.0, float(banda_hz))
    fuori = abs(float(scarto_hz)) / banda
    if fuori >= 1.0:
        return FILTRO_PAVIMENTO
    fianco = 0.5 * (1.0 + math.cos(math.pi * fuori))
    return FILTRO_PAVIMENTO + (1.0 - FILTRO_PAVIMENTO) * fianco


def tono_stazione(mio, scarto):
    """Il tono di una stazione: il mio piu' lo scarto, ribaltato se esce dai limiti.

    Con il tono proprio vicino a un estremo, sommare lo scarto porterebbe fuori
    da cio' che il motore CW accetta: tagliare ammucchierebbe tutte le stazioni
    sul limite, cioe' lontanissime dal mio tono e quindi mute sotto il filtro.
    Ribaltando lo scarto la distanza resta quella, dall'altra parte.
    """
    basso, alto = TONO_STAZIONE
    tono = round(mio + scarto)
    if not (basso <= tono <= alto):
        tono = round(mio - scarto)
    return max(basso, min(alto, tono))


def dividi_in_pezzi(marcato, wpm, incremento):
    """Il testo marcato diventa pezzi con la loro velocita', o None se non serve.

    I pezzi si alternano: fuori dai segni la velocita' di base, dentro
    quella accelerata. Due pezzi di fila alla stessa velocita' si uniscono,
    perche' ogni pezzo costa una voce del mixer e le voci sono trentadue.
    Ogni pezzo dice anche se il confine che lo precede era uno spazio: fra
    due gruppi il silenzio e' piu' lungo che fra due lettere, e chi rimette
    insieme il suono, sbagliandolo, farebbe sentire uno strappo in mezzo
    allo scambio.
    """
    if MARCA_VELOCE not in marcato:
        return None
    veloce = max(1, round(int(wpm) * (1.0 + float(incremento) / 100.0)))
    parti = marcato.split(MARCA_VELOCE)
    pezzi = []
    for indice, parte in enumerate(parti):
        if not parte.strip():
            continue
        velocita = veloce if indice % 2 else int(wpm)
        # Il confine che conta e' quello che precede il pezzo: lo spazio sta
        # in coda alla parte prima o in testa a questa. Il 5NN attaccato a
        # una R sarebbe una parola sola.
        prima = parti[indice - 1] if indice else ""
        parola = prima.endswith(" ") or parte.startswith(" ")
        if pezzi and pezzi[-1][1] == velocita:
            unito = pezzi.pop()
            pezzi.append((unito[0] + (" " if parola else "") + parte.strip(), velocita, unito[2]))
            continue
        pezzi.append((parte.strip(), velocita, parola))
    return tuple(pezzi) if len(pezzi) > 1 else None


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
        # La banda dell'evanescenza e i due difetti di nota: le figlie li
        # prendono dal motore, che sa quali interruttori sono accesi. Qui
        # restano vuoti, cosi' una stazione costruita a mano nelle prove
        # suona pulita.
        self.qsb = None
        self.qsb_profondita = None
        self.chirp = None
        self.vibrato = None
        # Le stazioni di disturbo e quelle costruite a mano nelle prove non
        # accelerano: il 5NN accelerato e' un gesto di chi sta facendo un QSO.
        self.scambio_veloce = False

    @property
    def scarto_tono(self):
        """Quanto il tono di questa stazione dista dal mio, adesso.

        Si ricalcola invece di restare quello della nascita: spostando il mio
        tono con Alt e le frecce, il filtro deve trattare le stazioni gia' in
        aria come tratterebbe una che nascesse adesso. Prima no, e cercare
        con la sintonia una stazione che non si sentiva era un gesto che non
        serviva a niente.
        """
        return self.pitch - self.motore.mio_pitch

    @property
    def suo(self):
        """Il corrispondente della stazione, cioe' io."""
        return self.motore.mio_nominativo

    def testo_numero(self, marca=False):
        """Rapporto e numero della stazione, con l'errore dello sbadato quando tocca.

        Con marca, il rapporto esce fra due segni: chi costruisce la richiesta
        sa dove tagliare per mandarlo accelerato. La marcatura viene dopo
        l'errore dello sbadato, cosi' la correzione con la serie di e resta
        alla velocita' di sempre.
        """
        testo = numero_come_testo(self.rng, self.rst, self.nr, self.errore_nr)
        self.errore_nr = False
        if marca and len(testo) > LUNGHEZZA_RAPPORTO:
            testo = MARCA_VELOCE + testo[:LUNGHEZZA_RAPPORTO] + MARCA_VELOCE + testo[LUNGHEZZA_RAPPORTO:]
        return testo

    def testo_di(self, messaggio, marca=False):
        testo = TESTI[messaggio]
        while "<#>" in testo:
            testo = testo.replace("<#>", self.testo_numero(marca), 1)
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
        marcato = " ".join(self.testo_di(m, self.scambio_veloce) for m in self.messaggi)
        testo = marcato.replace(MARCA_VELOCE, "")
        pezzi = self.dividi_in_pezzi(marcato)
        # Il volume della richiesta e' gia' filtrato: la forza della stazione
        # attenuata da quanto il suo tono e' lontano dal mio, cioe' il filtro
        # del ricevitore reso voce per voce, come dice il piano.
        return Richiesta(
            self.id,
            testo,
            self.wpm,
            self.pitch,
            self.l,
            self.s,
            self.p,
            self.motore.guadagno(self),
            self.pan,
            tuple(self.messaggi),
            self.qsb,
            self.chirp,
            self.vibrato,
            isinstance(self, StazioneDX),
            pezzi,
            qsb_profondita=self.qsb_profondita,
        )

    def dividi_in_pezzi(self, marcato):
        """I pezzi di questa stazione, alla sua velocita'."""
        return dividi_in_pezzi(marcato, self.wpm, self.motore.scambio_incremento)

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
        # Si centra sulla velocita' che sente, cioe' la mia effettiva: con i
        # miei pesi larghi i miei 25 nominali possono suonare come 16.
        wpm = oper.velocita(motore.mio_rwpm)
        # Il tono a piu' o meno trecento hertz dal mio, come oggi; la panoramica
        # entro l'ampiezza stereo scelta; la forza fra il minimo che da' la
        # propagazione e il pieno, un quinto a 50.
        scarto = math.fmod(rng.gauss(0.0, TONO_SCARTO), TONO_MASSIMO)
        pitch = tono_stazione(motore.mio_pitch, scarto)
        pan = rng.uniform(-motore.ampiezza_stereo, motore.ampiezza_stereo)
        volume = motore.forza_di_nascita((1.0 + math.sin(math.pi * (rng.random() - 0.5))) / 2.0)
        super().__init__(motore, nominativo, wpm, pitch, pan, volume, motore.pesi_stazione())
        self.oper = oper
        self.qsb = motore.evanescenza()
        self.qsb_profondita = motore.profondita_evanescenza(self.qsb)
        self.chirp, self.vibrato = motore.difetti_di_nota()
        # Chi accelera il rapporto lo fa per tutto il QSO: e' un'abitudine
        # dell'operatore, non un capriccio del momento.
        self.scambio_veloce = rng.random() * 100.0 < motore.scambio_probabilita
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

    def saluto(self, ritardo):
        """Il suo saluto dopo il mio TU, con la sua voce, la sua nota e il suo posto.

        Non cambia niente nel QSO, che e' gia' chiuso: e' una richiesta di
        suono e basta. In pile-up puo' sovrapporsi alle nuove chiamate, come
        in radio. Non porta la velocita' del QSO, che e' gia' stata presa.
        """
        return Richiesta(
            self.id,
            self.rng.choice(SALUTI),
            self.wpm,
            self.pitch,
            self.l,
            self.s,
            self.p,
            self.motore.guadagno(self),
            self.pan,
            (),
            self.qsb,
            self.chirp,
            self.vibrato,
            False,
            None,
            float(ritardo),
            self.qsb_profondita,
        )

    def verita(self):
        """Nominativo, rapporto e numero veri, per il confronto con cio' che ho messo a log."""
        self.stato = Stato.DA_TOGLIERE
        return (self.mio, int(self.rst), int(self.nr))


class StazioneQRM(Stazione):
    """Una stazione che disturba: chiede QRL?, lancia il suo CQ o mi manda a QSY, portata da qrmstation.py."""

    MESSAGGI = (Msg.QRL, Msg.QRL2, Msg.QRL2, Msg.CQ_LUNGO, Msg.CQ_LUNGO, Msg.CQ_LUNGO, Msg.QSY)

    def __init__(self, motore, adesso):
        rng = motore.rng
        pitch = tono_stazione(motore.mio_pitch, rng.randint(-int(TONO_MASSIMO), int(TONO_MASSIMO)))
        pan = rng.uniform(-motore.ampiezza_stereo, motore.ampiezza_stereo)
        volume = motore.forza_di_nascita(rng.random())
        super().__init__(motore, motore.nominativi(), rng.randint(30, 50), pitch, pan, volume)
        self.qsb = motore.evanescenza()
        self.qsb_profondita = motore.profondita_evanescenza(self.qsb)
        self.chirp, self.vibrato = motore.difetti_di_nota()
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
        """Per ogni intervallo di cinque minuti, i QSO fatti riportati all'ora.

        L'ultimo intervallo quasi mai dura cinque minuti: moltiplicarlo per
        dodici come gli altri faceva sembrare lentissima ogni sessione corta,
        che e' proprio quella a numero di QSO. Otto QSO in due minuti sono
        duecentoquaranta all'ora, non novantasei. Una coda piu' breve di un
        minuto non si riporta affatto, perche' due QSO in dieci secondi
        darebbero settecentoventi all'ora, un numero che non descrive niente.
        """
        durata = max(float(durata_secondi), 1.0)
        intervalli = max(1, math.ceil(durata / 300.0))
        righe = []
        for i in range(intervalli):
            secondi = min(300.0, durata - i * 300.0)
            if secondi <= 0.0 or (secondi < 60.0 and righe):
                continue
            quanti = self.qso_per_intervallo.get(i, 0)
            righe.append((i * 5, i * 5 + 4, round(quanti * 3600.0 / secondi)))
        return righe


class Contest:
    """Il pile-up: le stazioni nascono, chiamano, aspettano, perdono la pazienza e se ne vanno.

    Parametri:
      mio_nominativo, mio_wpm, mio_pitch: come trasmetto io.
      mio_rwpm: la mia velocita' effettiva prima della mia prima trasmissione, cioe' la stima con i miei pesi; poi chi usa il motore la rimisura a ogni mio messaggio con imposta_mia_velocita. Le stazioni si centrano su questa. None vale mio_wpm, cioe' pesi standard.
      nominativi: una funzione senza argomenti che da' un nominativo, veri e inventati con le percentuali di cwapu.
      pileup: falso e' il modo singolo, una stazione alla volta; vero e' il pile-up.
      pileup_massime: quante stazioni al massimo chiamano insieme nel pile-up, da 1 a PILEUP_MASSIME, issue 17.
      propagazione: da 0 a 100, issue 16. A 50 il contest e' quello di Morse Runner. Nel pile-up cambia quante stazioni rispondono al CQ e, sopra 50, fa arrivare stazioni anche senza CQ; in tutti e due i modi cambia la forza delle stazioni e il QSB; nel pile-up anche quanto spesso arriva il QRM.
      sbadati: gli operatori che sbagliano rapporto e numero e chiamano fuori turno.
      qrm, qrm_massime: le stazioni che disturbano, e quante al massimo insieme.
      qsb: l'evanescenza, cioe' il segnale che va e viene; flutter: la sua forma rapida, che tocca tre stazioni su dieci fra quelle che hanno gia' il QSB.
      ampiezza_stereo: da 0 a 100, quanto le stazioni si allargano fra gli altoparlanti.
      banda: la larghezza del filtro del ricevitore in hertz, che attenua i toni lontani dal mio.
      pesi_manuali: (probabilita', intervallo l, intervallo s, intervallo p) di chi manipola a mano con il tasto verticale, dalle impostazioni.
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
        pileup_massime=4,
        propagazione=PROPAGAZIONE_NEUTRA,
        sbadati=True,
        qrm=False,
        qrm_massime=1,
        qsb=False,
        flutter=False,
        ampiezza_stereo=100,
        banda=500,
        pesi_manuali=(0.3, (30, 60), (25, 75), (15, 50)),
        scambio_probabilita=0,
        scambio_incremento=15,
        mio_pesi=PESO_STANDARD,
        mio_rwpm=None,
        seme=None,
    ):
        self.rng = random.Random(seme)
        self.mio_nominativo = mio_nominativo.strip().upper()
        self.rapporto_effettivo = 1.0
        self.imposta_mia_velocita(mio_wpm, mio_rwpm)
        self.mio_pitch = int(mio_pitch)
        self.nominativi = nominativi
        self.pileup = bool(pileup)
        self.pileup_massime = max(1, min(PILEUP_MASSIME, int(pileup_massime)))
        self.propagazione = max(0.0, min(100.0, float(propagazione)))
        self.sbadati = bool(sbadati)
        self.qrm = bool(qrm)
        self.qrm_massime = max(1, int(qrm_massime))
        self.qsb = bool(qsb)
        self.flutter = bool(flutter)
        self.ampiezza_stereo = max(0.0, min(PAN_MASSIMO, float(ampiezza_stereo)))
        self.banda = int(banda)
        # Quante stazioni su cento accelerano il rapporto, e di quanto per
        # cento accelerano rispetto alla propria velocita'. A zero nessuna lo
        # fa, ed e' come se la cosa non esistesse.
        self.scambio_probabilita = float(scambio_probabilita)
        self.scambio_incremento = float(scambio_incremento)
        self.pesi_manuali = pesi_manuali
        # I pesi della mia manipolazione, cioe' quelli della sezione k: la mia
        # stazione manda come mando io in tutto il resto dell'applicazione.
        # Nel contest solo il Farnsworth resta fuori.
        self.mio_pesi = tuple(mio_pesi)
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

    def imposta_mia_velocita(self, wpm, effettiva=None):
        """La mia velocita': quella nominale, con cui trasmetto, e quella che si sente.

        Le due coincidono con i pesi standard. Con pesi diversi il motore CW
        trasmette alla nominale con i miei pesi, e quello che esce ha la
        velocita' effettiva: e' su questa che le stazioni si regolano, perche'
        in radio si risponde alla velocita' che si sente. Prima si
        regolavano sulla nominale, e con linee a 60 e spazi a 75 i miei 25 wpm
        suonavano come 16 mentre le stazioni rispondevano a 25 veri.
        L'effettiva si tiene come proporzione della nominale: passandola, la
        si rimisura; senza, cambiando la nominale l'effettiva la segue nella
        stessa proporzione, perche' con gli stessi pesi le durate scalano
        insieme alla velocita'.
        """
        self.mio_wpm = int(wpm)
        if effettiva:
            self.rapporto_effettivo = float(effettiva) / self.mio_wpm

    @property
    def mio_rwpm(self):
        """La mia velocita' effettiva, quella su cui le stazioni si regolano."""
        return self.mio_wpm * self.rapporto_effettivo

    def minuti(self, adesso):
        if self.inizio is None:
            return 0.0
        return max(0.0, (adesso - self.inizio) / 60.0)

    def evanescenza(self):
        """La banda dell'evanescenza di una stazione che nasce adesso, o None.

        Con il QSB acceso ogni stazione ne prende una; con il flutter acceso,
        tre su dieci fra quelle si prendono il tremolio polare di Morse Runner
        e una su dieci la nota ruvida, che Morse Runner non ha.
        """
        if not self.qsb:
            return None
        if self.flutter:
            # Con il flutter acceso, tre stazioni su dieci hanno il tremolio
            # polare e una su dieci la nota ruvida: sono i difetti del segnale,
            # e stanno insieme sotto lo stesso interruttore.
            sorte = self.rng.random()
            if sorte < PROB_FLUTTER:
                return self.rng.uniform(*FLUTTER_BANDA)
            if sorte < PROB_FLUTTER + PROB_RUVIDO:
                return self.rng.uniform(*RUVIDO_BANDA)
        # L'estrazione e' logaritmica, non uniforme. La banda e' l'inverso del
        # tempo: fra tre centesimi e sei decimi di hertz i tempi vanno da dodici
        # secondi a sei decimi, e prendendo a caso in modo uniforme le onde
        # lente non uscirebbero quasi mai, perche' occupano un angolo
        # dell'intervallo. Cosi' meta' delle stazioni sta sotto tredici
        # centesimi, cioe' con un'onda che impiega tre secondi buoni a scendere
        # e altrettanti a risalire, che e' il QSB che si sente davvero.
        # La propagazione sposta tutta la banda: sotto 50 i cali sono piu'
        # lenti e lunghi, fino a meta' a 0; sopra 50 piu' rapidi e brevi, fino
        # al doppio a 100.
        basso, alto = (b * self.fattore_banda_qsb() for b in QSB_BANDA)
        return math.exp(self.rng.uniform(math.log(basso), math.log(alto)))

    @property
    def aperta(self):
        """La propagazione da 0 a 1, cioe' quanto la banda e' aperta."""
        return self.propagazione / 100.0

    def fattore_banda_qsb(self):
        """Per quanto si moltiplica la banda del QSB lento: 0,5 a 0, 1 a 50, 2 a 100."""
        f = self.aperta
        return 0.5 + f if f <= 0.5 else 1.0 + 2.0 * (f - 0.5)

    def profondita_evanescenza(self, banda):
        """Quanto scende l'evanescenza di questa banda, in percento, o None se scende fino in fondo.

        Tocca solo il QSB lento: il flutter e la nota ruvida sono difetti del
        segnale, non della propagazione, e restano come sono. Da 50 in giu'
        la profondita' e' piena, come in Morse Runner; sopra scende fino a
        QSB_PROFONDITA_PIENA a 100, cioe' segnali forti con cali leggeri.
        """
        f = self.aperta
        if banda is None or banda >= FLUTTER_BANDA[0] or f <= 0.5:
            return None
        return 100.0 - (100.0 - QSB_PROFONDITA_PIENA) * 2.0 * (f - 0.5)

    def forza_di_nascita(self, sorte):
        """Il volume di una stazione che nasce, da una sorte fra 0 e 1.

        Il minimo dipende dalla propagazione, 0,1 a 0, 0,2 a 50 e 0,5 a 100, e
        il massimo resta uno. A 50 e' esattamente la formula di prima, con la
        stessa sorte: chi non tocca la propagazione sente le stesse stazioni.
        """
        f = self.aperta
        a, b, c = VOLUME_MINIMO
        minimo = a + (b - a) * f / 0.5 if f <= 0.5 else b + (c - b) * (f - 0.5) / 0.5
        return minimo + (1.0 - minimo) * sorte

    def media_risposte_cq(self):
        """Quante stazioni rispondono in media a un CQ nel pile-up: una frazione del tetto che cresce con la propagazione."""
        basso, alto = RISPOSTA_CQ
        return self.pileup_massime * (basso + (alto - basso) * self.aperta)

    def posti_liberi(self):
        """Quante stazioni possono ancora nascere senza superare il tetto del pile-up."""
        return max(0, self.pileup_massime - len(self.dx_attive()))

    def intervallo_qrm(self):
        """L'intervallo medio fra due stazioni di disturbo, in secondi.

        Nel pile-up la propagazione lo cambia, 480 a 0, 240 a 50 come cwsim, 120
        a 100: con la banda aperta c'e' piu' gente in aria. Nel modo singolo
        la propagazione tocca soltanto forza e QSB, per scelta di Gabriele,
        e l'intervallo resta quello di cwsim.
        """
        if not self.pileup:
            return INTERVALLO_QRM
        return INTERVALLO_QRM * 2.0 ** (1.0 - 2.0 * self.aperta)

    def arrivi_spontanei(self, adesso, dt):
        """Sopra 50 di propagazione le stazioni arrivano anche senza CQ, fino al tetto.

        Riempiono i posti liberi con una costante di tempo che a 100 vale
        RIEMPIMENTO_SPONTANEI e cresce scendendo verso 50, dove gli arrivi
        spontanei spariscono. Chi arriva a frequenza libera vuole gia' il QSO
        e chiama dopo un attimo; chi arriva mentre trasmetto e' come chi nasce
        dopo un CQ: aspetta la fine, e risponde se ho chiamato o chiuso.
        """
        f = self.aperta
        liberi = self.posti_liberi()
        if f <= 0.5 or dt <= 0 or not liberi:
            return
        costante = RIEMPIMENTO_SPONTANEI / (2.0 * (f - 0.5))
        for _ in range(min(liberi, poisson(self.rng, liberi * dt / costante))):
            nuova = StazioneDX(self, adesso, singola=False)
            if not self.io_trasmette:
                nuova.oper.imposta_stato(StatoOp.VUOLE_QSO)
                nuova.stato = Stato.PREPARA
                nuova.scadenza = adesso + self.rng.uniform(*ATTESA_SPONTANEI)
            self.stazioni.append(nuova)

    def difetti_di_nota(self):
        """Il chirp e il vibrato di una stazione che nasce adesso, o niente.

        Vanno con il flutter, che e' l'interruttore dei difetti del segnale, e
        sono indipendenti fra loro e dall'evanescenza: in radio una stazione
        puo' avere tutto insieme, oppure niente. Il chirp cade da una parte o
        dall'altra con la stessa probabilita', perche' un trasmettitore puo'
        salire o scendere.
        """
        if not self.flutter:
            return None, None
        chirp = None
        if self.rng.random() < PROB_CHIRP:
            chirp = self.rng.uniform(*CHIRP_SCARTO) * self.rng.choice((-1, 1))
        vibrato = None
        if self.rng.random() < PROB_VIBRATO:
            vibrato = (self.rng.uniform(*VIBRATO_PROFONDITA), self.rng.uniform(*VIBRATO_FREQUENZA))
        return chirp, vibrato

    def pesi_stazione(self):
        """I pesi di una stazione: quelli della manipolazione automatica, oppure quelli di chi usa il tasto verticale.

        La probabilita' e i tre intervalli vengono dalle impostazioni: quando
        la sorte dice tasto verticale, i tre pesi si estraggono insieme,
        ciascuno nel proprio intervallo, e valgono per tutta la stazione.
        """
        probabilita, (l0, l1), (s0, s1), (p0, p1) = self.pesi_manuali
        if self.rng.random() < probabilita / (100.0 if probabilita > 1 else 1.0):
            return (self.rng.randint(l0, l1), self.rng.randint(s0, s1), self.rng.randint(p0, p1))
        return PESO_STANDARD

    def guadagno(self, stazione):
        """Il volume con cui la stazione arriva: la sua forza per il filtro di banda."""
        return stazione.volume * guadagno_filtro(self.banda, stazione.scarto_tono)

    def dx_attive(self):
        return [s for s in self.stazioni if isinstance(s, StazioneDX) and s.oper.stato != StatoOp.FATTO]

    def qrm_attive(self):
        return [s for s in self.stazioni if isinstance(s, StazioneQRM)]

    def testo_mio(self, messaggi, marca=False):
        """Il testo che trasmetto io per questi messaggi.

        Con marca il mio rapporto esce fra due segni, come quello delle
        stazioni: chi costruisce il suono sa dove tagliare per mandarlo piu'
        accelerato. Il mio non tira la probabilita': se l'interruttore e' acceso
        il mio 5NN e' sempre accelerato, perche' e' una mia abitudine e non
        una cosa che mi capita.
        """
        pezzi = []
        for m in messaggi:
            testo = TESTI[m]
            if m == Msg.TU:
                testo = CHIUSURE[0] if self.rng.random() < PROB_CHIUSURA_TU else self.rng.choice(CHIUSURE[1:])
            numero = numero_come_testo(self.rng, 599, self.mio_nr)
            if marca and len(numero) > LUNGHEZZA_RAPPORTO:
                numero = MARCA_VELOCE + numero[:LUNGHEZZA_RAPPORTO] + MARCA_VELOCE + numero[LUNGHEZZA_RAPPORTO:]
            testo = testo.replace("<#>", numero)
            testo = testo.replace("<my>", self.mio_nominativo).replace("<his>", self.suo_nominativo)
            pezzi.append(testo)
        return " ".join(pezzi)

    def io_trasmetti(self, messaggi, adesso, suo_nominativo=None, testo=None, accoda=False):
        """Comincio a trasmettere: le stazioni smettono di aspettare e si mettono a copiare.

        Con accoda, se sto gia' trasmettendo i messaggi si aggiungono a quelli
        in corso invece di sostituirli, e l'inizio non si ridice: e' il gesto
        di Morse Runner, dove F5 e poi F7 mandano il nominativo copiato e poi
        il punto interrogativo. Le stazioni devono ricevere l'elenco completo
        in una volta sola, alla fine di tutta la coda: due inizi e due fini
        per una chiamata sola costerebbero loro due punti di pazienza, e nel
        buco fra i due pezzi farebbero in tempo a rispondermi sopra.

        Il testo restituito e' quello dei soli messaggi nuovi, perche' quello
        di prima e' gia' in aria.
        """
        if self.inizio is None:
            self.inizio = adesso
        if suo_nominativo is not None:
            self.suo_nominativo = suo_nominativo.strip().upper()
        if accoda and self.io_trasmette:
            self.io_messaggi.extend(messaggi)
        else:
            self.io_messaggi = list(messaggi)
        if Msg.TU in self.io_messaggi:
            self.attesa_annullata = False
        if not self.io_trasmette:
            self.io_trasmette = True
            for s in self.stazioni:
                s.processa(Evento.IO_INIZIO, adesso)
        if testo is not None:
            marcato = testo
        else:
            marcato = self.testo_mio(messaggi, marca=self.scambio_probabilita > 0)
        mio_testo = marcato.replace(MARCA_VELOCE, "")
        miei_pezzi = dividi_in_pezzi(marcato, self.mio_wpm, self.scambio_incremento)
        return Richiesta(IO, mio_testo, self.mio_wpm, self.mio_pitch, *self.mio_pesi, 1.0, 0.0, tuple(messaggi), None, None, None, False, miei_pezzi)

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
            # Il tetto non si supera mai: chi e' gia' in aria occupa il suo posto.
            for _ in range(min(self.posti_liberi(), poisson(self.rng, self.media_risposte_cq()))):
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
        """La verita' della stazione che ho messo a log, quando si puo' dire quale e'.

        Si cerca prima quella che torna con il nominativo a log. Se nessuna
        torna e ce n'e' una sola in sospeso, e' quella, ed e' il caso normale
        del nominativo copiato male: serve a dire cos'era davvero. Se ce ne
        sono piu' d'una non si indovina. Prima si restituiva comunque la piu'
        vecchia, e poteva essere di una stazione che non c'entrava niente:
        finiva nella riga a schermo come se fosse la verita' e nel confronto
        carattere per carattere, inventando errori su lettere mai mandate.
        """
        for i, verita in enumerate(self.verita_pendenti):
            if verita[0] == nominativo:
                return self.verita_pendenti.pop(i)
        if len(self.verita_pendenti) == 1:
            return self.verita_pendenti.pop(0)
        return None

    def chiudi_attesa(self):
        """Porta a log il QSO in sospeso e restituisce l'evento da riferire.

        L'evento porta anche la verita' usata per la verifica, cosi' chi lo
        riceve puo' dire cos'era davvero senza ricostruirla da se': a fine
        contest non c'e' nessun evento qso nello stesso giro da cui prenderla.
        """
        quando, nominativo, rst, nr, nr_mandato = self.in_attesa
        self.in_attesa = None
        self.attesa_annullata = False
        verita = self.prendi_verita(nominativo)
        self.verita_pendenti.clear()
        verifica = self.punteggio.registra(quando, nominativo, rst, nr, nr_mandato, verita)
        return ("log", self.punteggio.log[-1], verifica, verita)

    def chiudi_contest(self):
        """Fine del contest: il QSO eventualmente in sospeso va a log com'e'.

        Prima pero' si chiede la verita' alla stazione che stavo lavorando, se
        e' ancora viva. Senza, l'ultimo QSO di ogni sessione a tempo risultava
        NIL anche copiato giusto: la stazione dice la sua verita' soltanto
        quando il mio TU e' finito, e il tempo scade prima.
        """
        if self.in_attesa is None:
            return []
        nominativo = self.in_attesa[1]
        if not any(v[0] == nominativo for v in self.verita_pendenti):
            for s in self.stazioni:
                if isinstance(s, StazioneDX) and s.mio == nominativo:
                    self.verita_pendenti.append(s.verita())
                    break
        return [self.chiudi_attesa()]

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
                if self.rng.random() < PROB_SALUTO:
                    esito.richieste.append(s.saluto(self.rng.uniform(*RITARDO_SALUTO)))
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
        if self.pileup and self.ultimo_tick is not None:
            self.arrivi_spontanei(adesso, max(0.0, adesso - self.ultimo_tick))
        if self.qrm and self.ultimo_tick is not None:
            dt = max(0.0, adesso - self.ultimo_tick)
            if len(self.qrm_attive()) < self.qrm_massime and self.rng.random() < dt / self.intervallo_qrm():
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
