"""File-based trial storage: ``data/raw/*.txt`` + ``data/meta.json``."""

from __future__ import annotations

import json
import os
import secrets
from dataclasses import asdict
from datetime import datetime
from functools import lru_cache

from .io import parse_filename, slugify
from .models import Trial, TrialMeta, parse_date

DATA_DIR = os.environ.get(
    "THROWS_DATA_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"),
)
RAW_DIR = os.path.join(DATA_DIR, "raw")
META_PATH = os.path.join(DATA_DIR, "meta.json")


def _read_meta() -> dict:
    if not os.path.exists(META_PATH):
        return {}
    with open(META_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_meta(meta: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)


def list_trial_keys() -> list[str]:
    if not os.path.isdir(RAW_DIR):
        return []
    return sorted(os.path.splitext(f)[0] for f in os.listdir(RAW_DIR) if f.lower().endswith(".txt"))


def get_meta(key: str) -> TrialMeta:
    stored = _read_meta().get(key, {})
    meta = TrialMeta(athlete=parse_filename(key)["athlete"], key=key)
    for name, value in stored.items():
        if name in TrialMeta.__dataclass_fields__ and name != "key":
            setattr(meta, name, value)
    meta.date = parse_date(meta.date)  # older entries may hold e.g. "20250514"
    return meta


def list_metas() -> list[TrialMeta]:
    return [get_meta(k) for k in list_trial_keys()]


def list_athletes() -> list[str]:
    """Distinct stored athlete names, one spelling per name key."""
    names = {}
    for m in list_metas():
        names.setdefault(slugify(m.athlete), m.athlete)
    return sorted(names.values(), key=str.lower)


def _raw_path(key: str) -> str:
    return os.path.join(RAW_DIR, f"{key}.txt")


def _mtime(key: str) -> float:
    return max(os.path.getmtime(_raw_path(key)),
               os.path.getmtime(META_PATH) if os.path.exists(META_PATH) else 0)


@lru_cache(maxsize=128)
def _load_cached(key: str, _stamp: float) -> Trial:
    return Trial.from_source(_raw_path(key), meta=get_meta(key))


def load_trial(key: str) -> Trial:
    return _load_cached(key, _mtime(key))


def _new_key() -> str:
    """Unique, time-sortable storage id, e.g. ``20251027-143205-a1b2``."""
    while True:
        key = f"{datetime.now():%Y%m%d-%H%M%S}-{secrets.token_hex(2)}"
        if not os.path.exists(_raw_path(key)):
            return key


def save_trial(content: bytes, meta: TrialMeta) -> str:
    """Validate and store a new trial under an auto-generated key. Returns the key."""
    Trial.from_source(content, meta=meta)  # raises on malformed input
    os.makedirs(RAW_DIR, exist_ok=True)
    meta.key = _new_key()
    with open(_raw_path(meta.key), "wb") as f:
        f.write(content)
    update_meta(meta)
    return meta.key


def update_meta(meta: TrialMeta) -> None:
    all_meta = _read_meta()
    all_meta[meta.key] = {k: v for k, v in asdict(meta).items() if k != "key"}
    _write_meta(all_meta)


def delete_trial(key: str) -> None:
    path = _raw_path(key)
    if os.path.exists(path):
        os.remove(path)
    all_meta = _read_meta()
    if all_meta.pop(key, None) is not None:
        _write_meta(all_meta)
