# Calcola statistiche basate su cwapu_settings.json creato da cwapu.
# Creato in data giovedì 10 luglio 2025 da Gabriele Battaglia e Gemini 2.5 Pro
import json, math
import numpy as np
import pandas as pd
from collections import Counter

def wilson_score_upper_bound(errori, invii, confidenza=0.95):
    """
    Calcola il limite superiore dell'intervallo di confidenza di Wilson.
    """
    if invii == 0:
        return 1.0 # Il caso peggiore
    z = 1.96 # Valore Z per una confidenza del 95%
    p_hat = errori / invii
    
    # Formula del limite superiore
    divisor = 1 + z**2 / invii
    numeratore = p_hat + z**2 / (2 * invii) + z * math.sqrt((p_hat * (1 - p_hat) + z**2 / (4 * invii)) / invii)
    
    return numeratore / divisor

def wilson_score_lower_bound(errori, invii, confidenza=0.95):
    """
    Calcola il limite inferiore dell'intervallo di confidenza di Wilson per un tasso di errore.
    """
    if invii == 0:
        return 0
    z = 1.96 # Valore Z per una confidenza del 95%
    p_hat = errori / invii
    # Formula del limite inferiore dell'intervallo di Wilson
    divisor = 1 + z**2 / invii
    numeratore = p_hat + z**2 / (2 * invii) - z * math.sqrt((p_hat * (1 - p_hat) + z**2 / (4 * invii)) / invii)
    return numeratore / divisor

def _formatta_durata(secondi, _):
    """Formatta i secondi in 'X ore, Y minuti e Z secondi'."""
    secondi = int(secondi)
    if secondi == 0:
        return _("0 secondi")
    ore = secondi // 3600
    minuti = (secondi % 3600) // 60
    sec_rimanenti = secondi % 60
    parti = []
    if ore > 0:
        parti.append(_("{} ore").format(ore))
    if minuti > 0:
        parti.append(_("{} minuti").format(minuti))
    if sec_rimanenti > 0:
        parti.append(_("{} secondi").format(sec_rimanenti))
    return ", ".join(parti)

def genera_report_attivita(df: pd.DataFrame, _, lang, giorni ,mesi) -> str:
    """
    Analizza la distribuzione temporale delle sessioni e genera un report testuale.
    """
    report_lines = []
    total_sessions = len(df)
    if df.empty:
        return _('Nessun dato da analizzare.')
    report_lines.append(_('--- Riepilogo Attività ---'))
    prima_sessione = df['timestamp_iso'].min()
    ultima_sessione = df['timestamp_iso'].max()
    giorni_coperti = (ultima_sessione - prima_sessione).days
    prima_sessione_str = f"{giorni[prima_sessione.weekday()]} {prima_sessione.day} {mesi[prima_sessione.month]} {prima_sessione.year}, {prima_sessione.strftime('%H:%M')}"
    ultima_sessione_str = f"{giorni[ultima_sessione.weekday()]} {ultima_sessione.day} {mesi[ultima_sessione.month]} {ultima_sessione.year}, {ultima_sessione.strftime('%H:%M')}"
    report_lines.append(_('Numero totale di sessioni: {}').format(total_sessions))
    report_lines.append(_('Prima sessione: {}').format(prima_sessione_str))
    report_lines.append(_('Ultima sessione: {}').format(ultima_sessione_str))
    report_lines.append(_('Periodo coperto: {} giorni').format(giorni_coperti))
    report_lines.append('-' * 25)
    report_lines.append(_('\n--- Distribuzione Oraria delle Sessioni ---'))
    hourly_stats = df.groupby(df['timestamp_iso'].dt.hour).agg(
        count=('timestamp_iso', 'size'),
        total_duration=('duration_seconds', 'sum')
    )
    piu_intensa_ora = hourly_stats['total_duration'].idxmax()
    for hour, stats in hourly_stats.sort_values(by='total_duration', ascending=False).iterrows():
        percentage = (stats['count'] / total_sessions) * 100
        durata_str = _formatta_durata(stats['total_duration'], _)
        report_lines.append(_("   - Fascia oraria {start_hour:02d} - {end_hour:02d}: {count} sessioni ({percentage:.2f}%), durata {durata}").format(
            start_hour=hour, end_hour=hour + 1, count=int(stats['count']), percentage=percentage, durata=durata_str))
    report_lines.append(_("Picco di attività orario: {hour:02d}:00.").format(hour=piu_intensa_ora))
    report_lines.append('-' * 25)
    report_lines.append(_('\n--- Distribuzione Settimanale ---'))
    weekly_stats = df.groupby(df['timestamp_iso'].dt.dayofweek).agg(
        count=('timestamp_iso', 'size'),
        total_duration=('duration_seconds', 'sum')
    )
    piu_intenso_giorno_idx = weekly_stats['total_duration'].idxmax()
    for day_idx, stats in weekly_stats.sort_values(by='total_duration', ascending=False).iterrows():
        percentage = (stats['count'] / total_sessions) * 100
        durata_str = _formatta_durata(stats['total_duration'], _)
        report_lines.append(_("   - {giorno}: {count} sessioni ({percentage:.2f}%), durata {durata}").format(
            giorno=giorni[day_idx], count=int(stats['count']), percentage=percentage, durata=durata_str))
    report_lines.append(_('Picco di attività settimanale: {}.').format(giorni[int(piu_intenso_giorno_idx)]))
    report_lines.append('-' * 25)
    report_lines.append(_('\n--- Distribuzione Mensile ---'))
    monthly_stats = df.groupby(df['timestamp_iso'].dt.month).agg(
        count=('timestamp_iso', 'size'),
        total_duration=('duration_seconds', 'sum')
    )
    piu_intenso_mese_idx = monthly_stats['total_duration'].idxmax()
    for month_idx, stats in monthly_stats.sort_values(by='total_duration', ascending=False).iterrows():
        percentage = (stats['count'] / total_sessions) * 100
        durata_str = _formatta_durata(stats['total_duration'], _)
        report_lines.append(_("   - {mese}: {count} sessioni ({percentage:.2f}%), durata {durata}").format(
            mese=mesi[month_idx], count=int(stats['count']), percentage=percentage, durata=durata_str))
    report_lines.append(_('Picco di attività mensile: {}.').format(mesi[int(piu_intenso_mese_idx)]))
    report_lines.append(_('\n--- Distribuzione Stagionale ---'))
    stagioni_map = {
        12: _('Inverno'), 1: _('Inverno'), 2: _('Inverno'),
        3: _('Primavera'), 4: _('Primavera'), 5: _('Primavera'),
        6: _('Estate'), 7: _('Estate'), 8: _('Estate'),
        9: _('Autunno'), 10: _('Autunno'), 11: _('Autunno')
    }
    # Usiamo una copia per non modificare il DataFrame originale che potrebbe essere usato da altre funzioni
    df_copy = df.copy()
    df_copy['stagione'] = df_copy['timestamp_iso'].dt.month.map(stagioni_map)
    seasonal_stats = df_copy.groupby('stagione').agg(
        count=('timestamp_iso', 'size'),
        total_duration=('duration_seconds', 'sum')
    )
    for stagione, stats in seasonal_stats.sort_values(by='total_duration', ascending=False).iterrows():
        percentage = (stats['count'] / total_sessions) * 100
        durata_str = _formatta_durata(stats['total_duration'], _)
        report_lines.append(_("   - {stagione}: {count} sessioni ({percentage:.2f}%), durata {durata}").format(
            stagione=stagione, count=int(stats['count']), percentage=percentage, durata=durata_str))
    return '\n'.join(report_lines)

def genera_report_performance(df: pd.DataFrame, _, lang) -> str:
    """
    Analizza l'andamento della velocità (WPM) e degli errori sui caratteri.
    """
    if df.empty:
        return _('Nessun dato di performance da analizzare.')
        
    report_lines = []
    total_sessions = len(df)
    meta_sessioni = total_sessions // 2
    prima_meta_df = df.iloc[:meta_sessioni]
    seconda_meta_df = df.iloc[meta_sessioni:]
    report_lines.append(_('\n--- Analisi della Performance: Velocità (WPM) ---'))
    all_item_wpms = []
    if 'item_details' in df.columns:
        for session_details in df['item_details'].dropna():
            all_item_wpms.extend([item['wpm'] for item in session_details])
            
    if all_item_wpms:
        velocita_media_reale = np.mean(all_item_wpms)
        dev_std_reale = np.std(all_item_wpms)
        report_lines.append(_('Velocità media reale: {:.2f} WPM.').format(velocita_media_reale))
        report_lines.append(_('Consistenza WPM reale (dev. std): {:.2f}.').format(dev_std_reale))
    else:
        velocita_media_totale = df['wpm_avg'].mean()
        # MODIFICA: Aggiunta la chiamata a .format() che mancava.
        report_lines.append(_('Velocità media complessiva: {:.2f} WPM.').format(wpm=velocita_media_totale))
    
    report_lines.append('-' * 25)
    report_lines.append(_('\n--- Analisi degli Errori sui Caratteri ---'))
    stat_caratteri = []
    for u4, sessione in df.iterrows():
        caratteri_inviati = sessione.get('sent_chars_detail_session', {})
        errori_dettaglio = sessione.get('errors_detail_session', {})
        tutti_caratteri = set(caratteri_inviati.keys()) | set(errori_dettaglio.keys())
        for char in tutti_caratteri:
            stat_caratteri.append({'carattere': char, 'inviati': caratteri_inviati.get(char, 0), 'errori': errori_dettaglio.get(char, 0)})
    if not stat_caratteri:
         report_lines.append(_("Nessun dato dettagliato sui caratteri per un'analisi."))
    else:
        char_df = pd.DataFrame(stat_caratteri).groupby('carattere').sum()
        char_df['tasso_errore'] = np.where(char_df['inviati'] > 0, char_df['errori'] / char_df['inviati'] * 100, 0)
        char_df['punteggio_critico'] = char_df.apply(
            lambda row: wilson_score_lower_bound(row['errori'], row['inviati']),
            axis=1
        )
        char_df['punteggio_accuratezza'] = char_df.apply(
            lambda row: wilson_score_upper_bound(row['errori'], row['inviati']),
            axis=1
        )
        char_df_filtrato = char_df[char_df['inviati'] >= 20]
        if char_df_filtrato.empty:
            report_lines.append(_("Nessun carattere ha dati sufficienti per un'analisi dettagliata."))
        else:
            caratteri_critici = char_df_filtrato.sort_values(by='punteggio_critico', ascending=False).head(10)
            report_lines.append(_('Primi 10 caratteri critici (per tasso di errore):'))
            for char, row in caratteri_critici.iterrows():
                report_lines.append(_("   - Carattere '{}': Tasso errore {:.2f}% ({} errori su {} invii)").format(char, row['tasso_errore'], int(row['errori']), int(row['inviati'])))
            if not caratteri_critici.empty:
                char_piu_critico = caratteri_critici.index[0]
                report_lines.append(_("\nApprofondimento sull'evoluzione del carattere '{}':").format(char_piu_critico))
                errori_prima_meta = 0
                inviati_prima_meta = 0
                for u2, sessione in prima_meta_df.iterrows():
                    errori_prima_meta += sessione.get('errors_detail_session', {}).get(char_piu_critico, 0)
                    inviati_prima_meta += sessione.get('sent_chars_detail_session', {}).get(char_piu_critico, 0)
                errori_seconda_meta = 0
                inviati_seconda_meta = 0
                for u3, sessione in seconda_meta_df.iterrows():
                    errori_seconda_meta += sessione.get('errors_detail_session', {}).get(char_piu_critico, 0)
                    inviati_seconda_meta += sessione.get('sent_chars_detail_session', {}).get(char_piu_critico, 0)
                tasso_err_prima = np.where(inviati_prima_meta > 0, (errori_prima_meta / inviati_prima_meta) * 100, 0)
                tasso_err_seconda = np.where(inviati_seconda_meta > 0, (errori_seconda_meta / inviati_seconda_meta) * 100, 0)
                if tasso_err_seconda < tasso_err_prima:
                    tendenza_char = _('miglioramento')
                else:
                    tendenza_char = _('peggioramento o stabile')
                report_lines.append(_("Tasso errore prima metà: {:.2f}%.").format(tasso_err_prima))
                report_lines.append(_("Tasso errore seconda metà: {:.2f}%.").format(tasso_err_seconda))
                report_lines.append(_("Tendenza per '{}': {}.").format(char_piu_critico, tendenza_char))
            caratteri_accurati = char_df_filtrato.sort_values(by='punteggio_accuratezza', ascending=True).head(10)
            report_lines.append(_('\nPrimi 10 caratteri più accurati (tra quelli più praticati):'))
            for char, row in caratteri_accurati.iterrows():
                report_lines.append(_("   - Carattere '{}': Tasso errore {:.2f}% ({} errori su {} invii)").format(char, row['tasso_errore'], int(row['errori']), int(row['inviati'])))
    return '\n'.join(report_lines)

def genera_report_velocita_avanzato(df: pd.DataFrame, _, lang) -> str:
    """
    Calcola e riporta statistiche avanzate sulla velocità (WPM) usando solo Pandas e NumPy.
    """
    if df.empty or 'wpm_avg' not in df.columns:
        return ""

    report_lines = []
    report_lines.append(_('--- Analisi Avanzata della Velocità (WPM) ---'))
    
    wpm_series = df['wpm_avg'].dropna()
    if wpm_series.empty:
        report_lines.append(_("Nessun dato sulla velocità media disponibile per l'analisi."))
        return '\n'.join(report_lines)

    # Calcolo delle medie
    mean_aritmetica = wpm_series.mean()
    mean_quadratica = np.sqrt(np.mean(wpm_series**2))
    mean_ponderata = np.average(wpm_series, weights=df.loc[wpm_series.index, 'duration_seconds'])
    
    report_lines.append(_('\nProspettive sulla Velocità Media:'))
    report_lines.append(_("  - Media Aritmetica: {:.2f} WPM (il valore 'classico')").format(mean_aritmetica))
    report_lines.append(_("  - Media Ponderata (per durata): {:.2f} WPM (dà più peso alle sessioni lunghe)").format(mean_ponderata))
    report_lines.append(_("  - Media Quadratica (RMS): {:.2f} WPM (dà più peso alle velocità più alte)").format(mean_quadratica))

    # MODIFICA: Calcolo di moda e dispersione usando solo Pandas/NumPy
    moda_series = wpm_series.round().mode()
    # .mode() di Pandas restituisce una Serie; prendiamo il primo valore se esiste.
    moda_wpm = moda_series[0] if not moda_series.empty else np.nan 
    
    q1 = wpm_series.quantile(0.25)
    q3 = wpm_series.quantile(0.75)
    iqr = q3 - q1

    report_lines.append(_('\nFrequenza e Consistenza:'))
    if pd.notna(moda_wpm):
        report_lines.append(_("  - Moda (velocità più frequente): {:.0f} WPM").format(moda_wpm))
        
    report_lines.append(_("  - Dispersione (Range Interquartile): {:.2f} WPM (un valore basso indica grande consistenza)").format(iqr))
    report_lines.append(_("     (Il 50% delle tue sessioni ha una velocità media tra {:.2f} e {:.2f} WPM)").format(q1, q3))
    # Calcolo media ultime 12 settimane
    data_fine = pd.Timestamp('2025-07-12 19:12:12') 
    data_inizio = data_fine - pd.DateOffset(weeks=12)
    df_ultime_12_settimane = df[df['timestamp_iso'] >= data_inizio]
    
    if not df_ultime_12_settimane.empty:
        media_12_settimane = df_ultime_12_settimane['wpm_avg'].mean()
        report_lines.append(_('\nTrend Recente:'))
        report_lines.append(_("  - Velocità media nelle ultime 12 settimane: {:.2f} WPM").format(media_12_settimane))

    return '\n'.join(report_lines)

def genera_report_avanzato(df: pd.DataFrame, _, lang, giorni, mesi) -> str:
    """
    Calcola statistiche avanzate e genera un report.
    """
    if df.empty:
        return _("Nessun dato per l'analisi avanzata.")
    report_lines = []
    total_sessions = len(df)
    report_lines.append(_('\n--- Analisi Avanzata ---'))
    df['accuracy'] = np.where(df['items_sent_session'] > 0, (df['items_correct_session'] / df['items_sent_session']) * 100, 0)
    accuratezza_media = df['accuracy'].mean()
    report_lines.append(_("Accuratezza media complessiva: {:.2f}%.").format(accuratezza_media))
    meta_sessioni = total_sessions // 2
    prima_meta_df = df.iloc[:meta_sessioni]
    seconda_meta_df = df.iloc[meta_sessioni:]
    if not prima_meta_df.empty and not seconda_meta_df.empty:
        acc_prima_meta = prima_meta_df['accuracy'].mean()
        acc_seconda_meta = seconda_meta_df['accuracy'].mean()
        tendenza_acc = _('miglioramento') if acc_seconda_meta > acc_prima_meta else _('peggioramento')
        report_lines.append(_("Andamento accuratezza: da {:.2f}% (prima metà) a {:.2f}% (seconda metà). Tendenza: {}.").format(acc_prima_meta, acc_seconda_meta, tendenza_acc))
    report_lines.append('-' * 25)
    report_lines.append(_('\n--- Correlazione Velocità-Accuratezza ---'))
    all_item_details = []
    if 'item_details' in df.columns:
        for session_details in df['item_details'].dropna():
            all_item_details.extend(session_details)
    if all_item_details:
        item_df = pd.DataFrame(all_item_details)
        item_df['correct_numeric'] = item_df['correct'].astype(int)
        correlazione = item_df['wpm'].corr(item_df['correct_numeric'])
        interpretazione = ''
        if pd.isna(correlazione):
            interpretazione = _('Dati insufficienti per calcolare la correlazione.')
        elif correlazione < -0.2:
            interpretazione = _('Correlazione negativa debole: la velocità tende a diminuire quando l_accuratezza aumenta.')
        elif correlazione > 0.2:
            interpretazione = _('Correlazione positiva debole: la velocità tende ad aumentare con l_accuratezza.')
        else:
            interpretazione = _('Nessuna correlazione significativa tra velocità e accuratezza.')
        report_lines.append(_("Coefficiente di correlazione: {:.2f}.").format(correlazione))
        report_lines.append(_('Interpretazione: {}').format(interpretazione))
    else:
        report_lines.append(_('Granularità dei dati insufficiente per stabilire una correlazione.'))
    report_lines.append('-' * 25)
    report_lines.append(_('\n--- Analisi Durata Sessioni ---'))
    idx_min = df['duration_seconds'].idxmin()
    sessione_corta = df.loc[idx_min]
    durata_corta_sec = sessione_corta['duration_seconds']
    idx_max = df['duration_seconds'].idxmax()
    sessione_lunga = df.loc[idx_max]
    durata_lunga_sec = sessione_lunga['duration_seconds']
    durata_media_sec = df['duration_seconds'].mean()
    durata_media_str = _formatta_durata(durata_media_sec, _)
    durata_corta_str = _formatta_durata(durata_corta_sec, _)
    data_corta_str = f"{giorni[sessione_corta['timestamp_iso'].weekday()]} {sessione_corta['timestamp_iso'].day} {mesi[sessione_corta['timestamp_iso'].month]} {sessione_corta['timestamp_iso'].year}"
    durata_lunga_str = _formatta_durata(durata_lunga_sec, _)
    data_lunga_str = f"{giorni[sessione_lunga['timestamp_iso'].weekday()]} {sessione_lunga['timestamp_iso'].day} {mesi[sessione_lunga['timestamp_iso'].month]} {sessione_lunga['timestamp_iso'].year}"
    report_lines.append(_('Durata media di una sessione: {}').format(durata_media_str))
    report_lines.append(_('Sessione più corta: {} ({}).').format(durata_corta_str, data_corta_str))
    report_lines.append(_('Sessione più lunga: {} ({}).').format(durata_lunga_str, data_lunga_str))
    report_lines.append(_('\n--- Distribuzione Tempo Totale di Allenamento ---'))
    durata_per_ora = df.groupby(df['timestamp_iso'].dt.hour)['duration_seconds'].sum()
    ora_piu_dedizione = durata_per_ora.idxmax()
    tempo_ora_sec = durata_per_ora.max()
    report_lines.append(_("Ora di maggiore dedizione: {:02d}:00, con un totale di {} min e {} sec di pratica.").format(ora_piu_dedizione, int(tempo_ora_sec // 60), int(tempo_ora_sec % 60)))
    durata_per_giorno = df.groupby(df['timestamp_iso'].dt.dayofweek)['duration_seconds'].sum()
    giorno_piu_dedizione_idx = durata_per_giorno.idxmax()
    tempo_giorno_sec = durata_per_giorno.max()
    report_lines.append(_('Giorno di maggiore dedizione: {}, con un totale di {} min e {} sec di pratica.').format(giorni[int(giorno_piu_dedizione_idx)], int(tempo_giorno_sec // 60), int(tempo_giorno_sec % 60)))
    report_lines.append(_('\n--- Analisi Granulare Velocità/Accuratezza ---'))
    if not all_item_details:
        report_lines.append(_('Dati granulari non presenti.'))
    else:
        correct_items = [item for item in all_item_details if item['correct']]
        wrong_items = [item for item in all_item_details if not item['correct']]
        avg_wpm_correct = np.mean([item['wpm'] for item in correct_items]) if correct_items else 0
        avg_wpm_wrong = np.mean([item['wpm'] for item in wrong_items]) if wrong_items else 0
        report_lines.append(_('Media WPM su item corretti: {:.2f}').format(avg_wpm_correct))
        report_lines.append(_('Media WPM su item errati: {:.2f}').format(avg_wpm_wrong))
        if avg_wpm_correct > avg_wpm_wrong and wrong_items:
            report_lines.append(_("Conclusione: all'aumentare della velocità di ricezione, aumenta anche l'accuratezza."))
        elif avg_wpm_wrong > avg_wpm_correct and correct_items:
            report_lines.append(_("Conclusione: al diminuire della velocità di ricezione, aumenta l'accuratezza."))
    return '\n'.join(report_lines)

def genera_report_confronto_settimanale(df: pd.DataFrame, _, lang) -> str:
    """
    Analizza e confronta le performance tra giorni feriali e weekend.

    Args:
        df (pd.DataFrame): Il DataFrame con i dati delle sessioni.
        _ (function): Funzione di traduzione gettext.
        lang (str): Codice della lingua.

    Returns:
        str: Una stringa contenente il report di confronto formattato.
    """
    report_lines = []
    report_lines.append(_('\n--- Confronto Feriali vs. Weekend ---'))

    # Helper per formattare la durata in ore e minuti
    def formatta_durata(secondi):
        if secondi == 0:
            return _("0 minuti")
        ore = int(secondi // 3600)
        minuti = int((secondi % 3600) // 60)
        if ore > 0:
            return _("{} ore e {} minuti").format(ore, minuti)
        return _("{} minuti").format(minuti)

    # Calcola l'accuratezza per ogni sessione
    df['accuracy'] = np.where(df['items_sent_session'] > 0, 
                              (df['items_correct_session'] / df['items_sent_session']) * 100, 
                              0)

    # Separa i dati in feriali (0=Lunedì, 4=Venerdì) e weekend (5=Sabato, 6=Domenica)
    df_feriale = df[df['timestamp_iso'].dt.dayofweek < 5].copy()
    df_weekend = df[df['timestamp_iso'].dt.dayofweek >= 5].copy()

    # Analisi Giorni Feriali
    if not df_feriale.empty:
        wpm_feriale = df_feriale['wpm_avg'].mean()
        acc_feriale = df_feriale['accuracy'].mean()
        tempo_feriale_sec = df_feriale['duration_seconds'].sum()
        sessioni_feriale = len(df_feriale)
        
        report_lines.append(_('\nGiorni Feriali (Lun-Ven):'))
        report_lines.append(_("  - Sessioni totali: {}").format(sessioni_feriale))
        report_lines.append(_("  - WPM medio: {:.2f}").format(wpm_feriale))
        report_lines.append(_("  - Accuratezza media: {:.2f}%").format(acc_feriale))
        report_lines.append(_("  - Tempo totale di pratica: {}").format(formatta_durata(tempo_feriale_sec)))
    else:
        report_lines.append(_('\nNessuna sessione registrata nei giorni feriali.'))

    # Analisi Weekend
    if not df_weekend.empty:
        wpm_weekend = df_weekend['wpm_avg'].mean()
        acc_weekend = df_weekend['accuracy'].mean()
        tempo_weekend_sec = df_weekend['duration_seconds'].sum()
        sessioni_weekend = len(df_weekend)
        report_lines.append(_('\nWeekend (Sab-Dom):'))
        report_lines.append(_("  - Sessioni totali: {}").format(sessioni_weekend))
        report_lines.append(_("  - WPM medio: {:.2f}").format(wpm_weekend))
        report_lines.append(_("  - Accuratezza media: {:.2f}%").format(acc_weekend))
        report_lines.append(_("  - Tempo totale di pratica: {}").format(formatta_durata(tempo_weekend_sec)))
    else:
        report_lines.append(_('\nNessuna sessione registrata nel weekend.'))
    # Conclusione finale basata sui dati
    if not df_feriale.empty and not df_weekend.empty:
        giorni_feriali_unici = df_feriale['timestamp_iso'].dt.date.nunique() if not df_feriale.empty else 0
        giorni_weekend_unici = df_weekend['timestamp_iso'].dt.date.nunique() if not df_weekend.empty else 0
        media_giornaliera_feriale = (tempo_feriale_sec / giorni_feriali_unici) if giorni_feriali_unici > 0 else 0
        media_giornaliera_weekend = (tempo_weekend_sec / giorni_weekend_unici) if giorni_weekend_unici > 0 else 0
        report_lines.append(_('\nConclusione:'))
        conclusione = ""
        if media_giornaliera_feriale > media_giornaliera_weekend:
            conclusione += _("In media, tendi a praticare di più nei singoli giorni feriali che in quelli del weekend. ")
        elif media_giornaliera_weekend > media_giornaliera_feriale:
            conclusione += _("In media, tendi a dedicare più tempo alla pratica nei singoli giorni del weekend che in quelli feriali. ")
        if wpm_weekend > wpm_feriale:
            conclusione += _("Nel weekend la tua velocità media è maggiore. ")
        else:
            conclusione += _("Durante la settimana la tua velocità media è maggiore. ")
        if acc_weekend > acc_feriale:
            conclusione += _("La tua accuratezza è più alta nel weekend.")
        else:
            conclusione += _("La tua accuratezza è più alta nei giorni feriali.")
        report_lines.append(conclusione)
    return '\n'.join(report_lines)

def genera_report_stagionale(df: pd.DataFrame, _, lang) -> str:
    """
    Analizza i picchi di WPM e accuratezza per ogni stagione.

    Args:
        df (pd.DataFrame): Il DataFrame con i dati delle sessioni.
        _ (function): Funzione di traduzione gettext.
        lang (str): Codice della lingua.

    Returns:
        str: Una stringa contenente il report stagionale.
    """
    report_lines = []
    report_lines.append(_('\n--- Performance di Picco per Stagione ---'))

    # Mappatura dei mesi alle stagioni
    stagioni_map = {
        12: _('Inverno'), 1: _('Inverno'), 2: _('Inverno'),
        3: _('Primavera'), 4: _('Primavera'), 5: _('Primavera'),
        6: _('Estate'), 7: _('Estate'), 8: _('Estate'),
        9: _('Autunno'), 10: _('Autunno'), 11: _('Autunno')
    }
    
    # Crea una colonna 'stagione' nel DataFrame
    df_copy = df.copy()
    df_copy['stagione'] = df_copy['timestamp_iso'].dt.month.map(stagioni_map)

    # Calcola l'accuratezza se non è già presente
    if 'accuracy' not in df_copy.columns:
        df_copy['accuracy'] = np.where(df_copy['items_sent_session'] > 0, 
                                       (df_copy['items_correct_session'] / df_copy['items_sent_session']) * 100, 
                                       0)

    # Raggruppa per stagione e calcola i valori massimi
    stat_stagionali = df_copy.groupby('stagione').agg(
        picco_wpm=('wpm_max', 'max'),
        picco_accuratezza=('accuracy', 'max')
    )

    # Ordine desiderato per la visualizzazione
    ordine_stagioni = [_('Primavera'), _('Estate'), _('Autunno'), _('Inverno')]

    for stagione in ordine_stagioni:
        if stagione in stat_stagionali.index:
            wpm = stat_stagionali.loc[stagione, 'picco_wpm']
            acc = stat_stagionali.loc[stagione, 'picco_accuratezza']
            report_lines.append(_("  - {}: Picco WPM {:.0f}, Picco Accuratezza {:.2f}%").format(stagione, wpm, acc))
        else:
            report_lines.append(_("  - {}: Nessun dato disponibile.").format(stagione))
            
    # Aggiunge una conclusione finale
    if not stat_stagionali.empty:
        report_lines.append(_('\nConclusione:'))
        stagione_top_wpm = stat_stagionali['picco_wpm'].idxmax()
        stagione_top_acc = stat_stagionali['picco_accuratezza'].idxmax()
        
        if stagione_top_wpm == stagione_top_acc:
            report_lines.append(_("Hai raggiunto i tuoi picchi sia di velocità ({:.0f} WPM) che di accuratezza ({:.2f}%) durante la stagione: {}.").format(
                stat_stagionali['picco_wpm'].max(), 
                stat_stagionali['picco_accuratezza'].max(), 
                stagione_top_wpm
            ))
        else:
            report_lines.append(_("La tua velocità di punta ({:.0f} WPM) è stata registrata in {}, mentre hai raggiunto la massima accuratezza ({:.2f}%) in {}.").format(
                stat_stagionali['picco_wpm'].max(), 
                stagione_top_wpm, 
                stat_stagionali['picco_accuratezza'].max(), 
                stagione_top_acc
            ))

    return '\n'.join(report_lines)

def genera_report_temporale_completo(dati_sessioni, _, lang) -> str:
    """
    Funzione direttore che orchestra tutte le analisi e assembla il report finale.
    """
    if not dati_sessioni:
        return _('Attenzione: nessun dato di log disponibile da analizzare.')
    df = pd.DataFrame(dati_sessioni)
    df['timestamp_iso'] = pd.to_datetime(df['timestamp_iso'])
    df = df.sort_values(by='timestamp_iso').reset_index(drop=True)
    giorni = {0: _('Lunedì'), 1: _('Martedì'), 2: _('Mercoledì'), 3: _('Giovedì'), 4: _('Venerdì'), 5: _('Sabato'), 6: _('Domenica')}
    mesi = {1: _('Gennaio'), 2: _('Febbraio'), 3: _('Marzo'), 4: _('Aprile'), 5: _('Maggio'), 6: _('Giugno'), 7: _('Luglio'), 8: _('Agosto'), 9: _('Settembre'), 10: _('Ottobre'), 11: _('Novembre'), 12: _('Dicembre')}
    report_attivita = genera_report_attivita(df, _, lang, giorni, mesi)
    report_performance = genera_report_performance(df, _, lang)
    report_velocita_avanzato = genera_report_velocita_avanzato(df, _, lang)
    report_avanzato = genera_report_avanzato(df, _, lang, giorni, mesi)
    report_confronto = genera_report_confronto_settimanale(df, _, lang)
    report_stagionale = genera_report_stagionale(df, _, lang)
    # MODIFICA: Aggiunto un separatore per migliorare la leggibilità del report finale.
    report_completo = ''.join([
        report_attivita,
        report_performance,
        report_velocita_avanzato,
        report_avanzato,
        report_confronto,
        report_stagionale
        ])
    return report_completo