# Prove automatiche di CWapu, il diario che resta sotto un tetto.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Fable 5.1, modalita' auto).
# Nate con la issue 14. Ogni prova lavora su un diario suo in una cartella
# temporanea: quello vero, con anni di esercizi, non si tocca mai.

import inspect
import os
import sys

import pytest

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)

import cwapu  # noqa: E402


def voce(numero, righe=6, terminatore="Fine del rapporto."):
    corpo = "".join(f"riga {i} della voce {numero}, con un po' di testo per fare peso\n" for i in range(righe))
    return f"\nEsercizio di ricezione #{numero} eseguito il 2026/09/17 alle 10:00 minuti:\n{corpo}{terminatore}\n"


def diario(quante, **altri):
    return "".join(voce(n, **altri) for n in range(1, quante + 1))


class TestTaglio:
    def test_sotto_il_tetto_non_si_tocca(self):
        testo = diario(3)
        assert cwapu.taglia_diario(testo, massimo=10_000) == (testo, 0)

    def test_sopra_il_tetto_se_ne_vanno_le_voci_piu_vecchie_intere(self):
        testo = diario(20)
        nuovo, tolte = cwapu.taglia_diario(testo, massimo=len(testo.encode("utf-8")) - 1)
        assert tolte >= 1
        assert nuovo.startswith("Esercizio di ricezione #")
        assert f"Esercizio di ricezione #{tolte + 1} " in nuovo
        assert f"Esercizio di ricezione #{tolte} " not in nuovo
        assert nuovo.endswith("Fine del rapporto.\n")

    def test_scende_un_dieci_per_cento_sotto_il_tetto(self):
        """Cosi' il taglio non si ripete a ogni esercizio."""
        testo = diario(50)
        tetto = len(testo.encode("utf-8")) - 1
        nuovo, _ = cwapu.taglia_diario(testo, massimo=tetto)
        assert len(nuovo.encode("utf-8")) <= tetto * 0.9

    def test_riconosce_le_voci_vecchie_con_gli_asterischi_e_quelle_inglesi(self):
        """Quindici voci uguali, cinque per terminatore: il taglio al 55 per cento cade dopo la nona, quindi resta una voce inglese."""
        testo = diario(5, terminatore="***") + diario(5, terminatore="End of report.") + diario(5)
        nuovo, tolte = cwapu.taglia_diario(testo, massimo=len(testo.encode("utf-8")) // 2)
        assert tolte == 9
        assert "End of report." in nuovo
        assert nuovo.startswith("Esercizio di ricezione #")

    def test_senza_terminatori_non_si_tocca_niente(self):
        """Meglio un diario sopra il tetto che uno spezzato a meta' voce."""
        testo = "".join(f"riga {i}\n" for i in range(200))
        assert cwapu.taglia_diario(testo, massimo=500) == (testo, 0)

    def test_l_ultima_voce_non_si_taglia_mai(self):
        """Era un rilievo della revisione: con la sola voce appena scritta a portare un terminatore, il taglio svuotava tutto il diario."""
        spazzatura = "".join(f"riga senza voce {i}\n" for i in range(100))
        ultima = voce(1)
        testo = spazzatura + ultima
        assert cwapu.taglia_diario(testo, massimo=300) == (testo, 0)

    def test_con_due_voci_resta_sempre_l_ultima(self):
        testo = voce(1, righe=40) + voce(2, righe=40)
        nuovo, tolte = cwapu.taglia_diario(testo, massimo=100)
        assert tolte == 1
        assert nuovo.startswith("Esercizio di ricezione #2 ")

    def test_le_terminazioni_di_riga_di_windows_non_cambiano_il_conto(self):
        testo = diario(20).replace("\n", "\r\n")
        nuovo, tolte = cwapu.taglia_diario(testo, massimo=len(testo.encode("utf-8")) - 1)
        assert tolte >= 1
        assert "\r\n" in nuovo
        assert nuovo.startswith("Esercizio di ricezione #")


class TestScrittura:
    def test_accoda_e_non_taglia_sotto_il_tetto(self, tmp_path, monkeypatch, capsys):
        percorso = tmp_path / "diario.txt"
        monkeypatch.setattr(cwapu, "DIARY_FILE", str(percorso))
        assert cwapu.scrivi_diario(voce(1)) == 0
        assert cwapu.scrivi_diario(voce(2)) == 0
        assert percorso.read_text(encoding="utf-8").count("Fine del rapporto.") == 2
        assert capsys.readouterr().out == ""

    def test_oltre_il_tetto_taglia_e_lo_dice(self, tmp_path, monkeypatch, capsys):
        percorso = tmp_path / "diario.txt"
        monkeypatch.setattr(cwapu, "DIARY_FILE", str(percorso))
        monkeypatch.setattr(cwapu, "DIARIO_MAX_BYTE", 3_000)
        tolte = 0
        for n in range(1, 30):
            tolte += cwapu.scrivi_diario(voce(n))
        assert tolte >= 1
        assert percorso.stat().st_size <= 3_000
        contenuto = percorso.read_text(encoding="utf-8")
        assert contenuto.lstrip().startswith("Esercizio di ricezione #")
        assert "Esercizio di ricezione #29 " in contenuto
        uscita = capsys.readouterr().out
        assert "Diario: tolte" in uscita
        assert "KB" in uscita

    def test_un_byte_non_utf8_non_fa_cadere_il_taglio(self, tmp_path, monkeypatch, capsys):
        """Era un rilievo della revisione: un diario ritoccato con un editor in ANSI faceva cadere il programma alla fine dell'esercizio."""
        percorso = tmp_path / "diario.txt"
        percorso.write_bytes((voce(1) + voce(2)).replace("voce", "vocè").encode("cp1252"))
        monkeypatch.setattr(cwapu, "DIARY_FILE", str(percorso))
        monkeypatch.setattr(cwapu, "DIARIO_MAX_BYTE", 100)
        assert cwapu.scrivi_diario(voce(3)) >= 1
        contenuto = percorso.read_text(encoding="utf-8")
        assert "Esercizio di ricezione #3 " in contenuto
        assert "Diario: tolte" in capsys.readouterr().out

    def test_il_taglio_non_lascia_mai_il_diario_a_meta(self, tmp_path, monkeypatch):
        """La riscrittura passa da un file di appoggio: se fallisce, il diario resta com'era."""
        percorso = tmp_path / "diario.txt"
        monkeypatch.setattr(cwapu, "DIARY_FILE", str(percorso))
        monkeypatch.setattr(cwapu, "DIARIO_MAX_BYTE", 100)
        cwapu.scrivi_diario(voce(1))
        prima = percorso.read_bytes()

        def replace_rotto(*a, **k):
            raise OSError("disco sparito")

        monkeypatch.setattr(cwapu.os, "replace", replace_rotto)
        with pytest.raises(OSError):
            cwapu.scrivi_diario(voce(2))
        # La voce 2 e' stata accodata prima del taglio, e il taglio fallito
        # non ha toccato il file: c'e' tutto quello che c'era, piu' la voce.
        dopo = percorso.read_bytes()
        assert dopo.startswith(prima)
        assert b"#2 " in dopo

    def test_un_diario_che_non_si_puo_scrivere_solleva_come_open(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cwapu, "DIARY_FILE", str(tmp_path / "cartella_che_non_esiste" / "diario.txt"))
        with pytest.raises(OSError):
            cwapu.scrivi_diario(voce(1))


class TestApertura:
    def test_cio_che_si_scrive_nel_blocco_finisce_nel_diario_alla_chiusura(self, tmp_path, monkeypatch):
        percorso = tmp_path / "diario.txt"
        monkeypatch.setattr(cwapu, "DIARY_FILE", str(percorso))
        with cwapu.apri_diario() as f:
            f.write("prima riga\n")
            assert not percorso.exists()
            f.write("Fine del rapporto.\n")
        assert percorso.read_text(encoding="utf-8") == "prima riga\nFine del rapporto.\n"

    def test_se_il_blocco_solleva_non_si_scrive_niente(self, tmp_path, monkeypatch):
        percorso = tmp_path / "diario.txt"
        monkeypatch.setattr(cwapu, "DIARY_FILE", str(percorso))
        with pytest.raises(ValueError), cwapu.apri_diario() as f:
            f.write("mezza voce\n")
            raise ValueError("qualcosa e' andato storto a meta'")
        assert not percorso.exists()

    def test_gli_esercizi_scrivono_solo_da_qui(self):
        """Il diario si scrive da un posto solo: nessun open diretto in aggiunta."""
        sorgente = inspect.getsource(cwapu)
        assert 'open(DIARY_FILE, "a"' in inspect.getsource(cwapu.scrivi_diario)
        assert sorgente.count('open(DIARY_FILE, "a"') == 1
        assert sorgente.count("with apri_diario() as f:") == 3
