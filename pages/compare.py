"""Session compare — overlay up to five trials."""

import dash
import pandas as pd
from dash import Input, Output, State, callback, dcc, html

from aspire_dash.charts import GRAPH_CONFIG
from aspire_dash.components import card, empty_state, filter_bar, graph_card
from aspire_dash.theme import SLATE
from dashboard import figures
from dashboard.ui import GRID_2, compare_labels, data_table, section_title, trial_options
from throws import PHASES, format_date, phase_table, repository
from throws.export import report_workbook
from throws.metrics import trial_summary

dash.register_page(__name__, path="/compare", title="Session Compare", name="Session Compare")

MAX_TRIALS = len(figures.TRIAL_COLORS)


def _default_selection():
    metas = repository.list_metas()
    if not metas:
        return []
    latest = max(m.date for m in metas)
    keys = [m.key for m in sorted(metas, key=lambda m: (m.throw_label, m.key)) if m.date == latest]
    return keys[:MAX_TRIALS]


def layout(**kwargs):
    return html.Div([
        filter_bar([
            html.Div([
                html.Label(f"Trials (max {MAX_TRIALS})", className="control-label"),
                dcc.Dropdown(id="cmp-select", options=trial_options(), value=_default_selection(),
                             multi=True, style={"minWidth": "520px"}),
            ], style={"flex": "1"}),
            html.Div([
                html.Button([html.I(className="fa-solid fa-file-excel", style={"marginRight": "6px"}),
                             "Excel"], id="cmp-export-xlsx", className="btn btn-light btn-sm"),
                dcc.Download(id="cmp-download"),
            ], style={"alignSelf": "flex-end"}),
        ]),
        dcc.Loading(html.Div(id="cmp-content"), type="circle", color=SLATE["400"]),
    ], style={"maxWidth": "1400px"})


@callback(Output("cmp-select", "value"), Input("cmp-select", "value"), prevent_initial_call=True)
def limit_selection(keys):
    if keys and len(keys) > MAX_TRIALS:
        return keys[:MAX_TRIALS]
    return dash.no_update


@callback(Output("cmp-content", "children"), Input("cmp-select", "value"))
def update_compare(keys):
    keys = (keys or [])[:MAX_TRIALS]
    if not keys:
        return card(empty_state("fa-solid fa-code-compare", "Select trials to compare"))

    trials = [repository.load_trial(k) for k in keys]
    phases = [phase_table(t) for t in trials]
    summary = pd.DataFrame([trial_summary(t, ph) for t, ph in zip(trials, phases)])
    labels = compare_labels([t.meta for t in trials])
    summary["label"] = labels
    summary["date"] = summary["date"].map(format_date)
    best = int(summary["release_speed"].idxmax())

    release_table = card([
        data_table(summary, [
            ("label", "Trial", None),
            ("date", "Date", None),
            ("release_speed", "Speed (m/s)", ".2f"),
            ("release_angle", "Angle (°)", ".1f"),
            ("release_v_vertical", "V vert (m/s)", ".2f"),
            ("release_v_horizontal", "V horz (m/s)", ".2f"),
            ("release_height", "Height (m)", ".2f"),
            ("peak_speed_before_release", "Peak speed (m/s)", ".2f"),
            ("total_time", "TO1→REL (s)", ".2f"),
        ], highlight_row=best),
        html.Div("Highlighted row: highest release speed", style={
            "fontSize": "12px", "color": SLATE["400"], "marginTop": "8px"}),
    ])

    # Per-phase duration / speed change are already in the summary as dur::<phase> / dv::<phase>
    phase_cols = [("label", "Trial", None)]
    for name, _, _ in PHASES:
        phase_cols += [(f"dur::{name}", f"{name} (s)", ".2f"), (f"dv::{name}", f"{name} Δv", ".2f")]

    return html.Div([
        section_title("Release parameters", "fa-solid fa-gauge-high"),
        release_table,
        section_title("Speed & rhythm", "fa-solid fa-wave-square"),
        html.Div([
            graph_card(figures.compare_speed(trials, labels), title="Speed aligned at release",
                       config=GRAPH_CONFIG),
            graph_card(figures.phase_timeline(list(zip(labels, phases))),
                       title="Phase timeline", config=GRAPH_CONFIG),
        ], style=GRID_2),
        card([data_table(summary, phase_cols)]),
    ])


@callback(
    Output("cmp-download", "data"),
    Input("cmp-export-xlsx", "n_clicks"),
    State("cmp-select", "value"),
    prevent_initial_call=True,
)
def export_compare(_, keys):
    if not keys:
        return dash.no_update
    content = report_workbook([repository.load_trial(k) for k in keys[:MAX_TRIALS]])
    return dcc.send_bytes(content, "throws_compare.xlsx")
