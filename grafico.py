# CWapu, il report storico in forma di grafico.
# Autori: Gabriele Battaglia (IZ4APU) & ClaudIA (Claude Opus 5, modalita' UltraCode).
# 06/09/2026: estratto da cwapu.py, dove occupava un ottavo dell'applicazione.

"""Disegna in un file SVG le statistiche del blocco di esercizi appena chiuso.

Sono le stesse informazioni del rapporto HTML e del rapporto testuale della
timeline, messe in forma di grafico per chi le legge con gli occhi. Chi usa un
lettore di schermo non perde niente restando sugli altri due.

matplotlib si importa dentro la funzione: e' pesante e serve soltanto qui, e
un utente che non generi mai un rapporto grafico non deve pagarne il costo.
La funzione di traduzione arriva come parametro, come per timeline, cosi' il
modulo non dipende da chi lo chiama.
"""

import datetime as dt

from wilson import wilson_score_lower_bound, wilson_score_upper_bound


def crea_report_grafico(current_aggregates, previous_aggregates, g_val, x_val, num_sessions_in_report, output_filename, _, lang="en"):
    """
    Crea un report grafico delle statistiche storiche e lo salva come immagine.
    """
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError as e_import:
        print(_("matplotlib non trovato, il report grafico non si genera: {errore}").format(errore=e_import))
        return
    except Exception as e_import:  # noqa: BLE001 -- matplotlib puo' fallire in molti modi diversi
        print(_("Errore durante l'importazione di matplotlib: {errore}").format(errore=e_import))
        return
    plt.style.use("dark_background")
    fig_width_inches = 10
    fig_height_inches = 16
    text_color = "white"
    color_error_very_high = "#B22222"
    color_error_high = "#FF4136"
    color_warning = "#FF851B"
    color_neutral = "#FFDC00"
    color_good = "#2ECC40"
    color_excellent = "#7FDBFF"
    fig = plt.figure(figsize=(fig_width_inches, fig_height_inches))
    fig.patch.set_facecolor("#222222")
    y_cursor = 0.98
    line_height_fig = 0.03
    section_spacing_fig = 0.04
    title_text = _("CWAPU - Report Statistiche Storiche Esercizi Rx")
    fig.text(0.5, y_cursor, title_text, color=text_color, ha="center", va="top", fontsize=16, weight="bold")
    y_cursor -= line_height_fig * 1.5
    subtitle_text = _("Statistiche basate su {count} esercizi").format(count=num_sessions_in_report) + f" (G={g_val}, X={x_val})"
    fig.text(0.5, y_cursor, subtitle_text, color=text_color, ha="center", va="top", fontsize=12)
    y_cursor -= line_height_fig
    generation_time_text = _("Report generato il: {}").format(dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    fig.text(0.5, y_cursor, generation_time_text, color=text_color, ha="center", va="top", fontsize=10, style="italic")
    y_cursor -= section_spacing_fig * 1.5

    def get_delta_color_and_symbol(delta_value, higher_is_better=True, tolerance=0.01):
        symbol = ""
        color_to_use = color_neutral
        if higher_is_better:
            if delta_value > tolerance:
                color_to_use = color_good
                symbol = "▲"
            elif delta_value < -tolerance:
                color_to_use = color_error_high
                symbol = "▼"
            else:
                symbol = "~"
        elif delta_value < -tolerance:
            color_to_use = color_good
            symbol = "▼"
        elif delta_value > tolerance:
            color_to_use = color_error_high
            symbol = "▲"
        else:
            symbol = "~"
        return (color_to_use, symbol)

    fig.text(0.5, y_cursor, _("Statistiche Velocità Complessive"), color=color_excellent, ha="center", va="top", fontsize=14, weight="bold")
    y_cursor -= line_height_fig * 2.0
    wpm_metrics_data = [
        {"label_key": _("WPM Min"), "curr": current_aggregates["wpm_min_overall"], "prev": previous_aggregates["wpm_min_overall"] if previous_aggregates else None, "higher_better": True},
        {
            "label_key": _("WPM Media"),
            "curr": current_aggregates["wpm_avg_of_session_avgs"],
            "prev": previous_aggregates["wpm_avg_of_session_avgs"] if previous_aggregates else None,
            "higher_better": True,
        },
        {"label_key": _("WPM Max"), "curr": current_aggregates["wpm_max_overall"], "prev": previous_aggregates["wpm_max_overall"] if previous_aggregates else None, "higher_better": True},
    ]
    num_wpm_metrics = len(wpm_metrics_data)
    height_per_wpm_metric_group_fig = 0.07
    ax_wpm_needed_height_fig = height_per_wpm_metric_group_fig * num_wpm_metrics
    ax_wpm_left = 0.2
    ax_wpm_width = 0.55
    ax_wpm_bottom = y_cursor - ax_wpm_needed_height_fig
    ax_variation_text_left = ax_wpm_left + ax_wpm_width + 0.03
    ax_wpm = fig.add_axes([ax_wpm_left, ax_wpm_bottom, ax_wpm_width, ax_wpm_needed_height_fig])
    ax_wpm.set_facecolor("#383c44")
    wpm_scale_min = 0
    wpm_scale_max = 100
    ax_wpm.set_xlim(wpm_scale_min, wpm_scale_max)
    ax_wpm.set_xlabel("WPM", color=text_color, fontsize=10)
    ax_wpm.tick_params(axis="x", colors=text_color, labelsize=9)
    ax_wpm.spines["bottom"].set_color(text_color)
    ax_wpm.spines["top"].set_visible(False)
    ax_wpm.spines["right"].set_visible(False)
    ax_wpm.spines["left"].set_visible(False)
    y_tick_positions = np.arange(num_wpm_metrics)
    metric_labels = [m["label_key"] for m in wpm_metrics_data]  # <-- CORRETTO
    ax_wpm.set_yticks(y_tick_positions)
    ax_wpm.set_yticklabels(metric_labels[::-1])
    ax_wpm.tick_params(axis="y", colors=text_color, labelsize=10, length=0)
    ax_wpm.invert_yaxis()
    bar_draw_height = 0.35
    for i, metric in enumerate(wpm_metrics_data):
        y_group_center = y_tick_positions[i]
        ax_wpm.barh(y_group_center, wpm_scale_max - wpm_scale_min, height=bar_draw_height * 2.2, left=wpm_scale_min, color="#555555", edgecolor=text_color, linewidth=0.5, zorder=1, alpha=0.5)
        y_curr_bar_pos = y_group_center - bar_draw_height / 2.1
        ax_wpm.barh(y_curr_bar_pos, metric["curr"] - wpm_scale_min, height=bar_draw_height, left=wpm_scale_min, color=color_good, zorder=3, edgecolor=text_color, linewidth=0.5)
        ax_wpm.text(metric["curr"] + 0.015 * wpm_scale_max, y_curr_bar_pos, "{}".format(metric["curr"]), color=text_color, ha="left", va="center", fontsize=9, weight="bold")
        y_prev_bar_pos = y_group_center + bar_draw_height / 2.1
        if metric["prev"] is not None:
            ax_wpm.barh(y_prev_bar_pos, metric["prev"] - wpm_scale_min, height=bar_draw_height, left=wpm_scale_min, color=color_neutral, zorder=2, alpha=0.8, edgecolor=text_color, linewidth=0.5)
            ax_wpm.text(metric["prev"] + 0.015 * wpm_scale_max, y_prev_bar_pos, "{}".format(metric["prev"]), color=text_color, ha="left", va="center", fontsize=9)
        if metric["prev"] is not None:
            delta = metric["curr"] - metric["prev"]
            color_txt, symbol = get_delta_color_and_symbol(delta, higher_is_better=metric["higher_better"], tolerance=0.05)
            perc_delta_str = " ({}%)".format(delta / metric["prev"] * 100) if metric["prev"] != 0 else ""
            norm_y_in_ax = (y_group_center + 0.5) / num_wpm_metrics
            y_fig_coord_for_text = ax_wpm_bottom + (1 - norm_y_in_ax) * ax_wpm_needed_height_fig
            fig.text(ax_variation_text_left, y_fig_coord_for_text, f"{symbol} {delta}{perc_delta_str}", color=color_txt, ha="left", va="center", fontsize=10)
    if any(metric["prev"] is not None for metric in wpm_metrics_data):
        legend_elements = [plt.Rectangle((0, 0), 1, 1, color=color_good, label=_("Valore Attuale")), plt.Rectangle((0, 0), 1, 1, color=color_neutral, alpha=0.8, label=_("Valore Precedente"))]
        fig.legend(
            handles=legend_elements,
            loc="upper left",
            bbox_to_anchor=(ax_wpm_left + ax_wpm_width + 0.01, ax_wpm_bottom + ax_wpm_needed_height_fig + 0.03),
            fontsize=8,
            ncol=1,
            facecolor="#444444",
            edgecolor=text_color,
            labelcolor=text_color,
        )
    y_cursor = ax_wpm_bottom - section_spacing_fig
    fig.text(0.5, y_cursor, _("Statistiche Errori Complessive"), color=color_excellent, ha="center", va="top", fontsize=14, weight="bold")
    y_cursor -= line_height_fig * 1.2
    x_text_start = 0.1
    label_overall_err = _("Caratteri totali inviati (nel blocco)")
    value_overall_err_str = "{}".format(current_aggregates["total_chars_sent_overall"])
    fig.text(x_text_start, y_cursor, f"{label_overall_err}: {value_overall_err_str}", color=text_color, ha="left", va="top", fontsize=11)
    if previous_aggregates:
        prev_val = previous_aggregates["total_chars_sent_overall"]
        delta = current_aggregates["total_chars_sent_overall"] - prev_val
        perc_delta_str = f" ({delta / prev_val * 100}%)" if prev_val != 0 else ""
        fig.text(
            x_text_start + 0.4,
            y_cursor,
            _("vs. {prev_val} ({delta}{perc_delta_str})").format(prev_val=prev_val, delta=delta, perc_delta_str=perc_delta_str),
            color=color_neutral,
            ha="left",
            va="top",
            fontsize=10,
            style="italic",
        )
    y_cursor -= line_height_fig
    total_chars_curr = current_aggregates["total_chars_sent_overall"]
    total_errs_curr = current_aggregates["total_errors_chars_overall"]
    overall_error_rate_curr = total_errs_curr / total_chars_curr * 100 if total_chars_curr > 0 else 0.0
    label_overall_err = _("Tasso errore generale")
    value_overall_err_str = f"{overall_error_rate_curr}% ({total_errs_curr}/{total_chars_curr})"
    fig.text(x_text_start, y_cursor, f"{label_overall_err}: {value_overall_err_str}", color=text_color, ha="left", va="top", fontsize=11)
    if previous_aggregates:
        total_chars_prev = previous_aggregates["total_chars_sent_overall"]
        total_errs_prev = previous_aggregates["total_errors_chars_overall"]
        overall_error_rate_prev = total_errs_prev / total_chars_prev * 100 if total_chars_prev > 0 else 0.0
        delta_rate = overall_error_rate_curr - overall_error_rate_prev
        color, symbol = get_delta_color_and_symbol(delta_rate, higher_is_better=False)
        fig.text(
            x_text_start + 0.4,
            y_cursor,
            _("vs. {overall_error_rate_prev}% ({symbol} {delta_rate} punti %)").format(overall_error_rate_prev=overall_error_rate_prev, symbol=symbol, delta_rate=delta_rate),
            color=color,
            ha="left",
            va="top",
            fontsize=10,
            style="italic",
        )
    y_cursor -= section_spacing_fig
    fig.text(0.5, y_cursor, _("Dettaglio errori per carattere"), color=color_excellent, ha="center", va="top", fontsize=14, weight="bold")
    y_cursor -= line_height_fig * 0.06
    top_n_errors_to_display = 10
    if current_aggregates["aggregated_errors_detail"]:
        sorted_char_errors = sorted(current_aggregates["aggregated_errors_detail"].items(), key=lambda item: (-item[1], item[0]))[:top_n_errors_to_display]
        error_chars = [item[0].upper() for item in sorted_char_errors]
        error_counts = [item[1] for item in sorted_char_errors]
        if error_counts:
            height_per_error_bar_fig = 0.035
            ax_err_needed_height_fig = height_per_error_bar_fig * len(error_chars) + 0.03
            ax_err_left = 0.1
            ax_err_width = 0.8
            ax_err_bottom = y_cursor - ax_err_needed_height_fig
            ax_char_err = fig.add_axes([ax_err_left, ax_err_bottom, ax_err_width, ax_err_needed_height_fig])
            ax_char_err.set_facecolor("#383c44")
            y_positions = np.arange(len(error_chars))
            bar_draw_visual_height = 0.6
            max_error_val = max(error_counts) if error_counts else 1
            plot_area_width = max_error_val * 1.1
            ax_char_err.set_xlim(0, plot_area_width)
            left_offsets = [(plot_area_width - count) / 2 for count in error_counts]
            bar_colors_list = []
            for i in range(len(sorted_char_errors)):
                if i < 3:
                    bar_colors_list.append(color_error_high)
                elif i < 7:
                    bar_colors_list.append(color_neutral)
                else:
                    bar_colors_list.append(color_good)
            bars = ax_char_err.barh(y_positions, error_counts, height=bar_draw_visual_height, left=left_offsets, color=bar_colors_list, edgecolor=text_color, linewidth=0.5, zorder=2)
            ax_char_err.set_yticks(y_positions)
            ax_char_err.set_yticklabels(error_chars, color=text_color, fontsize=9, weight="bold")
            ax_char_err.invert_yaxis()
            ax_char_err.tick_params(axis="y", length=0)
            ax_char_err.set_xticks([])
            ax_char_err.set_xlabel("")
            ax_char_err.spines["bottom"].set_visible(False)
            ax_char_err.spines["top"].set_visible(False)
            ax_char_err.spines["right"].set_visible(False)
            ax_char_err.spines["left"].set_visible(False)
            if error_counts:
                longest_bar_width = error_counts[0]
                left_longest_bar = left_offsets[0]
                right_longest_bar = left_offsets[0] + longest_bar_width
                y_top_line = y_positions[0] + bar_draw_visual_height / 2
                y_bottom_line = y_positions[-1] - bar_draw_visual_height / 2
                ax_char_err.vlines(x=left_longest_bar, ymin=y_bottom_line, ymax=y_top_line, color="white", linestyle="--", linewidth=0.75, alpha=0.7, zorder=1)
                ax_char_err.vlines(x=right_longest_bar, ymin=y_bottom_line, ymax=y_top_line, color="white", linestyle="--", linewidth=0.75, alpha=0.7, zorder=1)
            total_chars_in_block_for_perc = current_aggregates["total_chars_sent_overall"]
            aggregated_sent_chars_for_perc = current_aggregates.get("aggregated_sent_chars_detail", {})
            for i, bar_patch in enumerate(bars):
                char_l = error_chars[i].lower()
                count = error_counts[i]
                perc_vs_total = count / total_chars_in_block_for_perc * 100 if total_chars_in_block_for_perc > 0 else 0.0
                errori = count
                inviati = aggregated_sent_chars_for_perc.get(char_l, 0)
                limite_inferiore = wilson_score_lower_bound(errori, inviati) * 100
                limite_superiore = wilson_score_upper_bound(errori, inviati) * 100
                annotation_text = _(" {errori} errori su {inviati}. Tasso err. ~ [{inf:.1f}% - {sup:.1f}%]").format(errori=errori, inviati=inviati, inf=limite_inferiore, sup=limite_superiore)
                text_x_pos = bar_patch.get_x() + bar_patch.get_width() + plot_area_width * 0.01
                ax_char_err.text(text_x_pos, bar_patch.get_y() + bar_patch.get_height() / 2, annotation_text, va="center", ha="left", color=text_color, fontsize=8)
            y_cursor = ax_err_bottom - section_spacing_fig
        else:
            no_detail_errors_text = _("Nessun errore di dettaglio da visualizzare nel grafico.")
            fig.text(0.5, y_cursor - line_height_fig, no_detail_errors_text, color=text_color, ha="center", va="top", fontsize=10, style="italic")
            y_cursor -= line_height_fig * 2 + section_spacing_fig
    else:
        no_errors_text = _("Nessun errore registrato per questo blocco di sessioni.")
        fig.text(0.5, y_cursor - line_height_fig, no_errors_text, color=text_color, ha="center", va="top", fontsize=10, style="italic")
        y_cursor -= line_height_fig * 2 + section_spacing_fig
    if previous_aggregates and previous_aggregates["num_sessions_in_block"] > 0:
        fig.text(0.5, y_cursor, _("Variazioni Dettaglio Errori per Carattere"), color=color_excellent, ha="center", va="top", fontsize=14, weight="bold")
        y_cursor -= line_height_fig * 0.06
        if "sorted_char_errors" not in locals() and "error_chars" not in locals():
            _potential_chars = list(set(current_aggregates["aggregated_errors_detail"].keys()) | set(previous_aggregates["aggregated_errors_detail"].keys()))
            _sorted_potential_chars = sorted(_potential_chars, key=lambda char_key: (-current_aggregates["aggregated_errors_detail"].get(char_key, 0), char_key))
            chars_for_variation_plot = [item.lower() for item in _sorted_potential_chars][:top_n_errors_to_display]
        elif "error_chars" in locals():
            chars_for_variation_plot = [char.lower() for char in error_chars]
        else:
            chars_for_variation_plot = []
        variation_data_list = []
        for char_lcase in chars_for_variation_plot:
            curr_count = current_aggregates["aggregated_errors_detail"].get(char_lcase, 0)
            prev_count = previous_aggregates["aggregated_errors_detail"].get(char_lcase, 0)
            curr_total_sent = current_aggregates.get("aggregated_sent_chars_detail", {}).get(char_lcase, 0)
            prev_total_sent = previous_aggregates.get("aggregated_sent_chars_detail", {}).get(char_lcase, 0)
            if curr_total_sent > 0 or prev_total_sent > 0:
                curr_rate_spec = curr_count / curr_total_sent * 100 if curr_total_sent > 0 else 0.0
                prev_rate_spec = prev_count / prev_total_sent * 100 if prev_total_sent > 0 else 0.0
                delta = curr_rate_spec - prev_rate_spec
                variation_data_list.append({"char": char_lcase.upper(), "delta": delta})
        if variation_data_list:
            deltas_values = [item["delta"] for item in variation_data_list]
            bar_colors_variation = []
            stable_threshold_abs = 1.0
            significant_improvements = sorted([d for d in deltas_values if d < -stable_threshold_abs])
            significant_worsenings = sorted([d for d in deltas_values if d > stable_threshold_abs])
            split_azzurro_verde = np.median(significant_improvements) if significant_improvements else -stable_threshold_abs
            split_arancione_rossocupo = np.median(significant_worsenings) if significant_worsenings else stable_threshold_abs
            for d_val in deltas_values:
                if d_val < -stable_threshold_abs:
                    if d_val <= split_azzurro_verde and significant_improvements:
                        bar_colors_variation.append(color_excellent)
                    else:
                        bar_colors_variation.append(color_good)
                elif d_val > stable_threshold_abs:
                    if d_val >= split_arancione_rossocupo and significant_worsenings:
                        bar_colors_variation.append(color_error_very_high)
                    else:
                        bar_colors_variation.append(color_warning)
                else:
                    bar_colors_variation.append(color_neutral)
            height_per_var_bar_fig = 0.035
            ax_var_needed_height_fig = height_per_var_bar_fig * len(variation_data_list) + 0.05
            ax_var_left = 0.15
            ax_var_width = 0.7
            ax_var_bottom = y_cursor - ax_var_needed_height_fig
            ax_err_var = fig.add_axes([ax_var_left, ax_var_bottom, ax_var_width, ax_var_needed_height_fig])
            ax_err_var.set_facecolor("#383c44")
            plot_chars = [item["char"] for item in variation_data_list]
            plot_deltas = [item["delta"] for item in variation_data_list]
            y_var_positions = np.arange(len(plot_chars))
            max_abs_delta_val = max(abs(d) for d in plot_deltas) if plot_deltas else 1.0
            axis_plot_limit = max_abs_delta_val * 1.15
            ax_err_var.set_xlim(-axis_plot_limit, axis_plot_limit)
            ax_err_var.axvline(0, color="white", linestyle=":", linewidth=0.7, alpha=0.7, zorder=1)
            ax_err_var.axvline(-max_abs_delta_val, color="white", linestyle="--", linewidth=0.75, alpha=0.5, zorder=1)
            ax_err_var.axvline(max_abs_delta_val, color="white", linestyle="--", linewidth=0.75, alpha=0.5, zorder=1)
            for i in range(len(plot_chars)):
                delta_val = plot_deltas[i]
                bar_w = abs(delta_val)
                bar_l = min(0, delta_val)
                ax_err_var.barh(y_var_positions[i], bar_w, left=bar_l, color=bar_colors_variation[i], height=0.5, edgecolor=text_color, linewidth=0.5, zorder=2)
                text_x_offset = axis_plot_limit * 0.02
                ha_val = "right" if delta_val < 0 else "left"
                text_x = delta_val - text_x_offset if delta_val < 0 else delta_val + text_x_offset
                ax_err_var.text(text_x, y_var_positions[i], f"{delta_val}%", va="center", ha=ha_val, color=text_color, fontsize=8)
            ax_err_var.set_yticks(y_var_positions)
            ax_err_var.set_yticklabels(plot_chars, color=text_color, fontsize=9)
            ax_err_var.invert_yaxis()
            ax_err_var.tick_params(axis="y", length=0)
            ax_err_var.set_xlabel(_("Variaz. err. per carattere (punti percentuali)"), color=text_color, fontsize=10)
            ax_err_var.tick_params(axis="x", colors=text_color, labelsize=9)
            ax_err_var.spines["bottom"].set_color(text_color)
            ax_err_var.spines["top"].set_visible(False)
            ax_err_var.spines["right"].set_visible(False)
            ax_err_var.spines["left"].set_visible(False)
            y_cursor = ax_var_bottom - section_spacing_fig
        else:
            fig.text(
                0.5, y_cursor - line_height_fig, _("Nessuna variazione significativa degli errori per carattere da visualizzare."), color=text_color, ha="center", va="top", fontsize=10, style="italic"
            )
            y_cursor -= line_height_fig * 2 + section_spacing_fig
    else:
        fig.text(0.5, y_cursor - line_height_fig, _("Dati precedenti non disponibili per calcolare le variazioni."), color=text_color, ha="center", va="top", fontsize=10, style="italic")
        y_cursor -= line_height_fig * 2 + section_spacing_fig
    try:
        plt.savefig(output_filename, format="svg", bbox_inches="tight", pad_inches=0.3, facecolor=fig.get_facecolor())
        plt.close(fig)
    except (OSError, ValueError) as e:
        if "fig" in locals() and fig:
            plt.close(fig)
        print(_("Errore nel salvataggio del file grafico: {errore}").format(errore=e))
