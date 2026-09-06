# Prove automatiche di CWapu, il catalogo delle traduzioni.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' UltraCode).
# Il catalogo inglese e' rimasto per anni presente ma completamente vuoto, e
# nessuno se n'e' accorto: chi usava cwapu in inglese vedeva ogni singola
# stringa in italiano. Queste prove fanno in modo che non possa succedere di
# nuovo in silenzio. Se falliscono, si rigenera il catalogo:
#   pybabel extract -F babel.cfg -o messages.pot .
#   pybabel update -i messages.pot -d locales -l en --ignore-obsolete
#   (si traducono le voci nuove nel file .po)
#   pybabel compile -d locales

import os
import re
import sys

import pytest
from babel.messages.pofile import read_po

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)

PO = os.path.join(RADICE, "locales", "en", "LC_MESSAGES", "messages.po")
MO = os.path.join(RADICE, "locales", "en", "LC_MESSAGES", "messages.mo")
SEGNAPOSTO = re.compile(r"\{[^{}]*\}")


def catalogo():
    with open(PO, encoding="utf-8") as f:
        return read_po(f)


def voci():
    return [m for m in catalogo() if m.id]


def come_stringa(valore):
    return valore if isinstance(valore, str) else valore[0]


class TestCompletezza:
    def test_il_catalogo_inglese_esiste(self):
        assert os.path.exists(PO)
        assert os.path.exists(MO), "manca il .mo: serve pybabel compile -d locales"

    def test_non_e_vuoto(self):
        assert len(voci()) > 300

    def test_ogni_voce_e_tradotta(self):
        """Una voce senza traduzione ricade sul testo italiano, in silenzio."""
        senza = [come_stringa(m.id) for m in voci() if not m.string]
        assert senza == [], f"{len(senza)} voci senza traduzione, la prima e' {senza[:1]}"

    def test_nessuna_voce_e_marcata_incerta(self):
        """Le voci fuzzy nascono dall'accoppiamento automatico e vanno riviste
        a mano: gettext non le usa, quindi valgono come non tradotte."""
        incerte = [come_stringa(m.id) for m in voci() if m.fuzzy]
        assert incerte == [], f"voci da rivedere: {incerte[:3]}"


class TestCoerenza:
    def test_i_segnaposti_sono_gli_stessi(self):
        """Un segnaposto perso o rinominato nella traduzione fa saltare la
        format al momento di mostrare il messaggio, cioe' in faccia all'utente."""
        errori = []
        for messaggio in voci():
            originale, tradotto = come_stringa(messaggio.id), come_stringa(messaggio.string)
            attesi = sorted(s for s in SEGNAPOSTO.findall(originale) if s != "{}")
            ottenuti = sorted(s for s in SEGNAPOSTO.findall(tradotto) if s != "{}")
            anonimi_attesi = SEGNAPOSTO.findall(originale).count("{}")
            anonimi_ottenuti = SEGNAPOSTO.findall(tradotto).count("{}")
            if attesi != ottenuti or anonimi_attesi != anonimi_ottenuti:
                errori.append(originale[:60])
        assert errori == [], f"segnaposti discordi in: {errori}"

    def test_le_sequenze_di_controllo_sono_le_stesse(self):
        """Un a capo o una tabulazione persi cambiano l'impaginazione a schermo."""
        errori = []
        for messaggio in voci():
            originale, tradotto = come_stringa(messaggio.id), come_stringa(messaggio.string)
            for sequenza in ("\n", "\t"):
                if originale.count(sequenza) != tradotto.count(sequenza):
                    errori.append((originale[:50], sequenza))
        assert errori == [], f"sequenze discordi in: {errori[:3]}"

    def test_il_mo_non_e_piu_vecchio_del_po(self):
        """Un .mo non ricompilato mostra la traduzione di ieri."""
        assert os.path.getmtime(MO) >= os.path.getmtime(PO), "serve pybabel compile -d locales"


def estrai_dal_codice():
    """Rilegge le stringhe direttamente dai sorgenti, non dal .pot.

    Confrontare il catalogo con messages.pot non serviva a niente: sono due
    file generati, e se non si rigenerano invecchiano insieme, lasciando
    passare le stringhe nuove senza che nessuna prova se ne accorga.
    """
    from babel.messages.extract import extract_from_dir
    from babel.messages.frontend import parse_mapping_cfg

    with open(os.path.join(RADICE, "babel.cfg"), encoding="utf-8") as f:
        metodo, opzioni = parse_mapping_cfg(f)
    trovate = set()
    for _percorso, _riga, messaggio, _commenti, _contesto in extract_from_dir(RADICE, metodo, opzioni):
        if isinstance(messaggio, str):
            trovate.add(messaggio)
        elif messaggio and isinstance(messaggio[0], str):
            trovate.add(messaggio[0])
    return trovate


class TestAllineamentoAlCodice:
    def test_ogni_stringa_del_codice_sta_nel_catalogo(self):
        """Se il codice guadagna una stringa e il catalogo no, quella frase
        resta in italiano anche per chi usa cwapu in inglese."""
        nel_codice = estrai_dal_codice()
        nel_catalogo = {come_stringa(m.id) for m in voci()}
        mancanti = sorted(nel_codice - nel_catalogo)
        assert mancanti == [], f"{len(mancanti)} stringhe nuove da tradurre, la prima e' {mancanti[:1]}"

    def test_il_catalogo_non_porta_stringhe_che_il_codice_non_ha_piu(self):
        """Voci rimaste indietro fanno credere che ci sia da tradurre
        qualcosa che nessuno vedra' mai."""
        nel_codice = estrai_dal_codice()
        nel_catalogo = {come_stringa(m.id) for m in voci()}
        avanzate = sorted(nel_catalogo - nel_codice)
        assert avanzate == [], f"{len(avanzate)} voci non piu' nel codice, la prima e' {avanzate[:1]}"

    def test_il_modello_pot_e_aggiornato(self):
        """Il .pot e' il punto di partenza per ogni lingua futura."""
        pot = os.path.join(RADICE, "messages.pot")
        if not os.path.exists(pot):
            pytest.skip("messages.pot non presente")
        with open(pot, encoding="utf-8") as f:
            modello = read_po(f)
        nel_modello = {come_stringa(m.id) for m in modello if m.id}
        assert estrai_dal_codice() - nel_modello == set(), "serve pybabel extract"


class TestTraduzioneViva:
    def test_gettext_restituisce_davvero_l_inglese(self):
        """La prova che conta: non il file, ma cio' che l'utente leggerebbe."""
        import gettext

        traduzione = gettext.translation("messages", localedir=os.path.join(RADICE, "locales"), languages=["en"])
        assert traduzione.gettext("Esercizio di ricezione") == "Receiving exercise"
        assert traduzione.gettext("Superato!") == "Passed!"
        assert traduzione.gettext("Lunedì") == "Monday"

    def test_le_chiavi_degli_switcher_restano_in_italiano(self):
        """key_state non passa dalla traduzione, e non deve passarci mai: e' la
        chiave con cui lo stato viene salvato nel file delle impostazioni."""
        import cwapu

        salvate = set(cwapu.DEFAULT_DATA["rx_menu_switcher_states"])
        for voce in cwapu.RX_SWITCHER_ITEMS:
            assert voce["key_state"] in salvate
