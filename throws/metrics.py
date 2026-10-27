"""Release parameters, phase timing, and event snapshots.

Event order (Simi ``Event`` column, first six values):
    Start, Toe-off 1, Toe-off 2, Touchdown 1, Touchdown 2, Release
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .models import Trial

EVENT_NAMES = ["Start", "Toe-off 1", "Toe-off 2", "Touchdown 1", "Touchdown 2", "Release"]
EVENT_ABBR = ["Start", "TO1", "TO2", "TD1", "TD2", "REL"]

# Support phases reported in the table: (label, start event, end event)
PHASES = [
    ("Entry", 1, 2),
    ("Flight", 2, 3),
    ("Transition", 3, 4),
    ("Delivery", 4, 5),
]

# Trajectory segments used for colouring plots: (label, start event, end event).
# The four support phases plus the lead-in and a short post-release tail;
# ``None`` as end means "release + POST_RELEASE_FRAMES".
SEGMENTS = [
    ("Double Support", 0, 1),
    *PHASES,
    ("Post-release", 5, None),
]
POST_RELEASE_FRAMES = 5

# Release variables are sampled one frame before the release event
# (MATLAB: ``ef(6)-1``), i.e. the last frame of hand contact.
DEFAULT_RELEASE_OFFSET = -1


def segment_bounds(trial: Trial) -> list[tuple[str, int, int]]:
    """Frame index bounds (inclusive) of each plotting segment."""
    idx = trial.event_idx
    last = len(trial.data) - 1
    bounds = []
    for label, start, end in SEGMENTS:
        i0 = int(idx[start])
        i1 = int(idx[end]) if end is not None else min(i0 + POST_RELEASE_FRAMES, last)
        bounds.append((label, i0, i1))
    return bounds


def _release_angle(trial: Trial, r: int) -> float:
    """Path tangent angle at frame ``r`` (central difference of AP-VT position)."""
    ap, vt = trial.data["ap"].to_numpy(), trial.data["vt"].to_numpy()
    return float(np.degrees(np.arctan2(vt[r + 1] - vt[r - 1], ap[r + 1] - ap[r - 1])))


def release_params(trial: Trial, offset: int = DEFAULT_RELEASE_OFFSET) -> dict:
    """Release speed, angle, velocity components, and height."""
    r = trial.release_idx + offset
    d = trial.data
    return {
        "speed": float(d["speed"].iat[r]),
        "angle": _release_angle(trial, r),
        "v_vertical": float(d["v_vt"].iat[r]),
        "v_horizontal": float(d["v_ap"].iat[r]),
        "v_ml": float(d["v_ml"].iat[r]),
        "height": float(d["vt"].iat[r]),
        "time": float(d["time"].iat[r]),
        "frame": r,
    }


def phase_table(trial: Trial) -> pd.DataFrame:
    """Duration, speed change, and cumulative time for each support phase."""
    idx = trial.event_idx
    speed = trial.data["speed"].to_numpy()
    pos = trial.data[["ml_f", "ap_f", "vt_f"]].to_numpy()

    rows = []
    for label, s, e in PHASES:
        i0, i1 = int(idx[s]), int(idx[e])
        path = np.linalg.norm(np.diff(pos[i0:i1 + 1], axis=0), axis=1).sum()
        rows.append({
            "phase": label,
            "events": f"{EVENT_ABBR[s]} → {EVENT_ABBR[e]}",
            "duration": (i1 - i0) / trial.fs,
            "speed_start": speed[i0],
            "speed_end": speed[i1],
            "speed_change": speed[i1] - speed[i0],
            "path_length": path,
        })
    df = pd.DataFrame(rows)
    df["cumulative"] = df["duration"].cumsum()
    df["duration_pct"] = 100 * df["duration"] / df["duration"].sum()
    return df


def event_snapshot_table(trial: Trial) -> pd.DataFrame:
    """Implement position and velocity at each event (filtered positions)."""
    d = trial.data
    rows = []
    for name, i in zip(EVENT_NAMES, trial.event_idx):
        i = int(i)
        rows.append({
            "event": name,
            "time": d["time"].iat[i],
            "frame": i,
            "ml": d["ml_f"].iat[i],
            "ap": d["ap_f"].iat[i],
            "vt": d["vt_f"].iat[i],
            "speed": d["speed"].iat[i],
            "v_ml": d["v_ml"].iat[i],
            "v_ap": d["v_ap"].iat[i],
            "v_vt": d["v_vt"].iat[i],
        })
    return pd.DataFrame(rows)


def trial_summary(trial: Trial, phases: pd.DataFrame | None = None) -> dict:
    """Flat dict of key metrics for cross-trial comparison.

    ``phases`` may be passed when the caller already has the phase table.
    """
    rel = release_params(trial)
    if phases is None:
        phases = phase_table(trial)
    summary = {
        "key": trial.meta.key,
        "athlete": trial.meta.display_name,
        "date": trial.meta.date,
        "throw_label": trial.meta.throw_label,
        "distance": trial.meta.distance,
        "release_speed": rel["speed"],
        "release_angle": rel["angle"],
        "release_v_vertical": rel["v_vertical"],
        "release_v_horizontal": rel["v_horizontal"],
        "release_height": rel["height"],
        "peak_speed_before_release": float(trial.data["speed"].iloc[: trial.release_idx].max()),
        "total_time": float(phases["duration"].sum()),
    }
    for row in phases.itertuples():
        summary[f"dur::{row.phase}"] = row.duration
        summary[f"dv::{row.phase}"] = row.speed_change
    return summary
