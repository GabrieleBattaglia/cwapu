# CWapu, intervallo di confidenza di Wilson.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' UltraCode).
# 06/09/2026: estratto da timeline.py per non pagare pandas e numpy a ogni avvio.

"""Limiti dell'intervallo di Wilson per una proporzione.

Sta in un modulo suo perche' cwapu lo usa durante ogni esercizio, mentre
timeline serve soltanto quando si aprono le statistiche: tenere le due cose
insieme costringeva a caricare pandas e numpy anche a chi non li usa mai.
Qui basta math.
"""

import math

Z_95 = 1.96  # Valore z per una confidenza del 95 per cento


def _dentro_zero_uno(valore):
    """Riporta il risultato dentro l'intervallo che una proporzione puo' avere.

    Serve contro l'errore della virgola mobile: con tutti gli invii sbagliati
    il limite superiore esce a 1.0000000000000002, che moltiplicato per cento
    e stampato non si vede, ma rompe qualunque confronto con uno.
    """
    return max(0.0, min(1.0, valore))


def wilson_score_upper_bound(errori, invii, confidenza=0.95):
    """Limite superiore dell'intervallo di Wilson per il tasso di errore.

    Con zero invii restituisce 1.0, cioe' il caso peggiore: non sappiamo
    niente, quindi non escludiamo niente.
    """
    if invii == 0:
        return 1.0
    errori = min(errori, invii)
    z = Z_95
    p_hat = errori / invii
    divisore = 1 + z**2 / invii
    numeratore = p_hat + z**2 / (2 * invii) + z * math.sqrt((p_hat * (1 - p_hat) + z**2 / (4 * invii)) / invii)
    return _dentro_zero_uno(numeratore / divisore)


def wilson_score_lower_bound(errori, invii, confidenza=0.95):
    """Limite inferiore dell'intervallo di Wilson per il tasso di errore.

    Con zero invii restituisce 0, per lo stesso motivo detto sopra.
    """
    if invii == 0:
        return 0
    errori = min(errori, invii)
    z = Z_95
    p_hat = errori / invii
    divisore = 1 + z**2 / invii
    numeratore = p_hat + z**2 / (2 * invii) - z * math.sqrt((p_hat * (1 - p_hat) + z**2 / (4 * invii)) / invii)
    return _dentro_zero_uno(numeratore / divisore)
