"""Trial report — single-throw analysis (replaces the per-trial Excel sheet)."""

import dash
from dash import Input, Output, State, callback, clientside_callback, dcc, html

from aspire_dash.charts import GRAPH_CONFIG
from aspire_dash.components import card, empty_state, filter_bar, graph_card, print_header, summary_card
from aspire_dash.theme import SLATE
from dashboard import figures
from dashboard.video import dartfish_embed_url
from dashboard.ui import (GRID_2, KPI_GRID, data_table, fmt, section_title, segment_legend,
                          trial_label, trial_options)
from throws import format_date, phase_table, release_params, repository
from throws.export import report_workbook

dash.register_page(__name__, path="/", title="Trial Report", name="Trial Report")

# Six KPI cards (min 170px + 12px gaps = 1080px) still fit one row at this width
PAGE_WIDTH = 1100
# Half the page (minus grid gap) less card padding and title, so the 2x2 cards stay square
TRAJECTORY_HEIGHT = (PAGE_WIDTH - 16) // 2 - 52


def layout(trial=None, **kwargs):
    options = trial_options()
    value = trial if trial in {o["value"] for o in options} else (options[0]["value"] if options else None)
    return html.Div([
        filter_bar([
            html.Div([
                html.Label("Trial", className="control-label"),
                dcc.Dropdown(id="trial-select", options=options, value=value, clearable=False,
                             style={"minWidth": "360px"}),
            ]),
            html.Div([
                html.Button([html.I(className="fa-solid fa-file-excel", style={"marginRight": "6px"}),
                             "Excel"], id="trial-export-xlsx", className="btn btn-light btn-sm"),
                html.Button([html.I(className="fa-solid fa-print", style={"marginRight": "6px"}),
                             "Print"], id="trial-print", className="btn btn-light btn-sm"),
                dcc.Download(id="trial-download"),
            ], style={"display": "flex", "gap": "8px", "marginLeft": "auto", "alignSelf": "flex-end"}),
        ]),
        dcc.Loading(html.Div(id="trial-content"), type="circle", color=SLATE["400"]),
    ], className="trial-page", style={"maxWidth": f"{PAGE_WIDTH}px"})


def _render(trial):
    rel = release_params(trial)
    phases = phase_table(trial)
    m = trial.meta

    kpis = html.Div([
        summary_card("Release speed", fmt(rel["speed"], 2, " m/s"), icon="fa-solid fa-gauge-high"),
        summary_card("Release angle", fmt(rel["angle"], 1, "°"), icon="fa-solid fa-angle-up"),
        summary_card("Vertical velocity", fmt(rel["v_vertical"], 2, " m/s"), icon="fa-solid fa-arrow-up"),
        summary_card("Horz. velocity", fmt(rel["v_horizontal"], 2, " m/s"),
                     icon="fa-solid fa-arrow-right"),
        summary_card("Release height", fmt(rel["height"], 2, " m"), icon="fa-solid fa-ruler-vertical"),
        summary_card("TO1 → Release", fmt(phases["duration"].sum(), 2, " s"), icon="fa-solid fa-stopwatch"),
    ], style=KPI_GRID)

    trajectories = html.Div([
        graph_card(figures.trajectory_view(trial, "ap", "ml", height=TRAJECTORY_HEIGHT),
                   title="Overhead view (AP–ML)", config=GRAPH_CONFIG),
        graph_card(figures.trajectory_view(trial, "ap", "vt", height=TRAJECTORY_HEIGHT),
                   title="Side-on view (AP–VT)", config=GRAPH_CONFIG),
        graph_card(figures.trajectory_view(trial, "ml", "vt", height=TRAJECTORY_HEIGHT),
                   title="Front-on view (ML–VT)", config=GRAPH_CONFIG),
        graph_card(figures.speed_time(trial, height=TRAJECTORY_HEIGHT),
                   title=f"{trial.implement} speed", config=GRAPH_CONFIG),
    ], style=GRID_2)

    phase_section = html.Div([
        card([
            data_table(phases, [
                ("phase", "Phase", None),
                ("events", "Events", None),
                ("duration", "Duration (s)", ".2f"),
                ("duration_pct", "Share (%)", ".1f"),
                ("speed_change", "Δ Speed (m/s)", ".2f"),
                ("cumulative", "Cumulative (s)", ".2f"),
            ]),
        ]),
        graph_card(figures.phase_timeline([(m.short_label, phases)]), title="Phase timeline",
                   config=GRAPH_CONFIG),
    ])

    extra = html.Div([
        graph_card(figures.velocity_components(trial), title="Velocity components", config=GRAPH_CONFIG),
        graph_card(figures.trajectory_3d(trial), title="3D path (drag to rotate)",
                   config={"displayModeBar": False}),
    ], style=GRID_2)

    return html.Div([
        print_header(title="Aspire Biomechanics Throw Analysis", subtitle=trial_label(m)),
        html.Div([
            html.H2(m.display_name, style={"fontSize": "22px", "fontWeight": "700", "margin": 0,
                                           "color": SLATE["800"]}),
            html.Div(" · ".join(filter(None, [
                format_date(m.date), f"Throw {m.throw_label}" if m.throw_label else None,
                trial.implement, f"{m.distance:.2f} m" if m.distance else None,
            ])), style={"color": SLATE["500"], "fontSize": "13px", "marginTop": "2px"}),
        ], style={"marginBottom": "16px"}),
        kpis,
        section_title("Path and Speed", "fa-solid fa-route"),
        segment_legend(),
        trajectories,
        # Print (A4 portrait): page 1 = KPIs + path/speed, page 2 = support phases;
        # velocity and video stay screen-only
        html.Div([section_title("Support phases", "fa-solid fa-shoe-prints"), phase_section],
                 className="print-page-break"),
        html.Div([section_title("Velocity and 3D Path", "fa-solid fa-cube"), extra], className="no-print"),
        *_video_section(m.video),
    ])


def _video_section(link: str) -> list:
    """Dartfish player at the bottom of the report; nothing when no video is linked."""
    embed_url = dartfish_embed_url(link)
    if not embed_url:
        return []
    player = html.Div(
        html.Iframe(src=embed_url, allow="fullscreen",
                    style={"position": "absolute", "inset": 0, "width": "100%", "height": "100%",
                           "border": "none"}),
        # 16:9 box that scales with the card width
        style={"position": "relative", "paddingBottom": "56.25%", "background": SLATE["100"],
               "borderRadius": "8px", "overflow": "hidden"},
    )
    # Embedded players cannot be printed, so the whole section is left out of print
    return [html.Div([section_title("Video", "fa-solid fa-video"), card(player)], className="no-print")]


@callback(
    Output("trial-content", "children"),
    Input("trial-select", "value"),
)
def update_trial(key):
    if not key:
        return card(empty_state("fa-solid fa-file-circle-plus", "No trials yet",
                                "Upload a Simi .txt export on the Upload Data page"))
    try:
        trial = repository.load_trial(key)
    except Exception as exc:  # malformed file on disk
        return card(empty_state("fa-solid fa-triangle-exclamation", f"Could not load {key}", str(exc)))
    return _render(trial)


@callback(
    Output("trial-download", "data"),
    Input("trial-export-xlsx", "n_clicks"),
    State("trial-select", "value"),
    prevent_initial_call=True,
)
def export_trial(_, key):
    if not key:
        return dash.no_update
    content = report_workbook([repository.load_trial(key)])
    return dcc.send_bytes(content, f"{key}_report.xlsx")


clientside_callback(
    "function(n) { if (n) { window.print(); } return window.dash_clientside.no_update; }",
    Output("trial-print", "title"),
    Input("trial-print", "n_clicks"),
    prevent_initial_call=True,
)
