import json
import numpy as np
import pandas as pd
from collections import Counter

def genera_report_attivita(df: pd.DataFrame,Trnsl, lang) -> str:
    """
    Analizza la distribuzione temporale delle sessioni e genera un report testuale.

    Args:
        df (pd.DataFrame): Il DataFrame con i dati delle sessioni.

    Returns:
        str: Una stringa contenente il report testuale formattato.
    """
    report_lines = []
    total_sessions = len(df)
    meta_sessioni = total_sessions // 2
    prima_meta_df = df.iloc[:meta_sessioni]
    seconda_meta_df = df.iloc[meta_sessioni:]
    if df.empty:
        # Questa stringa verrà da Trnsl('no_data_to_analyze')
        return "Nessun dato da analizzare." 
    # La tua app chiamerà Trnsl('summary_title')
    report_lines.append("--- Riepilogo Attività ---")
    
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
    giorni_raw = Trnsl('giorni_settimana_dict', lang=lang)
    giorni = {int(k): v for k, v in giorni_raw.items()}
    report_lines.append("\n--- Distribuzione Settimanale ---") # Trnsl('weekly_distribution_title')
    # Assumiamo che Trnsl('giorni_settimana_dict') restituisca un dizionario {0: 'Lunedì', ...}
    weekly_counts = Counter(df['timestamp_iso'].dt.dayofweek)
    piu_intenso_giorno_idx = weekly_counts.most_common(1)[0][0]
    
    for day_idx in sorted(weekly_counts.keys()):
        count = weekly_counts[day_idx]
        percentage = (count / total_sessions) * 100
        # Trnsl('weekly_distribution_line', day_name=giorni[day_idx], count=count, percentage=percentage)
        report_lines.append(f"  - {giorni[int(day_idx)]}: {count} sessioni ({percentage:.1f}%)")
    report_lines.append(f"Picco di attività settimanale: {giorni[int(piu_intenso_giorno_idx)]}.") # Trnsl('weekly_peak_activity', day_name=...)
    report_lines.append("-" * 25)
    
    # --- Distribuzione Mensile ---
    report_lines.append("\n--- Distribuzione Mensile ---") # Trnsl('monthly_distribution_title')
    mesi_raw = Trnsl('mesi_anno_dict', lang=lang)
    mesi = {int(k): v for k, v in mesi_raw.items()}
    monthly_counts = Counter(df['timestamp_iso'].dt.month)
    piu_intenso_mese_idx = monthly_counts.most_common(1)[0][0]

    for month_idx in sorted(monthly_counts.keys()):
        count = monthly_counts[month_idx]
        percentage = (count / total_sessions) * 100
        # Trnsl('monthly_distribution_line', month_name=mesi[month_idx], count=count, percentage=percentage)
        report_lines.append(f"  - {mesi[int(month_idx)]}: {count} sessioni ({percentage:.1f}%)")

    report_lines.append(f"Picco di attività mensile: {mesi[int(piu_intenso_mese_idx)]}.") # Trnsl('monthly_peak_activity', month_name=...)

    return "\n".join(report_lines)

def genera_report_performance(df: pd.DataFrame,Trnsl, lang) -> str:
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
    meta_sessioni = total_sessions // 2
    prima_meta_df = df.iloc[:meta_sessioni]
    seconda_meta_df = df.iloc[meta_sessioni:]
    # --- 1. Analisi della Velocità (WPM) ---
    report_lines.append(Trnsl('wpm_analysis_title', lang=lang))
    # Raccogliamo tutte le velocità per singolo item dalle sessioni che le contengono
    all_item_wpms = []
    if 'item_details' in df.columns:
        for session_details in df['item_details'].dropna():
            all_item_wpms.extend([item['wpm'] for item in session_details])
    if all_item_wpms:
        # Calcoli basati sui nuovi dati granulari
        velocita_media_reale = np.mean(all_item_wpms)
        dev_std_reale = np.std(all_item_wpms)
        report_lines.append(Trnsl('real_avg_wpm', lang=lang, wpm=f"{velocita_media_reale:.1f}"))
        report_lines.append(Trnsl('real_wpm_consistency', lang=lang, std=f"{dev_std_reale:.1f}"))
    else:
        # Fallback al vecchio metodo se non ci sono dati granulari
        velocita_media_totale = df['wpm_avg'].mean()
        report_lines.append(Trnsl('overall_avg_wpm', lang=lang, wpm=f"{velocita_media_totale:.1f}"))
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
    caratteri_accurati = char_df_filtrato.sort_values(by='tasso_errore', ascending=True).head(5)
    report_lines.append("\nPrimi 5 caratteri più accurati (tra quelli più praticati):") # Trnsl('top5_accurate_chars_title')
    for char, row in caratteri_accurati.iterrows():
        # Trnsl('accurate_char_summary', char=char, rate=..., errors=..., sent=...)
        report_lines.append(
            f"  - Carattere '{char}': Tasso errore {row['tasso_errore']:.1f}% "
            f"({int(row['errori'])} errori su {int(row['inviati'])} invii)"
        )
    return "\n".join(report_lines)

def genera_report_avanzato(df: pd.DataFrame, Trnsl, lang) -> str:
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
    all_item_details = []
    if 'item_details' in df.columns:
        for session_details in df['item_details'].dropna():
            all_item_details.extend(session_details)
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
    # --- 2. Correlazione Velocità vs. Accuratezza (Granulare) ---
    report_lines.append(Trnsl('correlation_title', lang=lang))
    # Usiamo la lista 'all_item_details' che abbiamo già calcolato nella sezione 4
    if all_item_details:
        # Creiamo un DataFrame temporaneo solo per questa analisi
        item_df = pd.DataFrame(all_item_details)
        # Convertiamo il booleano 'correct' in 1 (corretto) e 0 (sbagliato)
        item_df['correct_numeric'] = item_df['correct'].astype(int)
        correlazione = item_df['wpm'].corr(item_df['correct_numeric'])
        if pd.isna(correlazione):
            interpretazione_key = 'corr_insufficient_data'
        elif correlazione < -0.2:
            interpretazione_key = 'corr_moderate_negative_granular' # Es: "Tendi a sbagliare di più ad alte velocità."
        elif correlazione > 0.2:
            interpretazione_key = 'corr_moderate_positive_granular' # Es: "Tendi a essere più accurato quando vai più veloce."
        else:
            interpretazione_key = 'corr_none'
        interpretazione = Trnsl(interpretazione_key, lang=lang)
        report_lines.append(f"Coefficiente di correlazione: {correlazione:.2f}.")
        report_lines.append(Trnsl('correlation_interpretation', lang=lang, interpretation=interpretazione))
    else:
        report_lines.append(Trnsl('no_granular_data_for_correlation', lang=lang))
    report_lines.append("-" * 25)
    # --- 3. Analisi Durata Sessioni ---
    durata_media_sec = df['duration_seconds'].mean()
    report_lines.append(f"\n--- Analisi Durata Sessioni ---") # Trnsl('duration_analysis_title')
    report_lines.append(f"Durata media di una sessione: {int(durata_media_sec // 60)} minuti e {int(durata_media_sec % 60)} secondi.") # Trnsl('avg_duration', min=..., sec=...)
    # --- Analisi Min/Max Durata ---
    # Trova la sessione più corta e più lunga
    idx_min = df['duration_seconds'].idxmin()
    sessione_corta = df.loc[idx_min]
    durata_corta_sec = sessione_corta['duration_seconds']
    idx_max = df['duration_seconds'].idxmax()
    sessione_lunga = df.loc[idx_max]
    durata_lunga_sec = sessione_lunga['duration_seconds']
    # Trnsl('shortest_session_info', min=.., sec=.., date=...)
    report_lines.append(f"Sessione più corta: {int(durata_corta_sec // 60)} min e {int(durata_corta_sec % 60)} sec (il {sessione_corta['timestamp_iso'].strftime('%d/%m/%Y')}).")
    # Trnsl('longest_session_info', min=.., sec=.., date=...)
    report_lines.append(f"Sessione più lunga: {int(durata_lunga_sec // 60)} min e {int(durata_lunga_sec % 60)} sec (il {sessione_lunga['timestamp_iso'].strftime('%d/%m/%Y')}).")

    # --- Distribuzione del tempo di allenamento totale ---
    report_lines.append("\n--- Distribuzione Tempo Totale di Allenamento ---") # Trnsl('total_training_time_dist_title')

    # Raggruppa per ora e somma le durate
    durata_per_ora = df.groupby(df['timestamp_iso'].dt.hour)['duration_seconds'].sum()
    ora_piu_dedizione = durata_per_ora.idxmax()
    tempo_ora_sec = durata_per_ora.max()
    # Trnsl('peak_duration_hour', hour=..., min=..., sec=...)
    report_lines.append(f"Ora di maggiore dedizione: {ora_piu_dedizione:02d}:00, con un totale di {int(tempo_ora_sec // 60)} min e {int(tempo_ora_sec % 60)} sec di pratica.")

    # Raggruppa per giorno della settimana
    giorni_raw = Trnsl('giorni_settimana_dict', lang=lang)
    giorni = {int(k): v for k, v in giorni_raw.items()}
    durata_per_giorno = df.groupby(df['timestamp_iso'].dt.dayofweek)['duration_seconds'].sum()
    giorno_piu_dedizione_idx = durata_per_giorno.idxmax()
    tempo_giorno_sec = durata_per_giorno.max()
    # Trnsl('peak_duration_day', day=..., min=..., sec=...)
    report_lines.append(f"Giorno di maggiore dedizione: {giorni[int(giorno_piu_dedizione_idx)]}, con un totale di {int(tempo_giorno_sec // 60)} min e {int(tempo_giorno_sec % 60)} sec di pratica.")
    # Raccogliamo tutti i dettagli degli item da tutte le sessioni
    all_item_details = []
    # Il titolo va messo prima del controllo, così appare sempre
    report_lines.append("\n--- Analisi Granulare Velocità/Accuratezza ---") # Trnsl('granular_analysis_title')
    all_item_details = []
    # Usiamo .get() per evitare errori se la colonna 'item_details' non esiste
    for session_details in df.get('item_details', pd.Series(dtype=object)).dropna():
        all_item_details.extend(session_details)
    if not all_item_details:
        report_lines.append(Trnsl('no_granular_data_found', lang=lang))
    if not all_item_details:
        report_lines.append(Trnsl('no_granular_data_found', lang=lang)) # Trnsl per "Nessun dato granulare disponibile."
    else:
        # Separiamo gli item corretti da quelli sbagliati
        correct_items = [item for item in all_item_details if item['correct']]
        wrong_items = [item for item in all_item_details if not item['correct']]
        # Calcoliamo le velocità medie per i due gruppi
        avg_wpm_correct = np.mean([item['wpm'] for item in correct_items]) if correct_items else 0
        avg_wpm_wrong = np.mean([item['wpm'] for item in wrong_items]) if wrong_items else 0
        report_lines.append(Trnsl('avg_wpm_on_correct_items', lang=lang, wpm=f"{avg_wpm_correct:.1f}"))
        report_lines.append(Trnsl('avg_wpm_on_wrong_items', lang=lang, wpm=f"{avg_wpm_wrong:.1f}"))
        if avg_wpm_correct > avg_wpm_wrong and wrong_items:
            report_lines.append(Trnsl('granular_conclusion_faster_when_correct', lang=lang))
        elif avg_wpm_wrong > avg_wpm_correct and correct_items:
            report_lines.append(Trnsl('granular_conclusion_slower_when_correct', lang=lang))
    return "\n".join(report_lines)

def genera_report_temporale_completo(dati_sessioni, Trnsl, lang) -> str:
    """
    Funzione direttore che orchestra tutte le analisi e assembla il report finale.

    Returns:
        str: Il report statistico testuale completo.
    """
    # Esegue qui i controlli e la preparazione dei dati
    if not dati_sessioni:
        return Trnsl('warning_no_log_data', lang=lang)
    # Crea e prepara il DataFrame
    df = pd.DataFrame(dati_sessioni)
    df['timestamp_iso'] = pd.to_datetime(df['timestamp_iso'])
    df = df.sort_values(by='timestamp_iso').reset_index(drop=True)
    # 2. Genera i report parziali chiamando le altre funzioni
    report_attivita = genera_report_attivita(df, Trnsl, lang)
    report_performance = genera_report_performance(df,Trnsl=Trnsl,lang=lang)
    report_avanzato = genera_report_avanzato(df,Trnsl=Trnsl,lang=lang)
    # 3. Assembla il report finale
    report_completo = "".join([
        report_attivita,
        report_performance,
        report_avanzato
    ])
    return report_completo