"""Trial data model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
import pandas as pd

from .io import load_simi_txt, parse_filename
from .processing import detect_fs, event_frames, to_lab_frame


DISPLAY_DATE_FORMAT = "%d/%m/%Y"
# Accepted typed forms, day-first before year-first
_DATE_INPUT_FORMATS = ("%d/%m/%Y", "%d.%m.%Y", "%d-%m-%Y", "%Y-%m-%d", "%Y/%m/%d", "%Y%m%d")


def parse_date(text) -> str:
    """Normalise a typed date to stored ISO ``YYYY-MM-DD``; unparseable text is kept."""
    text = str(text or "").strip()
    for fmt in _DATE_INPUT_FORMATS:
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return text


def format_date(value) -> str:
    """Stored date shown as ``DD/MM/YYYY``."""
    iso = parse_date(value)
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime(DISPLAY_DATE_FORMAT)
    except ValueError:
        return iso


DISCIPLINES = ("Discus", "Shot put", "Hammer")


def match_discipline(name: str) -> str:
    """Map a Simi object name (e.g. "Discus", "Shot") onto DISCIPLINES; "" if none."""
    first = (name or "").strip().lower().split(" ")[0]
    return next((d for d in DISCIPLINES if d.lower().split(" ")[0] == first), "") if first else ""


@dataclass
class TrialMeta:
    athlete: str = ""          # athlete name, e.g. "Ibrahim Hamdan"; groups trials
    discipline: str = ""       # one of DISCIPLINES; overrides the Simi object name
    date: str = ""             # ISO date, e.g. "2025-05-14"
    throw_label: str = ""      # e.g. clock time of the throw "16:17"
    distance: float | None = None  # official mark (m), optional
    notes: str = ""
    video: str = ""            # optional Dartfish link or video id
    key: str = ""              # storage id, assigned automatically on upload

    @property
    def display_name(self) -> str:
        return self.athlete

    @property
    def short_label(self) -> str:
        """Compact label to tell trials apart in charts: throw # or date."""
        return f"#{self.throw_label}" if self.throw_label else (format_date(self.date) or "Trial")


@dataclass
class Trial:
    meta: TrialMeta
    data: pd.DataFrame                 # lab-frame kinematics (see processing.to_lab_frame)
    event_times: np.ndarray            # seconds, length 6
    fs: float
    implement: str = "Discus"
    event_idx: np.ndarray = field(init=False)

    def __post_init__(self):
        self.event_idx = event_frames(self.event_times, self.fs)
        last = len(self.data) - 1
        if self.event_idx.max() > last - 1:
            raise ValueError("Release event is too close to the end of the recording")

    @classmethod
    def from_source(cls, source, meta: TrialMeta | None = None, filename: str | None = None):
        raw, event_times, implement = load_simi_txt(source)
        if meta is None:
            meta = TrialMeta()
        name = filename or (source if isinstance(source, str) else None)
        if name and not meta.athlete:
            meta.athlete = parse_filename(name)["athlete"]
        fs = detect_fs(raw["time"].to_numpy())
        return cls(meta=meta, data=to_lab_frame(raw, fs), event_times=event_times,
                   fs=fs, implement=meta.discipline or match_discipline(implement) or implement)

    @property
    def release_idx(self) -> int:
        return int(self.event_idx[-1])
