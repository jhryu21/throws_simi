"""Upload Simi exports and manage trial metadata."""

import base64

import dash
import pandas as pd
from dash import Input, Output, State, callback, dash_table, dcc, html

from aspire_dash.components import card, info_box
from aspire_dash.theme import FONT_FAMILY, SLATE
from dashboard.ui import fmt, section_title, trial_label
from dashboard.video import resolve_video_link
from throws import (DISCIPLINES, Trial, TrialMeta, format_date, match_discipline, parse_date,
                    parse_filename, release_params, repository, slugify)

dash.register_page(__name__, path="/upload", title="Upload Data", name="Upload Data")

META_FIELDS = ["athlete", "discipline", "date", "throw_label", "distance", "notes", "video"]
FIELD_LABELS = {
    "athlete": "Athlete", "discipline": "Event", "date": "Date",
    "throw_label": "Throw #", "distance": "Distance (m)", "notes": "Notes",
    "video": "Dartfish video",
}
INVALID_VIDEO = ("Video link not recognised. Paste the Dartfish share link (dartfi.sh/...) "
                 "or the embed code from Share > Embed.")


def _input(field, placeholder="", type_="text", **kwargs):
    return html.Div([
        html.Label(FIELD_LABELS[field], className="control-label"),
        dcc.Input(id=f"up-{field}", type=type_, placeholder=placeholder, debounce=True,
                  className="form-control", style={"fontSize": "13px"}, **kwargs),
    ])


def _athlete_options():
    return [html.Option(value=name) for name in repository.list_athletes()]


def _match_athlete(file_athlete: str) -> str:
    """Map the athlete part of a file name onto a stored athlete name.

    "Ibrahim" matches "Ibrahim Hamdan" when it is the only stored name
    containing that word; otherwise the file name part is used as is.
    """
    word = slugify(file_athlete)
    names = repository.list_athletes()
    exact = [n for n in names if slugify(n) == word]
    if exact:
        return exact[0]
    partial = [n for n in names if word in slugify(n).split("-")]
    return partial[0] if len(partial) == 1 else file_athlete


def _meta_table_data():
    # "key" is carried in the row data (not shown) to address edits and deletes
    return [{"key": m.key, **{f: getattr(m, f) for f in META_FIELDS}, "date": format_date(m.date)}
            for m in repository.list_metas()]


def layout(**kwargs):
    return html.Div([
        info_box("File format", [
            html.Div("Simi Motion trajectory export (.txt, comma separated): "
                     "Time, X, Y, Z, v(X), v(Y), v(Z), v(abs), Event. "
                     "The first six Event values are Start, Toe-off 1, Toe-off 2, Touchdown 1, "
                     "Touchdown 2, Release."),
            html.Div("Each upload is stored as a new trial. A file name like Ibrahim_517.txt "
                     "pre-fills the athlete, matched to stored athlete names.",
                     style={"marginTop": "4px"}),
        ]),
        card([
            dcc.Upload(
                id="up-file",
                children=html.Div([
                    html.I(className="fa-solid fa-cloud-arrow-up",
                           style={"fontSize": "28px", "color": SLATE["400"], "marginBottom": "6px"}),
                    html.Div("Drag & drop a Simi .txt file, or click to browse",
                             style={"color": SLATE["500"], "fontSize": "13px"}),
                ], style={"display": "flex", "flexDirection": "column", "alignItems": "center"}),
                accept=".txt",
                style={"border": f"2px dashed {SLATE['300']}", "borderRadius": "10px",
                       "padding": "28px", "cursor": "pointer", "background": SLATE["50"]},
            ),
            dcc.Store(id="up-store"),
            html.Div(id="up-preview", style={"marginTop": "16px"}),
            html.Datalist(id="up-athlete-list", children=_athlete_options()),
            html.Div([
                _input("athlete", "e.g. Ibrahim Hamdan", list="up-athlete-list"),
                html.Div([
                    html.Label(FIELD_LABELS["discipline"], className="control-label"),
                    dcc.Dropdown(id="up-discipline", options=list(DISCIPLINES), clearable=False,
                                 placeholder="Select…", style={"fontSize": "13px"}),
                ]),
                html.Div([
                    html.Label(FIELD_LABELS["date"], className="control-label"),
                    # Calendar shown as DD/MM/YYYY; the value stays ISO YYYY-MM-DD
                    dcc.DatePickerSingle(id="up-date", display_format="DD/MM/YYYY",
                                         first_day_of_week=1, clearable=True,
                                         placeholder="DD/MM/YYYY"),
                ]),
                _input("throw_label", "e.g. 16:17"),
                _input("distance", "optional", "number"),
                _input("notes", "optional"),
                html.Div(_input("video", "optional · Dartfish share link or embed code"),
                         style={"gridColumn": "span 2"}),
            ], style={"display": "grid", "gridTemplateColumns": "repeat(auto-fill, minmax(180px, 1fr))",
                      "gap": "12px", "marginTop": "16px"}),
            html.Div([
                html.Button([html.I(className="fa-solid fa-floppy-disk", style={"marginRight": "6px"}),
                             "Save trial"], id="up-save", className="btn btn-primary btn-sm", disabled=True),
                html.Span(id="up-status", style={"fontSize": "13px", "marginLeft": "12px"}),
            ], style={"marginTop": "16px", "display": "flex", "alignItems": "center"}),
        ]),
        section_title("Stored trials", "fa-solid fa-database"),
        card([
            dash_table.DataTable(
                id="up-meta-table",
                data=_meta_table_data(),
                columns=[{"id": f, "name": FIELD_LABELS[f],
                          **({"type": "numeric"} if f == "distance" else {}),
                          **({"presentation": "dropdown"} if f == "discipline" else {})}
                         for f in META_FIELDS],
                dropdown={"discipline": {"options": [{"label": d, "value": d} for d in DISCIPLINES],
                                         "clearable": False}},
                editable=True,
                row_selectable="multi",
                style_as_list_view=True,
                style_table={"overflowX": "auto"},
                style_header={"fontWeight": "600", "fontSize": "12px", "color": SLATE["500"],
                              "backgroundColor": "white"},
                style_cell={"fontFamily": FONT_FAMILY, "fontSize": "13px", "padding": "8px 12px",
                            "textAlign": "left", "border": "none"},
                style_data_conditional=[{"if": {"column_editable": True},
                                         "backgroundColor": "#fbfdff"}],
            ),
            html.Div([
                html.Button("Save metadata changes", id="up-meta-save", className="btn btn-light btn-sm"),
                html.Button("Delete selected", id="up-meta-delete", className="btn btn-light btn-sm",
                            style={"color": "#dc2626"}),
                html.Span(id="up-meta-status", style={"fontSize": "13px"}),
            ], style={"display": "flex", "gap": "8px", "alignItems": "center", "marginTop": "12px"}),
        ]),
    ], style={"maxWidth": "1200px"})


@callback(
    Output("up-store", "data"),
    Output("up-preview", "children"),
    Output("up-athlete", "value"),
    Output("up-discipline", "value"),
    Output("up-save", "disabled"),
    Input("up-file", "contents"),
    State("up-file", "filename"),
    prevent_initial_call=True,
)
def on_upload(contents, filename):
    raw = base64.b64decode(contents.split(",", 1)[1])
    parts = parse_filename(filename)
    try:
        trial = Trial.from_source(raw, meta=TrialMeta(athlete=parts["athlete"]))
    except Exception as exc:
        err = html.Div([html.I(className="fa-solid fa-triangle-exclamation", style={"marginRight": "6px"}),
                        f"{filename}: {exc}"], style={"color": "#dc2626", "fontSize": "13px"})
        return None, err, None, None, True

    rel = release_params(trial)
    preview = html.Div([
        html.I(className="fa-solid fa-circle-check", style={"color": "#16a34a", "marginRight": "6px"}),
        html.Strong(filename),
        html.Span(f" · {trial.implement} · {trial.fs:.0f} Hz · {len(trial.data)} frames · "
                  f"release {fmt(rel['speed'], 2, ' m/s')} @ {fmt(rel['angle'], 1, '°')}, "
                  f"height {fmt(rel['height'], 2, ' m')}",
                  style={"color": SLATE["600"]}),
    ], style={"fontSize": "13px"})
    store = {"filename": filename, "content": contents.split(",", 1)[1]}
    # Pre-select the event from the Simi object name (e.g. "Discus X"); None if unknown
    discipline = match_discipline(trial.implement) or None
    return store, preview, _match_athlete(parts["athlete"]), discipline, False


@callback(
    Output("up-status", "children"),
    Output("up-meta-table", "data", allow_duplicate=True),
    Output("up-athlete-list", "children", allow_duplicate=True),
    Input("up-save", "n_clicks"),
    State("up-store", "data"),
    State("up-athlete", "value"),
    State("up-discipline", "value"),
    State("up-date", "date"),
    State("up-throw_label", "value"),
    State("up-distance", "value"),
    State("up-notes", "value"),
    State("up-video", "value"),
    prevent_initial_call=True,
)
def on_save(_, store, athlete, discipline, date, throw_label, distance, notes, video):
    if not store:
        return "Upload a file first.", dash.no_update, dash.no_update
    if not (athlete or "").strip():
        return "Athlete is required.", dash.no_update, dash.no_update
    if discipline not in DISCIPLINES:
        return "Select the event (Discus, Shot put or Hammer).", dash.no_update, dash.no_update
    video = (video or "").strip()
    if video:
        video = resolve_video_link(video)
        if not video:
            return INVALID_VIDEO, dash.no_update, dash.no_update
    meta = TrialMeta(athlete=" ".join(athlete.split()), discipline=discipline,
                     date=date or "", throw_label=throw_label or "",
                     distance=float(distance) if distance not in (None, "") else None, notes=notes or "",
                     video=video)
    key = repository.save_trial(base64.b64decode(store["content"]), meta)
    link = dcc.Link("open report", href=f"/?trial={key}")
    return (html.Span(["Saved ", html.Strong(trial_label(meta)), " — ", link], style={"color": "#16a34a"}),
            _meta_table_data(), _athlete_options())


@callback(
    Output("up-meta-status", "children"),
    Output("up-meta-table", "data"),
    Output("up-meta-table", "selected_rows"),
    Output("up-athlete-list", "children"),
    Input("up-meta-save", "n_clicks"),
    Input("up-meta-delete", "n_clicks"),
    State("up-meta-table", "data"),
    State("up-meta-table", "selected_rows"),
    prevent_initial_call=True,
)
def on_meta_action(_, __, rows, selected):
    if dash.ctx.triggered_id == "up-meta-delete":
        keys = [rows[i]["key"] for i in (selected or [])]
        if not keys:
            return "Select rows to delete.", dash.no_update, dash.no_update, dash.no_update
        for key in keys:
            repository.delete_trial(key)
        return f"Deleted {len(keys)} trial(s).", _meta_table_data(), [], _athlete_options()

    no_athlete = bad_video = 0
    for row in rows:
        meta = repository.get_meta(row["key"])
        for f in META_FIELDS:
            value = row.get(f)
            if f == "distance":
                value = float(value) if value not in (None, "") and not pd.isna(value) else None
            else:
                value = " ".join(str(value or "").split())
                if f == "date":
                    value = parse_date(value)
            setattr(meta, f, value)
        stored_video = repository.get_meta(row["key"]).video
        if meta.video and meta.video != stored_video:
            # Only new or changed links are resolved (short links need a network call)
            meta.video = resolve_video_link(meta.video) or ""
            if not meta.video:
                bad_video += 1
                continue
        if not meta.athlete:
            no_athlete += 1
        else:
            repository.update_meta(meta)
    skipped = [f"{n} row(s) {why}" for n, why in [(no_athlete, "without athlete"),
                                                  (bad_video, "with an invalid video link")] if n]
    status = f"Saved; skipped {', '.join(skipped)}." if skipped else "Metadata saved."
    return status, _meta_table_data(), dash.no_update, _athlete_options()
