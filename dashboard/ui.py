"""Shared UI pieces for the throws dashboard pages."""

from __future__ import annotations

from dash import dash_table, html

from aspire_dash.theme import FONT_FAMILY, SLATE
from throws import format_date, repository
from throws.metrics import SEGMENTS

from .figures import SEGMENT_COLORS

GRID_2 = {
    "display": "grid",
    "gridTemplateColumns": "repeat(auto-fit, minmax(max(380px, 45%), 1fr))",
    "gap": "16px",
}
KPI_GRID = {
    "display": "grid",
    # auto-fit stretches the cards to the full row so its edge lines up with the grids below
    "gridTemplateColumns": "repeat(auto-fit, minmax(170px, 1fr))",
    "gap": "12px",
    "marginBottom": "20px",
}


def segment_legend():
    """Shared phase legend shown once above the trajectory grid."""
    items = []
    for label, _, _ in SEGMENTS:
        dashed = label == "Post-release"
        items.append(html.Div([
            html.Span(style={
                "display": "inline-block", "width": "18px", "height": "0",
                "borderTop": f"3px {'dotted' if dashed else 'solid'} {SEGMENT_COLORS[label]}",
                "marginRight": "6px", "verticalAlign": "middle",
            }),
            html.Span(label, style={"fontSize": "12px", "color": SLATE["600"]}),
        ], style={"display": "inline-flex", "alignItems": "center"}))
    items.append(html.Span("TO = toe-off · TD = touchdown · REL = release",
                           style={"fontSize": "12px", "color": SLATE["400"], "marginLeft": "auto"}))
    return html.Div(items, style={
        "display": "flex", "flexWrap": "wrap", "gap": "16px", "alignItems": "center",
        "marginBottom": "12px",
    })


def section_title(text, icon=None):
    children = [html.I(className=icon, style={"marginRight": "8px", "color": SLATE["400"]})] if icon else []
    return html.H3(children + [text], className="section-title", style={"marginTop": "8px"})


def data_table(df, columns, table_id=None, highlight_row=None, **kwargs):
    """Aspire-styled DataTable.

    ``columns`` is a list of (field, header, format) where format is a
    d3-format string such as ``".2f"`` or ``None`` for text.
    """
    cols = []
    for field, header, fmt in columns:
        col = {"id": field, "name": header}
        if fmt:
            col.update(type="numeric", format={"specifier": fmt})
        cols.append(col)

    cond = [{"if": {"row_index": "odd"}, "backgroundColor": SLATE["50"]}]
    if highlight_row is not None:
        cond.append({"if": {"row_index": highlight_row}, "fontWeight": "600",
                     "backgroundColor": "#eff6ff"})
    extra = {"id": table_id} if table_id else {}
    return dash_table.DataTable(
        data=df.to_dict("records"),
        columns=cols,
        style_as_list_view=True,
        style_table={"overflowX": "auto"},
        style_header={
            "fontWeight": "600", "fontSize": "12px", "color": SLATE["500"],
            "backgroundColor": "white", "borderBottom": f"2px solid {SLATE['200']}",
            "textTransform": "uppercase", "letterSpacing": "0.3px",
        },
        style_cell={
            "fontFamily": FONT_FAMILY, "fontSize": "13px", "color": SLATE["700"],
            "padding": "8px 12px", "border": "none", "textAlign": "right",
            "fontVariantNumeric": "tabular-nums",
        },
        style_cell_conditional=[{"if": {"column_id": columns[0][0]}, "textAlign": "left"}],
        style_data_conditional=cond,
        **extra,
        **kwargs,
    )


def trial_label(meta) -> str:
    parts = [meta.display_name, format_date(meta.date) or None,
             f"#{meta.throw_label}" if meta.throw_label else None]
    return " · ".join(p for p in parts if p)


def compare_labels(metas) -> list[str]:
    """Short, unique labels for trials shown side by side.

    Uses the throw # (or date), prefixed with the athlete when several athletes
    are compared; repeated labels get a running suffix.
    """
    multi = len({m.athlete for m in metas}) > 1
    labels, seen = [], {}
    for m in metas:
        label = f"{m.athlete} {m.short_label}" if multi else m.short_label
        seen[label] = seen.get(label, 0) + 1
        labels.append(label if seen[label] == 1 else f"{label} ({seen[label]})")
    return labels


def trial_options() -> list[dict]:
    """Dropdown options for stored trials, newest session first."""
    metas = sorted(repository.list_metas(), key=lambda m: (m.date, m.throw_label, m.key),
                   reverse=True)
    return [{"label": trial_label(m), "value": m.key} for m in metas]


def fmt(value, digits=2, unit=""):
    if value is None:
        return "–"
    return f"{value:.{digits}f}{unit}"
