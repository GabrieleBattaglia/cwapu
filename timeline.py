# TIMELINE Calcola statistiche basate su cwapu_settings.json creato da cwapu.
# V7. Creato in data giovedì 10 luglio 2025 da Gabriele Battaglia e Gemini 2.5 Pro
import json, math
import numpy as np
import pandas as pd
import datetime as dt
from collections import Counter

def wilson_score_upper_bound(errori, invii, confidenza=0.95):
    """
    Calcola il limite superiore dell'intervallo di confidenza di Wilson.
    """
    if invii == 0:
        return 1.0 # Il caso peggiore
    errori = min(errori, invii)
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
    errori = min(errori, invii)
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
    total_duration_overall = df['duration_seconds'].sum()
    if df.empty:
        return _('Nessun dato da analizzare.')
    def _formatta_delta_temporale(delta, _):
        parti = []
        secondi_totali = int(delta.total_seconds())
        giorni, secondi_rimanenti = divmod(secondi_totali, 86400)
        # Approssimazione: 365 giorni/anno, 30 giorni/mese
        anni, giorni_rimanenti = divmod(giorni, 365)
        mesi, giorni_finali = divmod(giorni_rimanenti, 30)
        ore, secondi_rimanenti = divmod(secondi_rimanenti, 3600)
        minuti, sec_finali = divmod(secondi_rimanenti, 60)
        if anni > 0: parti.append(_("{} anni").format(anni))
        if mesi > 0: parti.append(_("{} mesi").format(mesi))
        if giorni_finali > 0: parti.append(_("{} giorni").format(giorni_finali))
        if ore > 0: parti.append(_("{} ore").format(ore))
        if minuti > 0: parti.append(_("{} minuti").format(minuti))
        return ", ".join(parti) if parti else _("Meno di un minuto")
    durata_totale_delta = dt.timedelta(seconds=total_duration_overall)
    durata_totale_str = _formatta_delta_temporale(durata_totale_delta, _)
    report_lines.append(_('--- Riepilogo Attività ---'))
    prima_sessione = df['timestamp_iso'].min()
    ultima_sessione = df['timestamp_iso'].max()
    delta_coperto = ultima_sessione - prima_sessione
    periodo_coperto_str = _formatta_delta_temporale(delta_coperto, _)
    giorni_coperti = delta_coperto.days
    prima_sessione_str = f"{giorni[prima_sessione.weekday()]} {prima_sessione.day} {mesi[prima_sessione.month]} {prima_sessione.year}, {prima_sessione.strftime('%H:%M')}"
    ultima_sessione_str = f"{giorni[ultima_sessione.weekday()]} {ultima_sessione.day} {mesi[ultima_sessione.month]} {ultima_sessione.year}, {ultima_sessione.strftime('%H:%M')}"
    report_lines.append(_('   Numero totale di sessioni: {} (per un totale di {})').format(total_sessions, durata_totale_str))
    report_lines.append(_('  Prima sessione: {}').format(prima_sessione_str))
    report_lines.append(_('  Ultima sessione: {}').format(ultima_sessione_str))
    report_lines.append(_('  Periodo coperto: {}').format(periodo_coperto_str))
    if giorni_coperti > 0:
        frequenza_media = total_sessions / giorni_coperti
        report_lines.append(_('  Frequenza media: {:.2f} esercizi/giorno').format(frequenza_media))
    report_lines.append(_('--- Distribuzione Oraria delle Sessioni ---'))
    hourly_stats = df.groupby(df['timestamp_iso'].dt.hour).agg(
        count=('timestamp_iso', 'size'),
        total_duration=('duration_seconds', 'sum')
    )
    piu_intensa_ora = hourly_stats['total_duration'].idxmax()
    for hour, stats in hourly_stats.sort_values(by='total_duration', ascending=False).iterrows():
        percentage = (stats['total_duration'] / total_duration_overall) * 100 if total_duration_overall > 0 else 0
        durata_str = _formatta_durata(stats['total_duration'], _)
        report_lines.append(_("   - Fascia {start_hour:02d}-{end_hour:02d}: {count} sessioni ({percentage:.2f}%), durata {durata}").format(
            start_hour=hour, end_hour=hour + 1, count=int(stats['count']), percentage=percentage, durata=durata_str))
    report_lines.append(_("  Picco di attività orario: {hour:02d}:00.").format(hour=piu_intensa_ora))
    report_lines.append(_('  --- Suddivisione Giornaliera per Fasce di 6 Ore ---'))
    def get_fascia_6_ore(hour):
        if 0 <= hour <= 6:
            return "00-06"
        elif 7 <= hour <= 12:
            return "07-12"
        elif 13 <= hour <= 18:
            return "13-18"
        else:  # Ore da 19 a 23
            return "19-24"
    df_copy = df.copy()
    df_copy['fascia_6h'] = df_copy['timestamp_iso'].dt.hour.apply(get_fascia_6_ore)
    fasce_6h_stats = df_copy.groupby('fascia_6h').agg(
        count=('timestamp_iso', 'size'),
        total_duration=('duration_seconds', 'sum')
    )
    for fascia, stats in fasce_6h_stats.sort_values(by='total_duration', ascending=False).iterrows():
        percentage = (stats['total_duration'] / total_duration_overall) * 100 if total_duration_overall > 0 else 0
        durata_str = _formatta_durata(stats['total_duration'], _)
        report_lines.append(_("   - Fascia {fascia}: {count} sessioni ({percentage:.2f}%), durata {durata}").format(
            fascia=fascia, 
            count=int(stats['count']), 
            percentage=percentage, 
            durata=durata_str
        ))
    report_lines.append('-' * 25)
    report_lines.append(_('  -- Distribuzione Settimanale ---'))
    weekly_stats = df.groupby(df['timestamp_iso'].dt.dayofweek).agg(
        count=('timestamp_iso', 'size'),
        total_duration=('duration_seconds', 'sum')
    )
    piu_intenso_giorno_idx = weekly_stats['total_duration'].idxmax()
    for day_idx, stats in weekly_stats.sort_values(by='total_duration', ascending=False).iterrows():
        percentage = (stats['total_duration'] / total_duration_overall) * 100 if total_duration_overall > 0 else 0
        durata_str = _formatta_durata(stats['total_duration'], _)
        report_lines.append(_("   - {giorno}: {count} sessioni ({percentage:.2f}%), durata {durata}").format(
            giorno=giorni[day_idx], count=int(stats['count']), percentage=percentage, durata=durata_str))
    report_lines.append(_('   Picco di attività settimanale: {}.').format(giorni[int(piu_intenso_giorno_idx)]))
    report_lines.append('-' * 25)
    report_lines.append(_('--- Distribuzione Mensile ---'))
    monthly_stats = df.groupby(df['timestamp_iso'].dt.month).agg(
        count=('timestamp_iso', 'size'),
        total_duration=('duration_seconds', 'sum')
    )
    piu_intenso_mese_idx = monthly_stats['total_duration'].idxmax()
    for month_idx, stats in monthly_stats.sort_values(by='total_duration', ascending=False).iterrows():
        percentage = (stats['total_duration'] / total_duration_overall) * 100 if total_duration_overall > 0 else 0
        durata_str = _formatta_durata(stats['total_duration'], _)
        report_lines.append(_("   - {mese}: {count} sessioni ({percentage:.2f}%), durata {durata}").format(
            mese=mesi[month_idx], count=int(stats['count']), percentage=percentage, durata=durata_str))
    report_lines.append(_('   Picco di attività mensile: {}.').format(mesi[int(piu_intenso_mese_idx)]))
    report_lines.append('-' * 25)
    report_lines.append(_('--- Distribuzione Stagionale ---'))
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
        percentage = (stats['total_duration'] / total_duration_overall) * 100 if total_duration_overall > 0 else 0
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
            all_item_wpms.extend([item['rwpm'] for item in session_details])
    if all_item_wpms:
        velocita_media_reale = np.mean(all_item_wpms)
        dev_std_reale = np.std(all_item_wpms)
        report_lines.append(_('  Velocità media reale: {:.2f} WPM.').format(velocita_media_reale))
        report_lines.append(_('  Consistenza WPM reale (dev. std): {:.2f}.').format(dev_std_reale))
    else:
        velocita_media_totale = df['rwpm_avg'].mean()
        report_lines.append(_('  Velocità media complessiva: {:.2f} WPM.').format(velocita_media_totale))
    report_lines.append('-' * 25)
    report_lines.append(_('--- Analisi degli Errori sui Caratteri ---'))
    stat_caratteri = []
    for u4, sessione in df.iterrows():
        caratteri_inviati = sessione.get('sent_chars_detail_session', {})
        errori_dettaglio = sessione.get('errors_detail_session', {})
        tutti_caratteri = set(caratteri_inviati.keys()) | set(errori_dettaglio.keys())
        for char in tutti_caratteri:
            stat_caratteri.append({'carattere': char, 'inviati': caratteri_inviati.get(char, 0), 'errori': errori_dettaglio.get(char, 0)})
    if not stat_caratteri:
         report_lines.append(_("  Nessun dato dettagliato sui caratteri per un'analisi."))
    else:
        char_df = pd.DataFrame(stat_caratteri).groupby('carattere').sum()
        char_df['limite_inferiore'] = char_df.apply(lambda row: wilson_score_lower_bound(row['errori'], row['inviati']), axis=1)
        char_df['limite_superiore'] = char_df.apply(lambda row: wilson_score_upper_bound(row['errori'], row['inviati']), axis=1)
        # Calcoliamo la media e l'incertezza per la visualizzazione
        char_df['media_errore'] = (char_df['limite_superiore'] + char_df['limite_inferiore']) / 2 * 100
        char_df['incertezza'] = (char_df['limite_superiore'] - char_df['limite_inferiore']) / 2 * 100
        char_df_filtrato = char_df[char_df['inviati'] >= 20]
        if char_df_filtrato.empty:
            report_lines.append(_("  Nessun carattere ha dati sufficienti per un'analisi dettagliata."))
        else:
            caratteri_peggiori = char_df_filtrato.sort_values(by='limite_inferiore', ascending=False).head(10)
            report_lines.append(_('  Top 10 Caratteri Peggiori (ordinati per criticità statistica):'))
            for char, row in caratteri_peggiori.iterrows():
                report_lines.append(_("  - Carattere '{}': Errore stimato {:.2f}% ±{:.2f}% ({} errori su {} invii)").format(
                    char, row['media_errore'], row['incertezza'], int(row['errori']), int(row['inviati'])))
            if not caratteri_peggiori.empty:
                char_piu_critico = caratteri_peggiori.index[0]
                report_lines.append(_("  Approfondimento sull'evoluzione del carattere '{}':").format(char_piu_critico))
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
                report_lines.append(_("  Tasso errore prima metà: {:.2f}%.").format(tasso_err_prima))
                report_lines.append(_("  Tasso errore seconda metà: {:.2f}%.").format(tasso_err_seconda))
                report_lines.append(_("  Tendenza per '{}': {}.").format(char_piu_critico, tendenza_char))
            caratteri_migliori = char_df_filtrato.sort_values(by='limite_superiore', ascending=True).head(10)
            report_lines.append(_('---Top 10 Caratteri Migliori (ordinati per affidabilità statistica):'))
            for char, row in caratteri_migliori.iterrows():
                # MODIFICA: Visualizziamo anche qui nel nuovo formato
                report_lines.append(_("  - Carattere '{}': Errore stimato {:.2f}% ±{:.2f}% ({} errori su {} invii)").format(
                    char, row['media_errore'], row['incertezza'], int(row['errori']), int(row['inviati'])))
    return '\n'.join(report_lines)

def genera_report_velocita_avanzato(df: pd.DataFrame, _, lang) -> str:
    """
    Calcola e riporta statistiche avanzate sulla velocità (WPM) usando solo Pandas e NumPy.
    """
    if df.empty or 'rwpm_avg' not in df.columns:
        return ""
    report_lines = []
    report_lines.append(_('\n--- Analisi Avanzata della Velocità (WPM) ---'))
    wpm_series = df['rwpm_avg'].dropna()
    if wpm_series.empty:
        report_lines.append(_("  Nessun dato sulla velocità media disponibile per l'analisi."))
        return '\n'.join(report_lines)
    # Calcolo delle medie
    mean_aritmetica = wpm_series.mean()
    mean_quadratica = np.sqrt(np.mean(wpm_series**2))
    mean_ponderata = np.average(wpm_series, weights=df.loc[wpm_series.index, 'duration_seconds'])
    report_lines.append(_('  Prospettive sulla Velocità Media:'))
    report_lines.append(_("  - Media Aritmetica: {:.2f} WPM (il valore 'classico')").format(mean_aritmetica))
    report_lines.append(_("  - Media Ponderata (per durata): {:.2f} WPM (dà più peso alle sessioni lunghe)").format(mean_ponderata))
    report_lines.append(_("  - Media Quadratica (RMS): {:.2f} WPM (dà più peso alle velocità più alte)").format(mean_quadratica))
    # MODIFICA: Calcolo di moda e dispersione usando solo Pandas/NumPy
    moda_series = wpm_series.round().mode()
    moda_wpm = moda_series[0] if not moda_series.empty else np.nan 
    q1 = wpm_series.quantile(0.25)
    q3 = wpm_series.quantile(0.75)
    iqr = q3 - q1
    report_lines.append(_('  Frequenza e Consistenza:'))
    if pd.notna(moda_wpm):
        report_lines.append(_("  - Moda (velocità più frequente): {:.0f} WPM").format(moda_wpm))
    report_lines.append(_("  - Dispersione (Range Interquartile): {:.2f} WPM (un valore basso indica grande consistenza)").format(iqr))
    report_lines.append(_("  - (Il 50% delle tue sessioni ha una velocità media tra {:.2f} e {:.2f} WPM)").format(q1, q3))
    # Calcolo media ultime 12 settimane
    data_fine = pd.Timestamp.now() 
    data_inizio = data_fine - pd.DateOffset(weeks=12)
    df_ultime_12_settimane = df[df['timestamp_iso'] >= data_inizio]
    if not df_ultime_12_settimane.empty:
        media_12_settimane = df_ultime_12_settimane['rwpm_avg'].mean()
        report_lines.append(_('  Trend Recente:'))
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
    report_lines.append(_("  Accuratezza media complessiva: {:.2f}%.").format(accuratezza_media))
    meta_sessioni = total_sessions // 2
    prima_meta_df = df.iloc[:meta_sessioni]
    seconda_meta_df = df.iloc[meta_sessioni:]
    if not prima_meta_df.empty and not seconda_meta_df.empty:
        acc_prima_meta = prima_meta_df['accuracy'].mean()
        acc_seconda_meta = seconda_meta_df['accuracy'].mean()
        tendenza_acc = _('miglioramento') if acc_seconda_meta > acc_prima_meta else _('peggioramento')
        report_lines.append(_("  Andamento accuratezza: da {:.2f}% (prima metà) a {:.2f}% (seconda metà). Tendenza: {}.").format(acc_prima_meta, acc_seconda_meta, tendenza_acc))
    report_lines.append(_('  --- Correlazione Velocità-Accuratezza ---'))
    all_item_details = []
    if 'item_details' in df.columns:
        for session_details in df['item_details'].dropna():
            all_item_details.extend(session_details)
    if all_item_details:
        item_df = pd.DataFrame(all_item_details)
        item_df['correct_numeric'] = item_df['correct'].astype(int)
        correlazione = item_df['rwpm'].corr(item_df['correct_numeric'])
        interpretazione = ''
        if pd.isna(correlazione):
            interpretazione = _('Dati insufficienti per calcolare la correlazione.')
        elif correlazione < -0.2:
            interpretazione = _('Correlazione negativa debole: la velocità tende a diminuire quando l_accuratezza aumenta.')
        elif correlazione > 0.2:
            interpretazione = _('Correlazione positiva debole: la velocità tende ad aumentare con l_accuratezza.')
        else:
            interpretazione = _('Nessuna correlazione significativa tra velocità e accuratezza.')
        report_lines.append(_("  Coefficiente di correlazione: {:.2f}.").format(correlazione))
        report_lines.append(_('  Interpretazione: {}').format(interpretazione))
    else:
        report_lines.append(_('  Granularità dei dati insufficiente per stabilire una correlazione.'))
    report_lines.append('-' * 25)
    report_lines.append(_('--- Analisi Durata Sessioni ---'))
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
    report_lines.append(_('  Durata media di una sessione: {}').format(durata_media_str))
    report_lines.append(_('  Sessione più corta: {} ({}).').format(durata_corta_str, data_corta_str))
    report_lines.append(_('  Sessione più lunga: {} ({}).').format(durata_lunga_str, data_lunga_str))
    report_lines.append(_('--- Analisi Granulare Velocità/Accuratezza ---'))
    if not all_item_details:
        report_lines.append(_('  Dati granulari non presenti.'))
    else:
        correct_items = [item for item in all_item_details if item['correct']]
        wrong_items = [item for item in all_item_details if not item['correct']]
        avg_wpm_correct = np.mean([item['rwpm'] for item in correct_items]) if correct_items else 0
        avg_wpm_wrong = np.mean([item['rwpm'] for item in wrong_items]) if wrong_items else 0
        report_lines.append(_('  Media WPM su item corretti: {:.2f}').format(avg_wpm_correct))
        report_lines.append(_('  Media WPM su item errati: {:.2f}').format(avg_wpm_wrong))
        if avg_wpm_correct > avg_wpm_wrong and wrong_items:
            report_lines.append(_("  Conclusione: all'aumentare della velocità di ricezione, aumenta anche l'accuratezza."))
        elif avg_wpm_wrong > avg_wpm_correct and correct_items:
            report_lines.append(_("  Conclusione: al diminuire della velocità di ricezione, aumenta l'accuratezza."))
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
        wpm_feriale = df_feriale['rwpm_avg'].mean()
        acc_feriale = df_feriale['accuracy'].mean()
        tempo_feriale_sec = df_feriale['duration_seconds'].sum()
        sessioni_feriale = len(df_feriale)
        report_lines.append(_('  Giorni Feriali (Lun-Ven):'))
        report_lines.append(_("  - Sessioni totali: {}").format(sessioni_feriale))
        report_lines.append(_("  - WPM medio: {:.2f}").format(wpm_feriale))
        report_lines.append(_("  - Accuratezza media: {:.2f}%").format(acc_feriale))
        report_lines.append(_("  - Tempo totale di pratica: {}").format(formatta_durata(tempo_feriale_sec)))
    else:
        report_lines.append(_('  Nessuna sessione registrata nei giorni feriali.'))
    # Analisi Weekend
    if not df_weekend.empty:
        wpm_weekend = df_weekend['rwpm_avg'].mean()
        acc_weekend = df_weekend['accuracy'].mean()
        tempo_weekend_sec = df_weekend['duration_seconds'].sum()
        sessioni_weekend = len(df_weekend)
        report_lines.append(_('  Weekend (Sab-Dom):'))
        report_lines.append(_("  - Sessioni totali: {}").format(sessioni_weekend))
        report_lines.append(_("  - WPM medio: {:.2f}").format(wpm_weekend))
        report_lines.append(_("  - Accuratezza media: {:.2f}%").format(acc_weekend))
        report_lines.append(_("  - Tempo totale di pratica: {}").format(formatta_durata(tempo_weekend_sec)))
    else:
        report_lines.append(_('  Nessuna sessione registrata nel weekend.'))
    if not df_feriale.empty and not df_weekend.empty:
        giorni_feriali_unici = df_feriale['timestamp_iso'].dt.date.nunique() if not df_feriale.empty else 0
        giorni_weekend_unici = df_weekend['timestamp_iso'].dt.date.nunique() if not df_weekend.empty else 0
        media_giornaliera_feriale = (tempo_feriale_sec / giorni_feriali_unici) if giorni_feriali_unici > 0 else 0
        media_giornaliera_weekend = (tempo_weekend_sec / giorni_weekend_unici) if giorni_weekend_unici > 0 else 0
        report_lines.append(_('  Conclusione:'))
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
        report_lines.append("  "+conclusione)
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
        picco_wpm=('rwpm_max', 'max'),
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
        report_lines.append(_('  Conclusione:'))
        stagione_top_wpm = stat_stagionali['picco_wpm'].idxmax()
        stagione_top_acc = stat_stagionali['picco_accuratezza'].idxmax()
        if stagione_top_wpm == stagione_top_acc:
            report_lines.append(_("  Hai raggiunto i tuoi picchi sia di velocità ({:.0f} WPM) che di accuratezza ({:.2f}%) durante la stagione: {}.").format(
                stat_stagionali['picco_wpm'].max(), 
                stat_stagionali['picco_accuratezza'].max(), 
                stagione_top_wpm
            ))
        else:
            report_lines.append(_("  La tua velocità di punta ({:.0f} WPM) è stata registrata in {}, mentre hai raggiunto la massima accuratezza ({:.2f}%) in {}.").format(
                stat_stagionali['picco_wpm'].max(), 
                stagione_top_wpm, 
                stat_stagionali['picco_accuratezza'].max(), 
                stagione_top_acc
            ))
    return '\n'.join(report_lines)

def genera_report_quartili(df: pd.DataFrame, _, lang, giorni, mesi) -> str:
    """
    Analizza l'andamento delle performance suddividendo i dati in quartili (Q1-Q4)
    con una logica di evidenziazione specifica per minimi, medie e massimi.
    """
    total_sessions = len(df)
    report_lines = [_('\n--- Analisi Evolutiva Dettagliata per Quartili ---')]
    if total_sessions < 8:
        report_lines.append(_("Dati insufficienti per un'analisi dettagliata a quartili (meno di 8 sessioni)."))
        return '\n'.join(report_lines)
    df_copy = df.copy()
    if 'accuracy' not in df_copy.columns:
        df_copy['accuracy'] = np.where(df_copy['items_sent_session'] > 0,
                                     (df_copy['items_correct_session'] / df_copy['items_sent_session']) * 100,
                                     0)
    for old, new in [('wpm_min', 'rwpm_min'), ('wpm_max', 'rwpm_max'), ('wpm_avg', 'rwpm_avg')]:
        if old in df_copy.columns and new not in df_copy.columns:
            df_copy.rename(columns={old: new}, inplace=True)
    quartili_df = {
        'Q1': df_copy.iloc[0 : total_sessions // 4],
        'Q2': df_copy.iloc[total_sessions // 4 : 2 * (total_sessions // 4)],
        'Q3': df_copy.iloc[2 * (total_sessions // 4) : 3 * (total_sessions // 4)],
        'Q4': df_copy.iloc[3 * (total_sessions // 4):]
    }
    def _formatta_durata_quartile(delta, _):
        """Formatta un timedelta in mesi, giorni, ore, minuti."""
        parts = []
        total_seconds = int(delta.total_seconds())
        days = total_seconds // 86400
        remaining_seconds = total_seconds % 86400
        months = days // 30
        remaining_days = days % 30
        hours = remaining_seconds // 3600
        remaining_seconds %= 3600
        minutes = remaining_seconds // 60
        if months > 0:
            parts.append(_('{num} mesi').format(num=months))
        if remaining_days > 0:
            parts.append(_('{num} giorni').format(num=remaining_days))
        if hours > 0:
            parts.append(_('{num} ore').format(num=hours))
        if minutes > 0:
            parts.append(_('{num} minuti').format(num=minutes))
        if not parts:
            return _("(durata inferiore a un minuto)")
        return f"({', '.join(parts)})"
    report_lines.append(_("  Periodi di riferimento dei quartili:\n  NOME--SEZIONI--INIZIO--DURATA---"))
    for nome_q, q_df in quartili_df.items():
        if not q_df.empty and len(q_df) > 1:
            start_ts = q_df['timestamp_iso'].min()
            end_ts = q_df['timestamp_iso'].max()
            duration_delta = end_ts - start_ts
            start_date_str = f"{giorni[start_ts.weekday()]} {start_ts.day} {mesi[start_ts.month]} {start_ts.year}, {start_ts.strftime('%H:%M')}"
            duration_str = _formatta_durata_quartile(duration_delta, _)
            num_esercizi = len(q_df)
            report_lines.append(f"  {nome_q}: S{num_esercizi} - {start_date_str} {duration_str}")
        elif not q_df.empty:
            # Gestisce il caso di un solo elemento nel quartile
            ts = q_df['timestamp_iso'].min()
            date_str = f"{giorni[ts.weekday()]} {ts.day} {mesi[ts.month]} {ts.year}, {ts.strftime('%H:%M')}"
            report_lines.append(f"  {nome_q}: S1 - {date_str} " + _("(singola sessione)"))
        else:
            report_lines.append(f"  {nome_q}: N/A")
    # --- FUNZIONE HELPER PER LA FORMATTAZIONE ---
    def formatta_linea_metrica(titolo: str, metrica_data: list, tipo_metrica: str, suffisso: str = ''):
        valori = [d['valore'] for d in metrica_data if d is not None]
        if not valori:
            return f"{titolo}: " + _("Dati non disponibili.")
        val_da_evidenziare = None
        if tipo_metrica == 'min':
            val_da_evidenziare = min(valori)
        elif tipo_metrica == 'max':
            val_da_evidenziare = max(valori)
        elif tipo_metrica == 'avg':
            media_dei_valori = np.mean(valori)
            val_da_evidenziare = min(valori, key=lambda x: abs(x - media_dei_valori))
        linea_str = [titolo + ":"]
        last_val = None
        for i, data in enumerate(metrica_data):
            nome_q = f"Q{i+1}"
            if data is None:
                linea_str.append(f"{nome_q}=N/A")
                continue
            val = data['valore']
            val_str = f"{val:.2f}"
            if val == val_da_evidenziare:
                val_str = f"[{val_str}]"
            diff_str = ""
            if last_val is not None:
                diff = val - last_val
                simbolo = '+' if diff > 0.01 else '-' if diff < -0.01 else '='
                diff_str = f" {simbolo} ({diff:+.2f}) -> "
            linea_str.append(f"{diff_str}{nome_q}={val_str}{suffisso}")
            last_val = val
        return " ".join(linea_str)
    report_lines.append(_('  --- Velocità (WPM) ---'))
    for metrica, titolo, tipo in [('rwpm_min', _('WPM Min'), 'min'), ('rwpm_avg', _('WPM Medio'), 'avg'), ('rwpm_max', _('WPM Max'), 'max')]:
        dati = [{'valore': q_df[metrica].min() if tipo == 'min' else q_df[metrica].mean() if tipo == 'avg' else q_df[metrica].max()} if not q_df.empty else None for q_df in quartili_df.values()]
        report_lines.append("  "+formatta_linea_metrica(titolo, dati, tipo, " WPM"))
    report_lines.append(_('  --- Accuratezza (%) ---'))
    for agg_func, titolo, tipo in [('min', _('Acc. Minima'), 'min'), ('mean', _('Acc. Media'), 'avg'), ('max', _('Acc. Massima'), 'max')]:
        dati = [{'valore': getattr(q_df['accuracy'], agg_func)()} if not q_df.empty else None for q_df in quartili_df.values()]
        report_lines.append("  "+formatta_linea_metrica(titolo, dati, tipo, "%"))
    report_lines.append(_('  --- Durata Esercizi ---'))
    for agg_func, titolo in [('min', _('Durata Minima')), ('mean', _('Durata Media')), ('max', _('Durata Massima'))]:
        dati = [{'valore': getattr(q_df['duration_seconds'], agg_func)()} if not q_df.empty else None for q_df in quartili_df.values()]
        linea_str = [titolo + ":"]
        last_val_sec = None
        for i, data in enumerate(dati):
            nome_q = f"Q{i+1}"
            if data is None:
                linea_str.append(f"{nome_q}=N/A")
                continue
            val_sec = data['valore']
            val_str_formatted = _formatta_durata(val_sec, _)
            diff_str_formatted = ""
            if last_val_sec is not None:
                diff_sec = val_sec - last_val_sec
                simbolo_diff = 'su' if diff_sec >= 0 else 'giù'
                durata_diff_str = _formatta_durata(abs(diff_sec), _)
                diff_str_formatted = f" {simbolo_diff} ({durata_diff_str}) -> "
            linea_str.append(f"{diff_str_formatted}{nome_q}={val_str_formatted}")
            last_val_sec = val_sec
        report_lines.append("  "+" ".join(linea_str))
    report_lines.append(_('  --- Frequenza Esercizi per Giorno ---'))
    frequenza_parts = []
    for nome_q, q_df in quartili_df.items():
        if not q_df.empty and len(q_df) > 1:
            num_esercizi = len(q_df)
            start_ts = q_df['timestamp_iso'].min()
            end_ts = q_df['timestamp_iso'].max()
            giorni_quartile = (end_ts - start_ts).days
            if giorni_quartile > 0:
                frequenza = num_esercizi / giorni_quartile
                frequenza_parts.append(f"{nome_q}: {frequenza:.2f} es./giorno")
            else:
                # Non calcolabile se tutte le sessioni sono nello stesso giorno
                frequenza_parts.append(f"{nome_q}: N/D")
        else:
            # Non calcolabile per quartile vuoto o con una sola sessione
            frequenza_parts.append(f"{nome_q}: N/D")
    report_lines.append("  " + ", ".join(frequenza_parts))
    report_lines.append(_('  --- Evoluzione dei 3 Caratteri Più Critici (Stima Errore ± Incertezza) ---'))
    global_errors = {}
    global_sents = {}
    for u1, sessione in df_copy.iterrows():
        for char, count in sessione.get('errors_detail_session', {}).items():
            global_errors[char] = global_errors.get(char, 0) + count
        for char, count in sessione.get('sent_chars_detail_session', {}).items():
            global_sents[char] = global_sents.get(char, 0) + count
    global_scores = []
    for char in set(global_errors.keys()) | set(global_sents.keys()):
        e, s = global_errors.get(char, 0), global_sents.get(char, 0)
        if s > 0:
            global_scores.append({'char': char, 'score': wilson_score_lower_bound(e, s)})
    top_3_critici_globali = sorted(global_scores, key=lambda x: -x['score'])[:3]
    if not top_3_critici_globali:
        report_lines.append(_("  Nessun dato sufficiente per identificare i caratteri critici."))
    else:
        for item_critico in top_3_critici_globali:
            char_da_tracciare = item_critico['char']
            quartili_str_list = []
            for nome_q, q_df in quartili_df.items():
                if q_df.empty:
                    quartili_str_list.append(f"{nome_q}=N/A")
                    continue
                errori_q = sum(s.get('errors_detail_session', {}).get(char_da_tracciare, 0) for _, s in q_df.iterrows())
                inviati_q = sum(s.get('sent_chars_detail_session', {}).get(char_da_tracciare, 0) for _, s in q_df.iterrows())
                if inviati_q > 0:
                    # Calcoliamo entrambi i limiti per ottenere media e incertezza
                    limite_inferiore = wilson_score_lower_bound(errori_q, inviati_q)
                    limite_superiore = wilson_score_upper_bound(errori_q, inviati_q)
                    media_errore = (limite_superiore + limite_inferiore) / 2 * 100
                    incertezza = (limite_superiore - limite_inferiore) / 2 * 100
                    quartili_str_list.append(f"{nome_q}={media_errore:.2f}%±{incertezza:.2f}%")
                else:
                    quartili_str_list.append(f"{nome_q}=N/D")
            riga_completa = f"  {char_da_tracciare.upper()}: " + ", ".join(quartili_str_list)
            report_lines.append(riga_completa)
    return '\n'.join(report_lines)

def genera_report_temporale_completo(dati_sessioni, _, lang) -> str:
    """
    Funzione direttore che orchestra tutte le analisi e assembla il report finale,
    incluso l'header.
    """
    mesi = {1: _('Gennaio'), 2: _('Febbraio'), 3: _('Marzo'), 4: _('Aprile'), 5: _('Maggio'), 6: _('Giugno'), 7: _('Luglio'), 8: _('Agosto'), 9: _('Settembre'), 10: _('Ottobre'), 11: _('Novembre'), 12: _('Dicembre')}
    giorni = {0: _('Lunedì'), 1: _('Martedì'), 2: _('Mercoledì'), 3: _('Giovedì'), 4: _('Venerdì'), 5: _('Sabato'), 6: _('Domenica')}
    # --- Creazione Header e dipendenze ---
    now = dt.datetime.now()
    data_formattata = f"{giorni[now.weekday()]} {now.day} {mesi[now.month]} {now.year}, {now.strftime('%H:%M')}"
    header = _("--- Report Statistico CWAPU generato il: {} ---\n").format(data_formattata)
    if not dati_sessioni:
        return header + _('Attenzione: nessun dato di log disponibile da analizzare.')
    df = pd.DataFrame(dati_sessioni)
    df['timestamp_iso'] = pd.to_datetime(df['timestamp_iso'])
    df = df.sort_values(by='timestamp_iso').reset_index(drop=True)
    report_attivita = genera_report_attivita(df, _, lang, giorni, mesi)
    report_performance = genera_report_performance(df, _, lang)
    report_velocita_avanzato = genera_report_velocita_avanzato(df, _, lang)
    report_avanzato = genera_report_avanzato(df, _, lang, giorni, mesi)
    report_confronto = genera_report_confronto_settimanale(df, _, lang)
    report_stagionale = genera_report_stagionale(df, _, lang)
    report_quartili = genera_report_quartili(df, _, lang, giorni, mesi)

    # --- Assemblaggio Corpo del Report ---
    corpo_report = ''.join([
        report_attivita,
        report_performance,
        report_velocita_avanzato,
        report_avanzato,
        report_confronto,
        report_stagionale,
        report_quartili
        ])
    return header + corpo_report