"""Throws biomechanics calculation package (Simi trajectory export → metrics).

Pure Python, no Dash dependency, so it can be reused in scripts and tests.
"""

from .io import load_simi_txt, parse_filename, slugify
from .models import DISCIPLINES, Trial, TrialMeta, format_date, match_discipline, parse_date
from .metrics import (
    EVENT_NAMES,
    PHASES,
    SEGMENTS,
    event_snapshot_table,
    phase_table,
    release_params,
)

__all__ = [
    "DISCIPLINES",
    "EVENT_NAMES",
    "PHASES",
    "SEGMENTS",
    "Trial",
    "TrialMeta",
    "event_snapshot_table",
    "format_date",
    "load_simi_txt",
    "match_discipline",
    "parse_date",
    "parse_filename",
    "phase_table",
    "release_params",
    "slugify",
]
