# Prove automatiche di CWapu, il motore del contest.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Fable 5.1, modalita' auto).
# Nate con la issue 7. Il motore non suona e non legge la tastiera: qui si
# pilota con un orologio finto, cioe' i secondi passati ad avanza(), e con un
# generatore casuale a seme fisso, cosi' ogni prova e' ripetibile.

import itertools
import os
import random
import sys

import pytest

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)

import contest as ct  # noqa: E402

NOMINATIVI = ("DL3XY", "IK2ABC", "W9CF", "F5IN", "JA1ZZZ", "VE3NEA", "OH2BH", "EA3XY")


def sorgente(*lista):
    """Una funzione che da' i nominativi in quest'ordine, e poi ricomincia."""
    giro = itertools.cycle(lista or NOMINATIVI)
    return lambda: next(giro)


def motore(**cambi):
    opzioni = {"seme": 1}
    opzioni.update(cambi)
    return ct.Contest("IZ4APU", 25, 600, sorgente(), **opzioni)


def avanza_fino(m, da, a, passo=0.5, finite=(), trasmissioni_brevi=False):
    """Fa girare l'orologio e raccoglie richieste ed eventi.

    Con trasmissioni_brevi ogni richiesta di suono si considera finita al
    giro successivo, come farebbe il ciclo di cwapu quando il PlaybackHandle
    dice di aver finito: senza, le stazioni resterebbero a trasmettere per
    sempre e non scatterebbero mai le loro scadenze.
    """
    richieste, eventi = [], []
    t = da
    prime = set(finite)
    while t <= a + 1e-9:
        e = m.avanza(round(t, 3), prime)
        prime = {r.stazione for r in e.richieste} if trasmissioni_brevi else set()
        richieste.extend(e.richieste)
        eventi.extend(e.eventi)
        t += passo
    return richieste, eventi


class TestPrefisso:
    @pytest.mark.parametrize(
        ("nominativo", "atteso"),
        [
            ("DL3XY", "DL3"),
            ("IZ4APU", "IZ4"),
            ("W9CF", "W9"),
            ("P55CF", "P55"),
            ("F5IN", "F5"),
            ("JA1ZZZ", "JA1"),
            ("DL3XY/P", "DL3"),
            ("DL3XY/7", "DL7"),
            ("F/DL3XY", "F0"),
            ("VK9/W9CF", "VK9"),
            ("4X4ABC", "4X4"),
        ],
    )
    def test_le_regole_wpx(self, nominativo, atteso):
        assert ct.prefisso(nominativo) == atteso


class TestFiltro:
    def test_dentro_meta_banda_passa_tutto(self):
        assert ct.guadagno_filtro(500, 0) == 1.0
        assert ct.guadagno_filtro(500, 250) == 1.0

    def test_fuori_banda_resta_il_pavimento_mai_il_silenzio(self):
        """Una stazione muta chiama, aspetta e rinuncia senza che nessuno
        possa sentirla: finiva fra le rinunce del rapporto come un'occasione
        persa che non c'era mai stata."""
        assert ct.guadagno_filtro(500, 500) == ct.FILTRO_PAVIMENTO
        assert ct.guadagno_filtro(500, 5000) == ct.FILTRO_PAVIMENTO
        assert ct.FILTRO_PAVIMENTO > 0.0

    def test_in_mezzo_al_fianco_passa_meta(self):
        mezzo = ct.FILTRO_PAVIMENTO + (1.0 - ct.FILTRO_PAVIMENTO) / 2.0
        assert ct.guadagno_filtro(500, 375) == pytest.approx(mezzo)
        assert ct.guadagno_filtro(500, -375) == pytest.approx(mezzo)

    def test_il_fianco_scende_senza_gradini(self):
        """Fra la banda passante e il pavimento non ci sono salti."""
        valori = [ct.guadagno_filtro(400, s) for s in range(0, 500, 5)]
        assert valori[0] == 1.0 and valori[-1] == ct.FILTRO_PAVIMENTO
        passi = list(itertools.pairwise(valori))
        assert all(b <= a + 1e-9 for a, b in passi)
        assert max(a - b for a, b in passi) < 0.05

    def test_una_banda_larga_lascia_passare_di_piu(self):
        assert ct.guadagno_filtro(600, 300) == 1.0
        assert ct.guadagno_filtro(100, 100) == ct.FILTRO_PAVIMENTO
        assert ct.guadagno_filtro(600, 300) > ct.guadagno_filtro(100, 300)


class TestRitmo:
    def test_l_ultimo_intervallo_si_rapporta_ai_secondi_davvero_trascorsi(self):
        """Otto QSO in due minuti sono duecentoquaranta all'ora, non
        novantasei: moltiplicare per dodici un intervallo che e' durato due
        minuti faceva sembrare lentissima ogni sessione corta."""
        p = ct.Punteggio()
        for i in range(8):
            p.registra(float(i), f"DL{i}XY", 599, i + 1, i + 1, None)
        ritmo = p.qso_all_ora(120.0)
        assert ritmo == [(0, 4, 240)], ritmo

    def test_un_intervallo_pieno_resta_il_per_dodici_di_morse_runner(self):
        p = ct.Punteggio()
        for i in range(8):
            p.registra(float(i), f"DL{i}XY", 599, i + 1, i + 1, None)
        assert p.qso_all_ora(300.0) == [(0, 4, 96)]

    def test_una_coda_piu_corta_di_un_minuto_non_si_riporta(self):
        """Due QSO in dieci secondi darebbero settecentoventi all'ora, un
        numero che non descrive niente."""
        p = ct.Punteggio()
        for i in range(4):
            p.registra(float(i), f"DL{i}XY", 599, i + 1, i + 1, None)
        p.registra(305.0, "W9CF", 599, 9, 9, None)
        ritmo = p.qso_all_ora(310.0)
        assert len(ritmo) == 1 and ritmo[0][0] == 0, ritmo


class TestSorte:
    def test_poisson_ha_la_media_giusta(self):
        rng = random.Random(3)
        estrazioni = [ct.poisson(rng, 2.0) for _ in range(4000)]
        assert 1.85 < sum(estrazioni) / len(estrazioni) < 2.15
        assert ct.poisson(rng, 0) == 0

    def test_rayleigh_ha_media_quattro(self):
        rng = random.Random(4)
        estrazioni = [ct.rayleigh(rng, ct.SCALA_RAYLEIGH) for _ in range(4000)]
        assert 3.8 < sum(estrazioni) / len(estrazioni) < 4.2


class TestOperatore:
    def nuovo(self, sbadati=False, nominativo="DL3XY"):
        m = motore(sbadati=sbadati)
        op = ct.Operatore(m.rng, m, nominativo, 0.0, singola=False)
        op.prob_ripeti = 0.0
        return m, op

    def test_il_cq_lo_fa_volere_il_qso(self):
        _, op = self.nuovo()
        op.ricevuto([ct.Msg.CQ])
        assert op.stato == ct.StatoOp.VUOLE_QSO
        assert op.pazienza is not None
        assert op.risposta() == ct.Msg.MIO

    def test_il_giro_intero_di_un_qso(self):
        m, op = self.nuovo()
        op.ricevuto([ct.Msg.CQ])
        m.suo_nominativo = "DL3XY"
        op.ricevuto([ct.Msg.SUO, ct.Msg.NR])
        assert op.stato == ct.StatoOp.VUOLE_FINE
        assert op.risposta() in (ct.Msg.R_NR, ct.Msg.R_NR2)
        op.ricevuto([ct.Msg.TU])
        assert op.stato == ct.StatoOp.FATTO
        assert op.risposta() == ct.Msg.NESSUNO

    def test_un_nominativo_quasi_giusto_fa_ripetere_il_suo(self):
        m, op = self.nuovo()
        op.ricevuto([ct.Msg.CQ])
        m.suo_nominativo = "DL3XZ"
        op.ricevuto([ct.Msg.SUO])
        assert op.stato == ct.StatoOp.VUOLE_CALL_NR
        assert op.risposta() in (ct.Msg.DE_MIO1, ct.Msg.DE_MIO2)

    def test_un_nominativo_di_un_altro_lo_rimette_in_attesa(self):
        m, op = self.nuovo()
        op.ricevuto([ct.Msg.CQ])
        m.suo_nominativo = "IK2ABC"
        op.ricevuto([ct.Msg.SUO])
        assert op.stato == ct.StatoOp.ATTENDE_FINE

    def test_il_parziale_vale_come_con_il_jolly(self):
        """Decisione D9: DL3 vale DL3?, cosi' la stazione ripete invece di tacere."""
        m, op = self.nuovo()
        m.suo_nominativo = "DL3"
        assert op.e_il_mio() == ct.Copia.QUASI
        m.suo_nominativo = "DL3?"
        assert op.e_il_mio() == ct.Copia.QUASI
        m.suo_nominativo = "D"
        assert op.e_il_mio() == ct.Copia.NO
        m.suo_nominativo = "DL3XY"
        assert op.e_il_mio() == ct.Copia.SI

    def test_la_pazienza_finisce(self):
        m, op = self.nuovo()
        op.ricevuto([ct.Msg.CQ])
        op.pazienza = 1
        m.suo_nominativo = "DL3XY"
        op.ricevuto([ct.Msg.SUO])
        assert op.stato == ct.StatoOp.VUOLE_NR
        op.pazienza = 1
        op.ricevuto([ct.Msg.CQ])
        assert op.stato == ct.StatoOp.FALLITO

    def test_l_attesa_della_risposta_sta_fra_due_e_sei_secondi(self):
        _, op = self.nuovo()
        attese = [op.attesa_risposta() for _ in range(500)]
        assert min(attese) >= 2.0 and max(attese) <= 6.0

    def test_il_ritardo_di_risposta_sta_fra_un_decimo_e_sei_decimi(self):
        _, op = self.nuovo()
        assert op.ritardo_invio() is None
        op.ricevuto([ct.Msg.CQ])
        ritardi = [op.ritardo_invio() for _ in range(200)]
        assert min(ritardi) >= 0.1 and max(ritardi) <= 0.6


class TestQsoSingolo:
    def qso_completo(self, nominativo_a_log="DL3XY"):
        m = motore(pileup=False, sbadati=False)
        e = m.avanza(0.0)
        assert ("nasce", "DL3XY") in e.eventi
        assert e.richieste == []
        cq = m.io_trasmetti([ct.Msg.CQ], 0.0)
        assert cq.stazione == ct.IO and cq.testo == "CQ TEST IZ4APU"
        richieste, _ = avanza_fino(m, 1.0, 2.0, finite=[ct.IO])
        assert len(richieste) == 1 and richieste[0].testo == "DL3XY"
        chiamante = richieste[0].stazione
        m.stazioni[0].oper.prob_ripeti = 0.0
        avanza_fino(m, 2.5, 3.0, finite=[chiamante])
        scambio = m.io_trasmetti([ct.Msg.SUO, ct.Msg.NR], 3.0, suo_nominativo="DL3XY")
        # Il mio scambio esce nella forma delle stazioni: rapporto e tre cifre
        # attaccati, con lo zero abbreviato.
        assert scambio.testo.startswith("DL3XY 5NN")
        assert scambio.testo.removeprefix("DL3XY 5NN") in ("TT1", "OO1")
        richieste, _ = avanza_fino(m, 4.0, 5.0, finite=[ct.IO])
        assert len(richieste) == 1 and richieste[0].testo.startswith("R 5NN")
        avanza_fino(m, 5.5, 6.0, finite=[chiamante])
        m.registra_qso(6.0, nominativo_a_log, nr=1)
        m.io_trasmetti([ct.Msg.TU], 6.0)
        _, eventi = avanza_fino(m, 7.0, 8.0, finite=[ct.IO])
        return m, eventi

    def test_un_qso_giusto_vale_un_punto_e_un_prefisso(self):
        m, eventi = self.qso_completo()
        assert ("qso", ("DL3XY", 599, 1)) in eventi
        log = [e for e in eventi if e[0] == "log"]
        assert len(log) == 1 and log[0][2] == ""
        assert m.punteggio.punti_verificati == 1
        assert m.punteggio.prefissi_verificati == {"DL3"}
        assert m.punteggio.punteggio_verificato == 1
        assert m.mio_nr == 2
        # In modo singolo la stazione seguente nasce subito.
        assert any(e[0] == "nasce" for e in eventi)

    def test_un_nominativo_sbagliato_a_log_e_un_nil(self):
        m, eventi = self.qso_completo(nominativo_a_log="DL3XZ")
        log = [e for e in eventi if e[0] == "log"]
        assert log[0][2] == "NIL"
        assert m.punteggio.punti_grezzi == 1
        assert m.punteggio.punti_verificati == 0
        assert m.punteggio.nominativi_sbagliati() == ["DL3XZ"]
        assert m.punteggio.percentuale_errore == 100.0


class TestRinuncia:
    def test_chi_non_riceve_risposta_se_ne_va(self):
        m = motore(pileup=False, sbadati=False)
        m.avanza(0.0)
        m.io_trasmetti([ct.Msg.CQ], 0.0)
        richieste, eventi = avanza_fino(m, 1.0, 120.0, finite=[ct.IO], trasmissioni_brevi=True)
        chiamate = [r for r in richieste if r.stazione != ct.IO]
        assert chiamate and chiamate[0].testo == "DL3XY"
        # Chiama piu' volte, perde la pazienza e se ne va.
        assert len([r for r in chiamate if r.testo == "DL3XY"]) >= 2
        assert ("rinuncia", "DL3XY") in eventi
        assert "DL3XY" in m.punteggio.rinunce
        # Dopo la rinuncia ne nasce un'altra, che aspetta un mio CQ.
        assert [e for e in eventi if e[0] == "nasce"]


class TestPileup:
    def test_dopo_il_cq_rispondono_in_media_due_stazioni(self):
        conteggi = []
        for seme in range(30):
            m = motore(pileup=True, attivita=4, seme=seme)
            assert m.avanza(0.0).eventi == []
            m.io_trasmetti([ct.Msg.CQ], 0.0)
            m.avanza(1.0, [ct.IO])
            conteggi.append(len(m.dx_attive()))
        media = sum(conteggi) / len(conteggi)
        assert 1.2 < media < 2.8
        assert max(conteggi) >= 3

    def test_le_stazioni_hanno_voci_diverse_entro_i_limiti(self):
        m = motore(pileup=True, attivita=9, ampiezza_stereo=60, seme=7)
        m.io_trasmetti([ct.Msg.CQ], 0.0)
        m.avanza(1.0, [ct.IO])
        stazioni = m.dx_attive()
        assert len(stazioni) >= 2
        for s in stazioni:
            assert -60 <= s.pan <= 60
            assert 0.2 <= s.volume <= 1.0
            assert ct.TONO_STAZIONE[0] <= s.pitch <= ct.TONO_STAZIONE[1]
            assert abs(s.pitch - 600) <= ct.TONO_MASSIMO
            assert 22 <= s.wpm <= 28

    def test_il_tu_con_il_mio_nominativo_richiama_altre_stazioni(self):
        m = motore(pileup=True, attivita=6, seme=11)
        m.io_trasmetti([ct.Msg.TU, ct.Msg.MIO], 0.0)
        assert m.testo_mio([ct.Msg.TU, ct.Msg.MIO]) == "TU IZ4APU"
        m.avanza(1.0, [ct.IO])
        assert len(m.dx_attive()) >= 1


class TestQrm:
    def test_le_stazioni_di_disturbo_arrivano_e_non_superano_il_massimo(self):
        m = motore(pileup=False, qrm=True, qrm_massime=2, seme=5)
        richieste, _ = avanza_fino(m, 0.0, 900.0, passo=0.5, trasmissioni_brevi=True)
        disturbi = [r for r in richieste if r.stazione != ct.IO and r.messaggi[0] in (ct.Msg.QRL, ct.Msg.QRL2, ct.Msg.CQ_LUNGO, ct.Msg.QSY)]
        assert disturbi
        testi = " ".join(r.testo for r in disturbi)
        assert "QRL?" in testi or "CQ CQ TEST" in testi
        assert all(30 <= r.wpm <= 50 for r in disturbi)

    def test_mai_piu_del_massimo_insieme(self):
        m = motore(pileup=False, qrm=True, qrm_massime=1, seme=5)
        finite = set()
        for t in range(0, 1800):
            e = m.avanza(t * 0.5, finite)
            finite = {r.stazione for r in e.richieste}
            assert len(m.qrm_attive()) <= 1


class TestPesi:
    def test_con_probabilita_zero_i_pesi_sono_standard(self):
        m = motore(pesi_manuali=(0, (30, 60), (25, 75), (15, 50)))
        assert all(m.pesi_stazione() == ct.PESO_STANDARD for _ in range(20))

    def test_con_probabilita_piena_stanno_negli_intervalli(self):
        m = motore(pesi_manuali=(100, (30, 60), (25, 75), (15, 50)))
        for _ in range(50):
            l, s, p = m.pesi_stazione()
            assert 30 <= l <= 60 and 25 <= s <= 75 and 15 <= p <= 50

    def test_la_probabilita_si_accetta_anche_in_frazione(self):
        m = motore(pesi_manuali=(1.0, (40, 40), (50, 50), (50, 50)))
        assert m.pesi_stazione() == (40, 50, 50)


class TestPunteggio:
    def test_punti_prefissi_e_verifiche(self):
        p = ct.Punteggio()
        assert p.registra(10.0, "DL3XY", 599, 27, 1, ("DL3XY", 599, 27)) == ""
        assert p.registra(20.0, "DL4AB", 599, 3, 2, ("DL4AB", 599, 4)) == "NR"
        assert p.registra(30.0, "W9CF", 599, 5, 3, ("W9CF", 579, 5)) == "RST"
        assert p.registra(400.0, "F5IN", 599, 7, 4, None) == "NIL"
        assert p.punti_grezzi == 4 and p.punti_verificati == 1
        assert p.prefissi_grezzi == {"DL3", "DL4", "W9", "F5"}
        assert p.prefissi_verificati == {"DL3"}
        assert p.punteggio_grezzo == 16 and p.punteggio_verificato == 1
        assert p.percentuale_errore == 75.0
        assert p.nominativi_sbagliati() == ["F5IN"]
        assert [v.nominativo for v in p.scambi_sbagliati()] == ["DL4AB", "W9CF"]

    def test_i_qso_all_ora_per_cinque_minuti(self):
        p = ct.Punteggio()
        for quando in (10.0, 20.0, 30.0, 400.0):
            p.registra(quando, "DL3XY", 599, 1, 1, ("DL3XY", 599, 1))
        assert p.qso_all_ora(600) == [(0, 4, 36), (5, 9, 12)]
        assert p.qso_all_ora(900) == [(0, 4, 36), (5, 9, 12), (10, 14, 0)]


class TestNumeri:
    def test_il_rapporto_esce_abbreviato(self):
        m = motore(sbadati=False)
        s = ct.Stazione(m, "DL3XY", 25, 600, 0.0, 1.0)
        s.nr = 27
        testi = {s.testo_numero() for _ in range(50)}
        assert all(t.startswith("5NN") for t in testi)
        assert all("9" not in t for t in testi)
        s.nr = 100
        testo = s.testo_numero()
        assert testo in ("5NN1TT", "5NN1OO")

    def test_lo_sbadato_corregge_il_numero(self):
        m = motore(sbadati=True)
        s = ct.Stazione(m, "DL3XY", 25, 600, 0.0, 1.0)
        s.nr = 33
        s.errore_nr = True
        testo = s.testo_numero()
        assert "eeeee" in testo
        assert s.errore_nr is False


class TestCorrezioniDelPorting:
    """I rilievi della revisione del motore, ognuno con la sua prova."""

    def test_i_disturbi_hanno_l_intervallo_di_cwsim(self):
        assert ct.INTERVALLO_QRM == 240.0

    def test_senza_qsb_nessuna_stazione_evanesce(self):
        m = motore()
        assert all(m.evanescenza() is None for _ in range(20))

    def test_con_il_qsb_ogni_stazione_prende_la_sua_banda(self):
        m = motore(qsb=True)
        bande = [m.evanescenza() for _ in range(50)]
        assert all(ct.QSB_BANDA[0] <= b <= ct.QSB_BANDA[1] for b in bande)
        assert len(set(bande)) > 10

    def test_con_il_flutter_tre_stazioni_su_dieci_vanno_veloci(self):
        m = motore(qsb=True, flutter=True, seme=3)
        bande = [m.evanescenza() for _ in range(400)]
        veloci = [b for b in bande if ct.FLUTTER_BANDA[0] <= b <= ct.FLUTTER_BANDA[1]]
        assert 0.2 < len(veloci) / len(bande) < 0.4, len(veloci) / len(bande)

    def test_con_il_flutter_una_su_dieci_ha_la_nota_ruvida(self):
        """Non sta in Morse Runner: la chiede Gabriele, che in radio di
        difetti ne sente molti di piu' di uno."""
        m = motore(qsb=True, flutter=True, seme=3)
        bande = [m.evanescenza() for _ in range(400)]
        ruvide = [b for b in bande if b >= ct.RUVIDO_BANDA[0]]
        assert all(ct.RUVIDO_BANDA[0] <= b <= ct.RUVIDO_BANDA[1] for b in ruvide)
        assert 0.05 < len(ruvide) / len(bande) < 0.16, len(ruvide) / len(bande)
        # Le tre nature non si mescolano: ogni banda sta in uno dei tre gruppi.
        for banda in bande:
            assert (
                ct.QSB_BANDA[0] <= banda <= ct.QSB_BANDA[1]
                or ct.FLUTTER_BANDA[0] <= banda <= ct.FLUTTER_BANDA[1]
                or ct.RUVIDO_BANDA[0] <= banda <= ct.RUVIDO_BANDA[1]
            ), banda

    def test_senza_flutter_la_nota_ruvida_non_esiste(self):
        m = motore(qsb=True, flutter=False, seme=3)
        assert all(b <= ct.QSB_BANDA[1] for b in (m.evanescenza() for _ in range(200)))

    def test_le_onde_lente_del_qsb_non_sono_una_rarita(self):
        """Estraendo la banda in modo uniforme, le onde lente occupano un
        angolo dell'intervallo e non uscirebbero quasi mai: e' il rilievo di
        Gabriele del 21 settembre 2026, che le trovava tutte repentine."""
        m = motore(qsb=True, seme=5)
        bande = [m.evanescenza() for _ in range(400)]
        assert all(ct.QSB_BANDA[0] <= b <= ct.QSB_BANDA[1] for b in bande)
        lente = [b for b in bande if b <= 0.15]
        assert 0.4 < len(lente) / len(bande) < 0.7, len(lente) / len(bande)
        # E la piu' lenta di tutte deve impiegare parecchi secondi a scendere.
        assert 0.37 / min(bande) > 8.0, 0.37 / min(bande)

    def test_le_stazioni_si_allargano_sui_toni(self):
        """Erano tutte centrate dentro la banda passante del filtro."""
        m = motore(pileup=True, seme=3)
        m.mio_pitch = 600
        toni = []
        for _ in range(300):
            stazione = ct.StazioneDX(m, 0.0, singola=False)
            toni.append(stazione.scarto_tono)
        larghi = [t for t in toni if abs(t) > 300]
        assert larghi, "nessuna stazione fuori dai trecento hertz"
        assert all(abs(t) <= ct.TONO_MASSIMO for t in toni)
        assert 0.1 < len(larghi) / len(toni) < 0.5, len(larghi) / len(toni)

    def test_con_il_tono_alto_le_stazioni_non_si_ammucchiano(self):
        """Il tetto stava a duemila: con il tono proprio piu' in alto tutte le
        stazioni ci finivano sopra, a centinaia di hertz dal mio, cioe' mute."""
        m = motore(pileup=True, seme=3)
        m.mio_pitch = 2600
        toni = {ct.StazioneDX(m, 0.0, singola=False).pitch for _ in range(60)}
        assert len(toni) > 30, sorted(toni)[:5]

    def test_nessuna_stazione_nasce_fuori_da_cio_che_il_motore_accetta(self):
        """Fuori dai limiti CWzator rifiuta il messaggio e lo dice: Gabriele
        riceveva una fila di errori avvicinandosi ai limiti del tono."""
        for mio in (200, 550, 1500, 2700):
            m = motore(pileup=True, seme=9)
            m.mio_pitch = mio
            for _ in range(200):
                assert ct.TONO_STAZIONE[0] <= ct.StazioneDX(m, 0.0, singola=False).pitch <= ct.TONO_STAZIONE[1]

    def test_ai_limiti_lo_scarto_si_ribalta_invece_di_tagliarsi(self):
        """Tagliare ammucchierebbe le stazioni sul bordo, lontanissime dal mio
        tono e quindi mute sotto il filtro."""
        alto = ct.TONO_STAZIONE[1]
        assert ct.tono_stazione(2700, 450) == 2250
        assert ct.tono_stazione(200, -450) == 650
        # E quando ribaltare non basta, il limite regge lo stesso.
        assert ct.TONO_STAZIONE[0] <= ct.tono_stazione(alto, 0) <= alto

    def test_nessuna_stazione_nasce_muta(self):
        """Nasceva muta e moriva muta: chiamava, aspettava, rinunciava, e la
        rinuncia finiva nel rapporto come un'occasione persa mai esistita.
        Con la banda a cento erano sei stazioni su dieci."""
        for banda in (100, 150, 250, 400, 600):
            m = motore(pileup=True, seme=5, banda=banda)
            m.mio_pitch = 500
            volumi = [m.guadagno(ct.StazioneDX(m, 0.0, singola=False)) for _ in range(300)]
            assert min(volumi) > 0.0, f"banda {banda}: {min(volumi)}"

    def test_il_filtro_segue_il_mio_tono(self):
        """Spostando il mio tono con Alt e le frecce, una stazione che prima
        era lontana deve avvicinarsi: lo scarto era congelato alla nascita e
        cercare con la sintonia non serviva a niente."""
        m = motore(pileup=True, seme=7, banda=200)
        m.mio_pitch = 500
        s = ct.StazioneDX(m, 0.0, singola=False)
        s.pitch = 900
        lontana = m.guadagno(s)
        m.mio_pitch = 900
        assert s.scarto_tono == 0
        assert m.guadagno(s) > lontana
        assert m.guadagno(s) == pytest.approx(s.volume)

    def test_i_messaggi_si_accodano_invece_di_sostituirsi(self):
        """F5 e poi F7: la stazione deve ricevere nominativo e punto
        interrogativo insieme, non il solo punto interrogativo."""
        m = motore(pileup=False, seme=2)
        m.avanza(0.0)
        m.io_trasmetti([ct.Msg.CQ], 0.0)
        m.io_finito(1.0)
        m.io_trasmetti([ct.Msg.SUO], 2.0, suo_nominativo="DL3XY")
        richiesta = m.io_trasmetti([ct.Msg.QM], 2.5, accoda=True)
        assert m.io_messaggi == [ct.Msg.SUO, ct.Msg.QM]
        # Il testo restituito e' quello dei soli messaggi nuovi: l'altro e'
        # gia' in aria.
        assert richiesta.testo.strip() == "?"
        assert m.io_trasmette

    def test_senza_accoda_i_messaggi_si_sostituiscono(self):
        m = motore(pileup=False, seme=2)
        m.avanza(0.0)
        m.io_trasmetti([ct.Msg.SUO], 0.0, suo_nominativo="DL3XY")
        m.io_trasmetti([ct.Msg.QM], 0.5)
        assert m.io_messaggi == [ct.Msg.QM]

    def test_accodare_non_ridice_l_inizio_alle_stazioni(self):
        """Un secondo inizio rimetterebbe in ascolto chi stava gia' copiando."""
        m = motore(pileup=True, attivita=9, seme=5)
        m.avanza(0.0)
        m.io_trasmetti([ct.Msg.CQ], 0.0)
        m.io_finito(1.0)
        avanza_fino(m, 1.5, 4.0, trasmissioni_brevi=True)
        assert m.stazioni, "nessuna stazione e' nata"
        stati_prima = [s.stato for s in m.stazioni]
        m.io_trasmetti([ct.Msg.SUO], 4.5, suo_nominativo="DL3XY")
        stati_dopo_inizio = [s.stato for s in m.stazioni]
        m.io_trasmetti([ct.Msg.QM], 5.0, accoda=True)
        assert [s.stato for s in m.stazioni] == stati_dopo_inizio
        assert stati_prima is not None

    def test_la_verita_di_un_altra_stazione_non_si_spaccia_per_la_tua(self):
        """Restituiva la piu' vecchia in sospeso: la riga diceva che avevi
        copiato male un nominativo che non ti era mai stato mandato, e il
        confronto carattere per carattere inventava errori."""
        m = motore(pileup=True, seme=1)
        m.verita_pendenti = [("DL3XY", 599, 1), ("W9CF", 599, 2)]
        assert m.prendi_verita("IK2ABC") is None
        assert len(m.verita_pendenti) == 2

    def test_con_una_sola_verita_in_sospeso_quella_e(self):
        """E' il caso normale del nominativo copiato male, e serve a dire
        cos'era davvero."""
        m = motore(pileup=True, seme=1)
        m.verita_pendenti = [("DL3XY", 599, 1)]
        assert m.prendi_verita("DL3XZ") == ("DL3XY", 599, 1)

    def test_l_ultimo_qso_non_e_nil_solo_perche_il_tempo_e_scaduto(self):
        """La stazione dice la sua verita' quando il mio TU e' finito: se il
        tempo scade prima, gliela si chiede lo stesso."""
        m = motore(pileup=False, seme=3)
        m.avanza(0.0)
        m.io_trasmetti([ct.Msg.CQ], 0.0)
        m.io_finito(1.0)
        avanza_fino(m, 1.5, 6.0, trasmissioni_brevi=True)
        vive = [s for s in m.stazioni if isinstance(s, ct.StazioneDX)]
        assert vive, "nessuna stazione in aria"
        stazione = vive[0]
        m.registra_qso(7.0, stazione.mio, stazione.nr, 599)
        eventi = m.chiudi_contest()
        assert eventi and eventi[0][0] == "log"
        assert eventi[0][2] == "", eventi[0]
        assert eventi[0][3] == (stazione.mio, int(stazione.rst), int(stazione.nr))

    def test_l_evento_di_log_porta_la_verita_usata(self):
        m = motore(pileup=False, seme=3)
        m.avanza(0.0)
        m.registra_qso(1.0, "DL3XY", 7, 599)
        eventi = m.chiudi_contest()
        assert len(eventi[0]) == 4

    def test_i_difetti_di_nota_vanno_con_il_flutter(self):
        """Il chirp e il vibrato sono difetti del segnale, come il flutter."""
        m = motore(qsb=True, flutter=True, seme=11)
        difetti = [m.difetti_di_nota() for _ in range(400)]
        chirp = [c for c, _ in difetti if c is not None]
        vibrato = [v for _, v in difetti if v is not None]
        assert 0.08 < len(chirp) / len(difetti) < 0.24, len(chirp) / len(difetti)
        assert 0.04 < len(vibrato) / len(difetti) < 0.18, len(vibrato) / len(difetti)
        # Il chirp cade da una parte e dall'altra: un trasmettitore puo' salire
        # o scendere.
        assert any(c > 0 for c in chirp) and any(c < 0 for c in chirp)
        assert all(ct.CHIRP_SCARTO[0] <= abs(c) <= ct.CHIRP_SCARTO[1] for c in chirp)
        assert all(ct.VIBRATO_PROFONDITA[0] <= p <= ct.VIBRATO_PROFONDITA[1] for p, _ in vibrato)
        assert all(ct.VIBRATO_FREQUENZA[0] <= f <= ct.VIBRATO_FREQUENZA[1] for _, f in vibrato)

    def test_senza_flutter_nessun_difetto_di_nota(self):
        m = motore(qsb=True, flutter=False)
        assert all(m.difetti_di_nota() == (None, None) for _ in range(50))

    def test_la_richiesta_porta_i_difetti_di_nota(self):
        m = motore(pileup=False, qsb=True, flutter=True, seme=4)
        m.avanza(0.0)
        m.io_trasmetti([ct.Msg.CQ], 0.0)
        richieste, _ = avanza_fino(m, 1.0, 3.0, finite=[ct.IO])
        assert richieste
        # Il mio messaggio non ha mai difetti: sono io.
        assert m.io_trasmetti([ct.Msg.CQ], 0.0).chirp is None
        assert m.io_trasmetti([ct.Msg.CQ], 0.0).vibrato is None

    def test_il_flutter_senza_qsb_non_esiste(self):
        m = motore(qsb=False, flutter=True)
        assert all(m.evanescenza() is None for _ in range(20))

    def test_la_richiesta_porta_la_banda_della_stazione(self):
        m = motore(pileup=False, qsb=True, seme=4)
        m.avanza(0.0)
        m.io_trasmetti([ct.Msg.CQ], 0.0)
        richieste, _ = avanza_fino(m, 1.0, 3.0, finite=[ct.IO])
        assert richieste
        assert all(r.qsb is not None for r in richieste)
        assert all(ct.QSB_BANDA[0] <= r.qsb <= ct.FLUTTER_BANDA[1] for r in richieste)

    def test_il_mio_messaggio_non_evanesce_mai(self):
        m = motore(pileup=False, qsb=True, flutter=True)
        assert m.io_trasmetti([ct.Msg.CQ], 0.0).qsb is None

    def test_l_ultima_lettera_sbagliata_non_e_gratis(self):
        o = ct.Operatore(random.Random(1), motore(), "DL3XY", 0.0, True)
        assert o.distanza("DL3XY") == 0
        assert o.distanza("DL3XZ") == 1
        assert o.confronta("DL3XY") == ct.Copia.SI
        assert o.confronta("DL3XZ") == ct.Copia.QUASI
        assert o.confronta("IK2ABC") == ct.Copia.NO

    def test_il_nominativo_troncato_vale_un_quasi(self):
        # Nella riga finale le lettere non arrivate non costano: e' il
        # parziale, che la stazione ripete invece di ignorare.
        o = ct.Operatore(random.Random(1), motore(), "DL3XY", 0.0, False)
        assert o.distanza("DL3") == 0
        assert o.confronta("DL3") == ct.Copia.QUASI
        assert o.confronta("?L3XY") == ct.Copia.QUASI

    def test_l_istante_del_log_non_e_sempre_zero(self):
        m = motore(pileup=True)
        m.avanza(0.0)
        m.registra_qso(42.0, "DL3XY", nr=1)
        m.verita_pendenti.append(("DL3XY", 599, 1))
        eventi = m.avanza(43.0).eventi
        voce = next(e for e in eventi if e[0] == "log")[1]
        assert voce.quando == 42.0

    def test_la_verita_si_prende_da_chi_corrisponde(self):
        # Due stazioni finite nello stesso giro: la riga a log non deve
        # pescare quella sbagliata e diventare NIL per colpa dell'altra.
        m = motore()
        m.verita_pendenti = [("IK2ABC", 599, 4), ("DL3XY", 599, 7)]
        assert m.prendi_verita("DL3XY") == ("DL3XY", 599, 7)
        assert m.prendi_verita("W9CF") == ("IK2ABC", 599, 4)
        assert m.prendi_verita("W9CF") is None

    def test_la_fine_detta_due_volte_vale_una(self):
        m = motore(pileup=False, sbadati=False)
        m.avanza(0.0)
        m.io_trasmetti([ct.Msg.CQ], 0.0)
        stazione = m.dx_attive()[0]
        m.annulla_trasmissione(1.0)
        pazienza = stazione.oper.pazienza
        m.io_finito(1.0)
        assert m.io_trasmette is False
        assert stazione.oper.pazienza == pazienza

    def test_l_esc_sul_tu_lascia_il_qso_in_sospeso(self):
        m = motore(pileup=True, sbadati=False)
        m.avanza(0.0)
        m.registra_qso(1.0, "DL3XY", nr=5)
        m.io_trasmetti([ct.Msg.TU], 1.0)
        m.annulla_trasmissione(2.0)
        eventi = m.avanza(2.5).eventi
        assert [e for e in eventi if e[0] == "log"] == []
        assert m.in_attesa is not None
        # Il TU rimandato chiude la riga, e la verita' arrivata vale.
        m.io_trasmetti([ct.Msg.TU], 3.0)
        m.verita_pendenti.append(("DL3XY", 599, 5))
        eventi = m.avanza(4.0, [ct.IO]).eventi
        log = [e for e in eventi if e[0] == "log"]
        assert len(log) == 1 and log[0][2] == ""
        assert m.mio_nr == 2

    def test_il_tu_rimandato_non_consuma_un_altro_progressivo(self):
        m = motore(pileup=True, sbadati=False)
        m.avanza(0.0)
        m.registra_qso(1.0, "DL3XY", nr=5)
        m.io_trasmetti([ct.Msg.TU], 1.0)
        m.annulla_trasmissione(2.0)
        m.registra_qso(3.0, "DL3XY", nr=5)
        assert m.mio_nr == 2
        assert m.in_attesa[0] == 1.0
        assert m.in_attesa[4] == 1

    def test_la_riga_abbandonata_va_a_log_quando_ne_arriva_un_altra(self):
        m = motore(pileup=True, sbadati=False)
        m.avanza(0.0)
        m.registra_qso(1.0, "DL3XY", nr=5)
        m.io_trasmetti([ct.Msg.TU], 1.0)
        m.annulla_trasmissione(2.0)
        m.registra_qso(9.0, "IK2ABC", nr=6)
        eventi = m.avanza(10.0).eventi
        log = [e for e in eventi if e[0] == "log"]
        # La riga abbandonata esce per prima, con il suo istante e il suo NIL.
        assert [e[1].nominativo for e in log] == ["DL3XY", "IK2ABC"]
        assert log[0][1].quando == 1.0 and log[0][2] == "NIL"
        assert m.mio_nr == 3

    def test_la_fine_del_contest_chiude_la_riga_in_sospeso(self):
        m = motore(pileup=True, sbadati=False)
        m.avanza(0.0)
        m.registra_qso(1.0, "DL3XY", nr=5)
        m.io_trasmetti([ct.Msg.TU], 1.0)
        m.annulla_trasmissione(2.0)
        chiusura = m.chiudi_contest()
        assert len(chiusura) == 1 and chiusura[0][1].nominativo == "DL3XY"
        assert m.chiudi_contest() == []

    def test_in_modo_singolo_nessuno_nasce_sopra_la_mia_voce(self):
        m = motore(pileup=False, sbadati=False)
        m.avanza(0.0)
        stazione = m.dx_attive()[0]
        m.io_trasmetti([ct.Msg.CQ], 0.0)
        stazione.oper.stato = ct.StatoOp.FATTO
        eventi = m.avanza(1.0).eventi
        assert any(e[0] == "nasce" for e in eventi)
        nuova = m.dx_attive()[0]
        assert nuova.stato == ct.Stato.COPIA
        assert nuova.scadenza is None

    def test_il_mio_scambio_ha_la_forma_delle_stazioni(self):
        m = motore()
        m.mio_nr = 7
        testo = m.testo_mio([ct.Msg.NR])
        assert testo.startswith("5NN")
        assert testo.removeprefix("5NN") in ("TT7", "OO7")
