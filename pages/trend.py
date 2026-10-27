"""Athlete trend — key metrics across sessions."""

import dash
import pandas as pd
from dash import Input, Output, callback, dcc, html

from aspire_dash.charts import GRAPH_CONFIG
from aspire_dash.components import card, empty_state, filter_bar, graph_card, info_box
from dashboard import figures
from dashboard.ui import data_table, section_title
from throws import format_date, repository, slugify
from throws.metrics import trial_summary

dash.register_page(__name__, path="/trend", title="Athlete Trend", name="Athlete Trend")

METRICS = {
    "release_speed": "Release speed (m/s)",
    "release_angle": "Release angle (°)",
    "release_height": "Release height (m)",
    "release_v_vertical": "Vertical release velocity (m/s)",
    "release_v_horizontal": "Horizontal release velocity (m/s)",
    "total_time": "TO1 → Release time (s)",
    "dur::Touchdown 2 to Release": "TD2 → Release time (s)",
    "dv::Touchdown 2 to Release": "TD2 → Release speed gain (m/s)",
    "distance": "Distance (m)",
}


def layout(**kwargs):
    # Options are keyed by the name slug so spelling/case variants group together
    options = [{"label": name, "value": slugify(name)} for name in repository.list_athletes()]
    return html.Div([
        filter_bar([
            html.Div([
                html.Label("Athlete", className="control-label"),
                dcc.Dropdown(id="trend-athlete", options=options,
                             value=options[0]["value"] if options else None, clearable=False,
                             style={"minWidth": "260px"}),
            ]),
            html.Div([
                html.Label("Metric", className="control-label"),
                dcc.Dropdown(id="trend-metric", value="release_speed", clearable=False,
                             options=[{"label": v, "value": k} for k, v in METRICS.items()],
                             style={"minWidth": "300px"}),
            ]),
        ]),
        html.Div(id="trend-content"),
    ], style={"maxWidth": "1400px"})


@callback(Output("trend-content", "children"), Input("trend-athlete", "value"), Input("trend-metric", "value"))
def update_trend(athlete, metric):
    if not athlete:
        return card(empty_state("fa-solid fa-chart-line", "No athletes yet"))
    trials = [repository.load_trial(m.key) for m in repository.list_metas() if slugify(m.athlete) == athlete]
    df = pd.DataFrame([trial_summary(t) for t in trials]).sort_values(["date", "throw_label"])
    # Sorted on ISO dates above; shown as DD/MM/YYYY from here on
    df["date"] = df["date"].map(format_date).replace("", "No date")

    plot_df = df.dropna(subset=[metric])
    note = None
    if df["date"].nunique() < 2:
        note = info_box("Single session", "Trends become meaningful once two or more sessions are uploaded.")
    chart = (graph_card(figures.trend_chart(plot_df, metric, METRICS[metric]), title=METRICS[metric],
                        config=GRAPH_CONFIG)
             if not plot_df.empty else card(empty_state(text="No values for this metric")))

    return html.Div([
        note,
        chart,
        section_title("All trials", "fa-solid fa-table"),
        card([data_table(df, [
            ("date", "Date", None),
            ("throw_label", "Throw #", None),
            ("distance", "Distance (m)", ".2f"),
            ("release_speed", "Speed (m/s)", ".2f"),
            ("release_angle", "Angle (°)", ".1f"),
            ("release_height", "Height (m)", ".2f"),
            ("total_time", "TO1→REL (s)", ".3f"),
            ("dur::Touchdown 2 to Release", "TD2→REL (s)", ".3f"),
        ], sort_action="native")]),
    ])
