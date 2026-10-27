"""Readers for Simi Motion trajectory text exports."""

from __future__ import annotations

import io
import os
import re

import numpy as np
import pandas as pd

# Simi export column order: Time, <Obj> X/Y/Z, <Obj> v(X)/v(Y)/v(Z)/v(abs), Event
RAW_COLUMNS = ["time", "x", "y", "z", "vx", "vy", "vz", "vabs", "event"]

N_EVENTS = 6


def _read_source(source) -> tuple[str, str | None]:
    """Return (text, filename) for a path, bytes, or file-like object."""
    if isinstance(source, (str, os.PathLike)) and os.path.exists(source):
        with open(source, "r", encoding="utf-8-sig") as f:
            return f.read(), os.path.basename(source)
    if isinstance(source, bytes):
        return source.decode("utf-8-sig"), None
    if hasattr(source, "read"):
        data = source.read()
        text = data.decode("utf-8-sig") if isinstance(data, bytes) else data
        return text, getattr(source, "name", None)
    if isinstance(source, str):
        return source, None
    raise TypeError(f"Unsupported source type: {type(source)!r}")


def load_simi_txt(source) -> tuple[pd.DataFrame, np.ndarray, str]:
    """Load a Simi trajectory export.

    Parameters
    ----------
    source : path, bytes, str content, or file-like

    Returns
    -------
    raw : DataFrame with columns ``RAW_COLUMNS[:-1]`` (rows with missing
        coordinates at the end of the file are dropped, like the MATLAB
        ``tdata(1:end-2,:)`` trim).
    event_times : array of the first six event times (s).
    implement : object name taken from the header, e.g. ``"Discus"``.
    """
    text, _ = _read_source(source)
    df = pd.read_csv(io.StringIO(text))
    if df.shape[1] < len(RAW_COLUMNS):
        raise ValueError(
            f"Expected {len(RAW_COLUMNS)} columns, found {df.shape[1]}: {list(df.columns)}"
        )

    # Implement name from header like "Discus X" / "Hammer X"
    match = re.match(r"\s*(.+?)\s+X\s*$", str(df.columns[1]))
    implement = match.group(1) if match else "Implement"

    df = df.iloc[:, : len(RAW_COLUMNS)]
    df.columns = RAW_COLUMNS

    event_times = df["event"].dropna().to_numpy(dtype=float)[:N_EVENTS]
    if len(event_times) < N_EVENTS:
        raise ValueError(f"Expected {N_EVENTS} event times, found {len(event_times)}")

    raw = df.drop(columns="event").dropna(subset=["x", "y", "z"]).reset_index(drop=True)
    return raw, event_times, implement


def slugify(text: str) -> str:
    """Lower-case, punctuation-free form of a name ("Ibrahim Hamdan" -> "ibrahim-hamdan")."""
    return re.sub(r"[\W_]+", "-", (text or "").strip().lower()).strip("-")


def parse_filename(filename: str) -> dict:
    """Guess the athlete from ``<Athlete>_<anything>.txt`` (whole stem if no ``_``)."""
    stem = os.path.splitext(os.path.basename(filename))[0]
    athlete = stem.rpartition("_")[0] or stem
    return {"athlete": athlete, "stem": stem}
