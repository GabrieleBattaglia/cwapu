import json
import numpy as np
import pandas as pd
from collections import Counter

def timeline_stats():
    """
    Carica e prepara i dati storici dal file JSON di CWAPU.
    Args:
    Returns:
        pandas.DataFrame: DataFrame con i dati delle sessioni, o None se c'è un errore.
    """
    print(Trnsl('analysis_start', lang))
    try:
        with open("cwapu_settings.json", 'r', encoding='utf-8') as f:
            dati = json.load(f)
        print(Trnsl('json_read_success', lang))
    except FileNotFoundError:
        print(Trnsl('error_file_not_found', lang))
        return None
    except json.JSONDecodeError:
        print(Trnsl('error_json_decode', lang))
        return None
    log_sessioni = dati.get("historical_rx_data", {}).get("sessions_log", [])
    if not log_sessioni:
        print(Trnsl('warning_no_log_data', lang))
        return None
    
    print(Trnsl('sessions_found', lang, count=len(log_sessioni)))

    df = pd.DataFrame(log_sessioni)
    print(Trnsl('df_load_success', lang))

    df['timestamp_iso'] = pd.to_datetime(df['timestamp_iso'])
    df = df.sort_values(by='timestamp_iso').reset_index(drop=True)
    
    print(Trnsl('data_prep_complete', lang))
    
    return df

def genera_report_attivita(df: pd.DataFrame) -> str:
    """
    Analizza la distribuzione temporale delle sessioni e genera un report testuale.

    Args:
        df (pd.DataFrame): Il DataFrame con i dati delle sessioni.

    Returns:
        str: Una stringa contenente il report testuale formattato.
    """
    if df.empty:
        # Questa stringa verrà da Trnsl('no_data_to_analyze')
        return "Nessun dato da analizzare." 

    report_lines = []
    total_sessions = len(df)

    # --- Riepilogo Generale ---
    # La tua app chiamerà Trnsl('summary_title')
    report_lines.append("--- Riepilogo Attività ---")
    
    # Nota: strftime non è localizzato di default, ma per date e ore va bene.
    # Per i nomi di mese/giorno useremo il metodo Trnsl come discusso.
    prima_sessione = df['timestamp_iso'].min()
    ultima_sessione = df['timestamp_iso'].max()
    giorni_coperti = (ultima_sessione - prima_sessione).days

    report_lines.append(f"Numero totale di sessioni: {total_sessions}") # Trnsl('total_sessions_info', count=total_sessions)
    report_lines.append(f"Periodo coperto: {giorni_coperti} giorni") # Trnsl('period_covered_info', days=giorni_coperti)
    report_lines.append(f"Prima sessione: {prima_sessione.strftime('%d/%m/%Y, %H:%M')}") # Trnsl('first_session_info', date=...)
    report_lines.append(f"Ultima sessione: {ultima_sessione.strftime('%d/%m/%Y, %H:%M')}") # Trnsl('last_session_info', date=...)
    report_lines.append("-" * 25)

    # --- Distribuzione Oraria ---
    report_lines.append("\n--- Distribuzione Oraria delle Sessioni ---") # Trnsl('hourly_distribution_title')
    hourly_counts = Counter(df['timestamp_iso'].dt.hour)
    piu_intensa_ora = hourly_counts.most_common(1)[0][0]
    
    for hour in sorted(hourly_counts.keys()):
        count = hourly_counts[hour]
        percentage = (count / total_sessions) * 100
        # Trnsl('hourly_distribution_line', hour_start=hour, count=count, percentage=percentage)
        report_lines.append(f"  - Ore {hour:02d}:00: {count} sessioni ({percentage:.1f}%)")
    
    report_lines.append(f"Picco di attività orario: {piu_intensa_ora:02d}:00.") # Trnsl('hourly_peak_activity', hour=piu_intensa_ora)
    report_lines.append("-" * 25)

    # --- Distribuzione Settimanale ---
    report_lines.append("\n--- Distribuzione Settimanale ---") # Trnsl('weekly_distribution_title')
    # Assumiamo che Trnsl('giorni_settimana_dict') restituisca un dizionario {0: 'Lunedì', ...}
    giorni = {0: 'Lunedì', 1: 'Martedì', 2: 'Mercoledì', 3: 'Giovedì', 4: 'Venerdì', 5: 'Sabato', 6: 'Domenica'}
    weekly_counts = Counter(df['timestamp_iso'].dt.dayofweek)
    piu_intenso_giorno_idx = weekly_counts.most_common(1)[0][0]
    
    for day_idx in sorted(weekly_counts.keys()):
        count = weekly_counts[day_idx]
        percentage = (count / total_sessions) * 100
        # Trnsl('weekly_distribution_line', day_name=giorni[day_idx], count=count, percentage=percentage)
        report_lines.append(f"  - {giorni[day_idx]}: {count} sessioni ({percentage:.1f}%)")

    report_lines.append(f"Picco di attività settimanale: {giorni[piu_intenso_giorno_idx]}.") # Trnsl('weekly_peak_activity', day_name=...)
    report_lines.append("-" * 25)
    
    # --- Distribuzione Mensile ---
    report_lines.append("\n--- Distribuzione Mensile ---") # Trnsl('monthly_distribution_title')
    # Assumiamo che Trnsl('mesi_anno_dict') restituisca un dizionario {1: 'Gennaio', ...}
    mesi = {1: 'Gennaio', 2: 'Febbraio', 3: 'Marzo', 4: 'Aprile', 5: 'Maggio', 6: 'Giugno', 7: 'Luglio', 8: 'Agosto', 9: 'Settembre', 10: 'Ottobre', 11: 'Novembre', 12: 'Dicembre'}
    monthly_counts = Counter(df['timestamp_iso'].dt.month)
    piu_intenso_mese_idx = monthly_counts.most_common(1)[0][0]

    for month_idx in sorted(monthly_counts.keys()):
        count = monthly_counts[month_idx]
        percentage = (count / total_sessions) * 100
        # Trnsl('monthly_distribution_line', month_name=mesi[month_idx], count=count, percentage=percentage)
        report_lines.append(f"  - {mesi[month_idx]}: {count} sessioni ({percentage:.1f}%)")

    report_lines.append(f"Picco di attività mensile: {mesi[piu_intenso_mese_idx]}.") # Trnsl('monthly_peak_activity', month_name=...)

    return "\n".join(report_lines)

def genera_report_performance(df: pd.DataFrame) -> str:
    """
    Analizza l'andamento della velocità (WPM) e degli errori sui caratteri,
    generando un report testuale sulle performance.

    Args:
        df (pd.DataFrame): Il DataFrame con i dati delle sessioni.

    Returns:
        str: Una stringa contenente il report formattato.
    """
    if df.empty:
        return "Nessun dato di performance da analizzare." # Trnsl('no_performance_data')

    report_lines = []
    total_sessions = len(df)
    
    # --- 1. Analisi della Velocità (WPM) ---
    report_lines.append("--- Analisi della Performance: Velocità (WPM) ---") # Trnsl('wpm_analysis_title')
    
    velocita_media_totale = df['wpm_avg'].mean()
    dev_std_totale = df['wpm_avg'].std()

    report_lines.append(f"Velocità media complessiva: {velocita_media_totale:.1f} WPM.") # Trnsl('overall_avg_wpm', wpm=...)
    report_lines.append(f"Consistenza (dev. std.): {dev_std_totale:.1f} WPM.") # Trnsl('overall_wpm_consistency', std=...)

    # Analisi del trend: confrontiamo la prima e la seconda metà delle sessioni
    meta_sessioni = total_sessions // 2
    prima_meta_df = df.iloc[:meta_sessioni]
    seconda_meta_df = df.iloc[meta_sessioni:]

    if not prima_meta_df.empty and not seconda_meta_df.empty:
        wpm_prima_meta = prima_meta_df['wpm_avg'].mean()
        wpm_seconda_meta = seconda_meta_df['wpm_avg'].mean()
        tendenza_wpm = "miglioramento" if wpm_seconda_meta > wpm_prima_meta else "peggioramento" # Trnsl(tendenza_wpm)

        # Trnsl('wpm_trend_report', half1=..., half2=..., trend=...)
        report_lines.append(
            f"Andamento: la media è passata da {wpm_prima_meta:.1f} WPM (prima metà) "
            f"a {wpm_seconda_meta:.1f} WPM (seconda metà). Tendenza: {tendenza_wpm}."
        )
    report_lines.append("-" * 25)

    # --- 2. Analisi degli Errori sui Caratteri ---
    report_lines.append("\n--- Analisi degli Errori sui Caratteri ---") # Trnsl('char_error_analysis_title')

    # Raccogliamo tutti i dati di errore e invio da ogni sessione
    stat_caratteri = []
    for _, sessione in df.iterrows():
        caratteri_inviati = sessione['sent_chars_detail_session']
        errori_dettaglio = sessione['errors_detail_session']
        # Uniamo tutte le chiavi (caratteri) da entrambi i dizionari
        tutti_caratteri = set(caratteri_inviati.keys()) | set(errori_dettaglio.keys())
        
        for char in tutti_caratteri:
            stat_caratteri.append({
                'carattere': char,
                'inviati': caratteri_inviati.get(char, 0),
                'errori': errori_dettaglio.get(char, 0)
            })
    
    # Aggreghiamo i dati per carattere
    char_df = pd.DataFrame(stat_caratteri).groupby('carattere').sum()
    
    # Calcoliamo il tasso di errore, gestendo la divisione per zero
    char_df['tasso_errore'] = np.where(char_df['inviati'] > 0, (char_df['errori'] / char_df['inviati']) * 100, 0)

    # Filtriamo per caratteri significativi (inviati almeno 20 volte)
    char_df_filtrato = char_df[char_df['inviati'] >= 20]

    if char_df_filtrato.empty:
        report_lines.append("Nessun carattere ha dati sufficienti per un'analisi dettagliata.") # Trnsl('insufficient_char_data')
    else:
        # Identifichiamo i 5 caratteri più critici
        caratteri_critici = char_df_filtrato.sort_values(by='tasso_errore', ascending=False).head(5)
        
        report_lines.append("Primi 5 caratteri critici (per tasso di errore):") # Trnsl('top5_critical_chars_title')
        for char, row in caratteri_critici.iterrows():
            # Trnsl('critical_char_summary', char=char, rate=..., errors=..., sent=...)
            report_lines.append(
                f"  - Carattere '{char}': Tasso errore {row['tasso_errore']:.1f}% "
                f"({int(row['errori'])} errori su {int(row['inviati'])} invii)"
            )
        
        # Aggiunta: Analisi dell'evoluzione per il carattere PIÙ critico
        if not caratteri_critici.empty:
            char_piu_critico = caratteri_critici.index[0]
            report_lines.append(f"\nApprofondimento sull'evoluzione del carattere '{char_piu_critico}':") # Trnsl('evolution_focus_title', char=...)
            
            # Calcoliamo il tasso di errore nella prima e seconda metà
            errori_prima_meta = 0
            inviati_prima_meta = 0
            for _, sessione in prima_meta_df.iterrows():
                errori_prima_meta += sessione.get('errors_detail_session', {}).get(char_piu_critico, 0)
                inviati_prima_meta += sessione.get('sent_chars_detail_session', {}).get(char_piu_critico, 0)

            errori_seconda_meta = 0
            inviati_seconda_meta = 0
            for _, sessione in seconda_meta_df.iterrows():
                errori_seconda_meta += sessione.get('errors_detail_session', {}).get(char_piu_critico, 0)
                inviati_seconda_meta += sessione.get('sent_chars_detail_session', {}).get(char_piu_critico, 0)
            
            tasso_err_prima = np.where(inviati_prima_meta > 0, (errori_prima_meta / inviati_prima_meta) * 100, 0)
            tasso_err_seconda = np.where(inviati_seconda_meta > 0, (errori_seconda_meta / inviati_seconda_meta) * 100, 0)
            tendenza_char = "miglioramento" if tasso_err_seconda < tasso_err_prima else "peggioramento o stabile" # Trnsl(...)
            
            # Trnsl('char_evolution_report', half1_rate=..., half2_rate=..., trend=...)
            report_lines.append(f"Tasso errore prima metà: {tasso_err_prima:.1f}%.")
            report_lines.append(f"Tasso errore seconda metà: {tasso_err_seconda:.1f}%.")
            report_lines.append(f"Tendenza per '{char_piu_critico}': {tendenza_char}.")
    return "\n".join(report_lines)

def genera_report_avanzato(df: pd.DataFrame) -> str:
    """
    Calcola statistiche avanzate come accuratezza, durata delle sessioni
    e correlazioni, generando un report testuale.

    Args:
        df (pd.DataFrame): Il DataFrame con i dati delle sessioni.

    Returns:
        str: Una stringa contenente il report formattato.
    """
    if df.empty:
        return "Nessun dato per l'analisi avanzata." # Trnsl('no_advanced_data')

    report_lines = []
    total_sessions = len(df)
    
    # --- 1. Analisi dell'Accuratezza ---
    report_lines.append("--- Analisi Avanzata ---") # Trnsl('advanced_analysis_title')
    
    # Calcoliamo l'accuratezza per ogni sessione, gestendo divisioni per zero
    df['accuracy'] = np.where(df['items_sent_session'] > 0, (df['items_correct_session'] / df['items_sent_session']) * 100, 0)
    
    accuratezza_media = df['accuracy'].mean()
    report_lines.append(f"Accuratezza media complessiva: {accuratezza_media:.1f}%.") # Trnsl('overall_avg_accuracy', acc=...)

    # Analisi del trend dell'accuratezza
    meta_sessioni = total_sessions // 2
    prima_meta_df = df.iloc[:meta_sessioni]
    seconda_meta_df = df.iloc[meta_sessioni:]

    if not prima_meta_df.empty and not seconda_meta_df.empty:
        acc_prima_meta = prima_meta_df['accuracy'].mean()
        acc_seconda_meta = seconda_meta_df['accuracy'].mean()
        tendenza_acc = "miglioramento" if acc_seconda_meta > acc_prima_meta else "peggioramento" # Trnsl(tendenza_acc)

        # Trnsl('accuracy_trend_report', half1=..., half2=..., trend=...)
        report_lines.append(
            f"Andamento accuratezza: da {acc_prima_meta:.1f}% (prima metà) "
            f"a {acc_seconda_meta:.1f}% (seconda metà). Tendenza: {tendenza_acc}."
        )
    report_lines.append("-" * 25)

    # --- 2. Correlazione Velocità vs. Accuratezza ---
    report_lines.append("\n--- Correlazione Velocità-Accuratezza ---") # Trnsl('correlation_title')
    
    correlazione = df['wpm_avg'].corr(df['accuracy'])
    
    if pd.isna(correlazione):
        interpretazione = "dati insufficienti per calcolare una correlazione." # Trnsl('corr_insufficient_data')
    elif correlazione < -0.5:
        interpretazione = "forte correlazione negativa: all'aumentare della velocità, l'accuratezza tende a diminuire." # Trnsl('corr_strong_negative')
    elif correlazione < -0.2:
        interpretazione = "correlazione negativa moderata: c'è una leggera tendenza a essere meno accurati a velocità più alte." # Trnsl('corr_moderate_negative')
    elif correlazione > 0.5:
        interpretazione = "forte correlazione positiva: all'aumentare della velocità, anche l'accuratezza tende a migliorare." # Trnsl('corr_strong_positive')
    elif correlazione > 0.2:
        interpretazione = "correlazione positiva moderata: c'è una leggera tendenza a essere più accurati a velocità più alte." # Trnsl('corr_moderate_positive')
    else:
        interpretazione = "nessuna correlazione significativa tra velocità e accuratezza." # Trnsl('corr_none')

    report_lines.append(f"Coefficiente di correlazione: {correlazione:.2f}.") # Trnsl('correlation_coefficient', r=...)
    report_lines.append(f"Interpretazione: {interpretazione}")
    report_lines.append("-" * 25)

    # --- 3. Analisi Durata Sessioni ---
    durata_media_sec = df['duration_seconds'].mean()
    report_lines.append(f"\n--- Analisi Durata Sessioni ---") # Trnsl('duration_analysis_title')
    report_lines.append(f"Durata media di una sessione: {int(durata_media_sec // 60)} minuti e {int(durata_media_sec % 60)} secondi.") # Trnsl('avg_duration', min=..., sec=...)

    return "\n".join(report_lines)

def genera_report_temporale_completo() -> str:
    """
    Funzione direttore che orchestra tutte le analisi e assembla il report finale.

    Returns:
        str: Il report statistico testuale completo.
    """
    # 1. Carica e prepara i dati
    df = timeline_stats()
    
    if df is None:
        # Assumendo che timeline_stats() stampi già il suo errore
        return "" # Restituisce una stringa vuota in caso di errore

    # 2. Genera i report parziali chiamando le altre funzioni
    report_attivita = genera_report_attivita(df)
    report_performance = genera_report_performance(df)
    report_avanzato = genera_report_avanzato(df)

    # 3. Assembla il report finale
    report_completo = "\n\n".join([
        report_attivita,
        report_performance,
        report_avanzato
    ])
    
    return report_completo