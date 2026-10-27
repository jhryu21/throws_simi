"""Plotly figures for throw trajectory analysis (Aspire template)."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from aspire_dash import charts  # noqa: F401  (registers the "aspire" template)
from aspire_dash.theme import SLATE
from throws import EVENT_NAMES, PHASES, Trial
from throws.metrics import SEGMENTS, segment_bounds

# Fixed phase colours (validated for CVD + normal vision, light and dark).
SEGMENT_COLORS = {
    "Double Support 1": "#1876ab",
    "Left Support": "#16a34a",
    "Flight": "#7c3aed",
    "Right Support": "#d97706",
    "Delivery": "#db2777",
    "Post-release": SLATE["400"],
}
# Support phases in the table map onto the plotting segments
PHASE_COLORS = {
    PHASES[0][0]: SEGMENT_COLORS["Left Support"],
    PHASES[1][0]: SEGMENT_COLORS["Flight"],
    PHASES[2][0]: SEGMENT_COLORS["Right Support"],
    PHASES[3][0]: SEGMENT_COLORS["Delivery"],
}
EVENT_ABBR = ["Start", "TO1", "TO2", "TD1", "TD2", "REL"]
# Label placement for TO1..REL; TO2 and TD1 are only a few frames apart
EVENT_TEXT_POS = ["top center", "top left", "top right", "top center", "top center"]
EVENT_XANCHOR = ["center", "right", "left", "center", "center"]

# Categorical order for comparing trials (same validated hues, fixed order)
TRIAL_COLORS = ["#1876ab", "#16a34a", "#7c3aed", "#d97706", "#db2777"]

AXIS_LABELS = {
    "ml": "ML (m)",
    "ap": "AP (m)",
    "vt": "VT (m)",
}

LINE_WIDTH = 2.5
SQUARE_PADDING = 0.05  # fraction of the data span added on each side
MARKER_SIZE = 9


def _base_layout(fig: go.Figure, height: int = 360, **kwargs) -> go.Figure:
    layout = dict(
        height=height,
        margin=dict(l=52, r=16, t=24, b=44),
        showlegend=False,
        hoverlabel=dict(namelength=-1),
    )
    layout.update(kwargs)
    fig.update_layout(**layout)
    return fig


def _event_markers(fig, x, y, trial: Trial, hover_extra=None, **trace_kwargs):
    """Event dots with a surface ring and short direct labels."""
    idx = trial.event_idx[1:]  # skip "Start"
    t = trial.data["time"].to_numpy()
    speed = trial.data["speed"].to_numpy()
    fig.add_trace(go.Scatter(
        x=x[idx], y=y[idx],
        mode="markers+text",
        text=EVENT_ABBR[1:],
        textposition=EVENT_TEXT_POS,
        textfont=dict(size=11, color=SLATE["600"]),
        marker=dict(size=MARKER_SIZE, color=SLATE["800"], line=dict(width=2, color="white")),
        customdata=np.column_stack([EVENT_NAMES[1:], t[idx], speed[idx]]),
        hovertemplate="<b>%{customdata[0]}</b><br>t = %{customdata[1]:.3f} s"
                      "<br>speed = %{customdata[2]:.2f} m/s<extra></extra>",
        showlegend=False,
        **trace_kwargs,
    ))


def trajectory_view(trial: Trial, x_axis: str, y_axis: str, height: int = 460) -> go.Figure:
    """2D projection of the filtered implement path, coloured by phase."""
    d = trial.data
    x, y = d[f"{x_axis}_f"].to_numpy(), d[f"{y_axis}_f"].to_numpy()
    t, speed = d["time"].to_numpy(), d["speed"].to_numpy()

    fig = go.Figure()
    for label, i0, i1 in segment_bounds(trial):
        sl = slice(i0, i1 + 1)
        fig.add_trace(go.Scatter(
            x=x[sl], y=y[sl], mode="lines", name=label,
            line=dict(color=SEGMENT_COLORS[label], width=LINE_WIDTH,
                      dash="dot" if label == "Post-release" else "solid"),
            customdata=np.column_stack([t[sl], speed[sl]]),
            hovertemplate=f"<b>{label}</b><br>t = %{{customdata[0]:.3f}} s"
                          "<br>speed = %{customdata[1]:.2f} m/s<extra></extra>",
        ))
    _event_markers(fig, x, y, trial)

    # Square plot area with equal metric scale: both axes share one span
    # centred on the path up to release (the dotted post-release tail may be
    # clipped); domains shrink to keep the 1:1 ratio.
    rel = trial.event_idx[-1]
    xs, ys = x[: rel + 1], y[: rel + 1]
    span = max(np.ptp(xs), np.ptp(ys)) * (1 + 2 * SQUARE_PADDING)
    xc, yc = (xs.max() + xs.min()) / 2, (ys.max() + ys.min()) / 2

    _base_layout(fig, height)
    fig.update_xaxes(title=AXIS_LABELS[x_axis], range=[xc - span / 2, xc + span / 2],
                     constrain="domain", dtick=0.5)
    fig.update_yaxes(title=AXIS_LABELS[y_axis], range=[yc - span / 2, yc + span / 2],
                     scaleanchor="x", scaleratio=1, constrain="domain", dtick=0.5)
    return fig


def speed_time(trial: Trial, height: int = 460) -> go.Figure:
    """Resultant implement speed over time up to release."""
    d = trial.data
    t, speed = d["time"].to_numpy(), d["speed"].to_numpy()

    fig = go.Figure()
    for label, i0, i1 in segment_bounds(trial):
        if label == "Post-release":
            continue
        sl = slice(i0, i1 + 1)
        fig.add_trace(go.Scatter(
            x=t[sl], y=speed[sl], mode="lines", name=label,
            line=dict(color=SEGMENT_COLORS[label], width=LINE_WIDTH),
            hovertemplate=f"<b>{label}</b><br>t = %{{x:.3f}} s<br>speed = %{{y:.2f}} m/s<extra></extra>",
        ))
    _event_markers(fig, t, speed, trial)

    _base_layout(fig, height, hovermode="closest")
    fig.update_xaxes(title="Time (s)", showspikes=True, spikemode="across",
                     spikethickness=1, spikecolor=SLATE["300"], spikedash="solid")
    # Headroom so the release label is not clipped
    fig.update_yaxes(title="Speed (m/s)", range=[0, speed[: trial.release_idx + 1].max() * 1.12])
    return fig


def velocity_components(trial: Trial, height: int = 440) -> go.Figure:
    """AP / VT / ML velocity components with a release marker."""
    d = trial.data
    r = trial.release_idx
    sl = slice(0, r + 1)
    t = d["time"].to_numpy()[sl]
    series = [("v AP", "v_ap", TRIAL_COLORS[0]), ("v VT", "v_vt", TRIAL_COLORS[3]),
              ("v ML", "v_ml", TRIAL_COLORS[2])]

    fig = go.Figure()
    for name, col, color in series:
        y = d[col].to_numpy()[sl]
        fig.add_trace(go.Scatter(
            x=t, y=y, mode="lines", name=name, line=dict(color=color, width=2),
            hovertemplate=f"{name}: %{{y:.2f}} m/s<extra></extra>",
        ))
        # Direct label at the line end
        fig.add_annotation(x=t[-1], y=y[-1], text=name, showarrow=False, xanchor="left",
                           xshift=6, font=dict(size=11, color=SLATE["600"]))
    for name, i, anchor in zip(EVENT_ABBR[1:], trial.event_idx[1:], EVENT_XANCHOR):
        fig.add_vline(x=d["time"].iat[int(i)], line=dict(color=SLATE["200"], width=1))
        fig.add_annotation(x=d["time"].iat[int(i)], y=1, yref="paper", text=name, showarrow=False,
                           yanchor="bottom", xanchor=anchor, font=dict(size=10, color=SLATE["500"]))

    _base_layout(fig, height, hovermode="x unified", showlegend=True,
                 legend=dict(orientation="h", y=-0.22, x=0))
    fig.update_layout(margin=dict(l=52, r=48, t=24, b=60))
    fig.update_xaxes(title="Time (s)")
    fig.update_yaxes(title="Velocity (m/s)", zeroline=True, zerolinecolor=SLATE["300"])
    return fig


def trajectory_3d(trial: Trial, height: int = 440) -> go.Figure:
    d = trial.data
    t, speed = d["time"].to_numpy(), d["speed"].to_numpy()
    fig = go.Figure()
    for label, i0, i1 in segment_bounds(trial):
        sl = slice(i0, i1 + 1)
        fig.add_trace(go.Scatter3d(
            x=d["ap_f"].to_numpy()[sl], y=d["ml_f"].to_numpy()[sl], z=d["vt_f"].to_numpy()[sl],
            mode="lines", name=label,
            line=dict(color=SEGMENT_COLORS[label], width=6),
            customdata=np.column_stack([t[sl], speed[sl]]),
            hovertemplate=f"<b>{label}</b><br>t = %{{customdata[0]:.3f}} s"
                          "<br>speed = %{customdata[1]:.2f} m/s<extra></extra>",
        ))
    idx = trial.event_idx[1:]
    fig.add_trace(go.Scatter3d(
        x=d["ap_f"].to_numpy()[idx], y=d["ml_f"].to_numpy()[idx], z=d["vt_f"].to_numpy()[idx],
        mode="markers+text", text=EVENT_ABBR[1:], textposition="top center",
        marker=dict(size=4, color=SLATE["800"]), hoverinfo="skip", showlegend=False,
    ))
    # VT starts at the ground; explicit ranges with a manual aspect ratio keep
    # the box in real-life proportion (1 m equal on all three axes).
    ranges = {a: [d[f"{a}_f"].min(), d[f"{a}_f"].max()] for a in ("ap", "ml")}
    ranges["vt"] = [0.0, d["vt_f"].max()]
    spans = {a: hi - lo for a, (lo, hi) in ranges.items()}
    longest = max(spans.values())
    fig.update_layout(
        height=height, margin=dict(l=0, r=0, t=0, b=0), showlegend=False,
        scene=dict(
            xaxis=dict(title="AP (m)", range=ranges["ap"]),
            yaxis=dict(title="ML (m)", range=ranges["ml"]),
            zaxis=dict(title="VT (m)", range=ranges["vt"]),
            aspectmode="manual",
            aspectratio=dict(x=spans["ap"] / longest, y=spans["ml"] / longest,
                             z=spans["vt"] / longest),
            # Closer than Plotly's default distance so the path fills the card
            camera=dict(eye=dict(x=-0.85, y=-0.85, z=0.55)),
        ),
    )
    return fig


def phase_timeline(phases_by_trial: list[tuple[str, "object"]], height: int | None = None) -> go.Figure:
    """Horizontal stacked bars of support-phase durations, one bar per trial.

    ``phases_by_trial`` is a list of (label, phase_table DataFrame).
    """
    labels = [label for label, _ in phases_by_trial]
    fig = go.Figure()
    for phase, _, _ in PHASES:
        durations = [float(df.loc[df["phase"] == phase, "duration"].iat[0]) for _, df in phases_by_trial]
        fig.add_trace(go.Bar(
            y=labels, x=durations, orientation="h", name=phase,
            marker=dict(color=PHASE_COLORS[phase], line=dict(color="white", width=2)),
            texttemplate="%{x:.3f}s", textposition="inside",
            insidetextanchor="middle", textfont=dict(color="white", size=11),
            hovertemplate=f"<b>{phase}</b><br>%{{y}}: %{{x:.3f}} s<extra></extra>",
        ))
    height = height or 48 * len(labels) + 150
    _base_layout(fig, height, barmode="stack", showlegend=True,
                 legend=dict(orientation="h", traceorder="normal", x=0, y=1, yanchor="bottom"))
    fig.update_layout(margin=dict(l=72, r=16, t=40, b=48), bargap=0.35)
    fig.update_xaxes(title="Time from Toe-off 1 (s)")
    fig.update_yaxes(autorange="reversed")
    return fig


def compare_speed(trials: list[Trial], labels: list[str] | None = None, height: int = 380) -> go.Figure:
    """Speed curves aligned at release (t = 0)."""
    labels = labels or [trial.meta.short_label for trial in trials]
    fig = go.Figure()
    for i, (trial, label) in enumerate(zip(trials, labels)):
        color = TRIAL_COLORS[i % len(TRIAL_COLORS)]
        d = trial.data
        r = trial.release_idx
        t = d["time"].to_numpy()[: r + 1] - d["time"].iat[r]
        speed = d["speed"].to_numpy()[: r + 1]
        fig.add_trace(go.Scatter(
            x=t, y=speed, mode="lines", name=label, line=dict(color=color, width=2),
            hovertemplate=f"<b>{label}</b> %{{y:.2f}} m/s<extra></extra>",
        ))
        ev = trial.event_idx[1:]
        fig.add_trace(go.Scatter(
            x=t[ev], y=speed[ev], mode="markers", showlegend=False, hoverinfo="skip",
            marker=dict(size=8, color=color, line=dict(width=2, color="white")),
        ))
    _base_layout(fig, height, hovermode="x unified", showlegend=True,
                 legend=dict(orientation="h", y=-0.2, x=0))
    fig.update_xaxes(title="Time relative to release (s)")
    fig.update_yaxes(title="Speed (m/s)", rangemode="tozero")
    return fig


def trend_chart(df, metric: str, metric_label: str, height: int = 360) -> go.Figure:
    """Metric per trial over sessions (single series, dots + session mean line)."""
    fig = go.Figure()
    # Keep the caller's chronological order (display dates do not sort as text)
    sess = df.groupby("date", as_index=False, sort=False)[metric].mean()
    fig.add_trace(go.Scatter(
        x=sess["date"], y=sess[metric], mode="lines", name="Session mean",
        line=dict(color=SLATE["300"], width=2), hovertemplate="Session mean %{y:.2f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=df["date"], y=df[metric], mode="markers", name="Trial",
        marker=dict(size=10, color=TRIAL_COLORS[0], line=dict(width=2, color="white")),
        customdata=df[["throw_label"]].to_numpy(),
        hovertemplate="Throw #%{customdata[0]}<br>%{y:.2f}<extra></extra>",
    ))
    _base_layout(fig, height, showlegend=True, legend=dict(orientation="h", y=-0.2, x=0))
    fig.update_xaxes(title="Session date", type="category")
    fig.update_yaxes(title=metric_label)
    return fig
