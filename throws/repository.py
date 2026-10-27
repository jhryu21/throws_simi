"""File-based trial storage: ``data/raw/*.txt`` + ``data/meta.json``."""

from __future__ import annotations

import json
import os
import re
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


# Keys come back from the browser (table rows, dropdown values), so they are
# checked before being turned into file paths: no separators, no "..".
_KEY_PATTERN = re.compile(r"^[\w-]+$")


def _read_meta() -> dict:
    if not os.path.exists(META_PATH):
        return {}
    with open(META_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_meta(meta: dict) -> None:
    """Write via a temp file and rename, so a crash never leaves a half-written meta.json."""
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = f"{META_PATH}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    os.replace(tmp, META_PATH)


def list_trial_keys() -> list[str]:
    if not os.path.isdir(RAW_DIR):
        return []
    return sorted(os.path.splitext(f)[0] for f in os.listdir(RAW_DIR) if f.lower().endswith(".txt"))


def _meta_from(key: str, stored: dict) -> TrialMeta:
    meta = TrialMeta(athlete=parse_filename(key)["athlete"], key=key)
    for name, value in stored.items():
        if name in TrialMeta.__dataclass_fields__ and name != "key":
            setattr(meta, name, value)
    meta.date = parse_date(meta.date)  # older entries may hold e.g. "20250514"
    return meta


def get_meta(key: str) -> TrialMeta:
    return _meta_from(key, _read_meta().get(key, {}))


def list_metas() -> list[TrialMeta]:
    all_meta = _read_meta()  # read once, not once per trial
    return [_meta_from(k, all_meta.get(k, {})) for k in list_trial_keys()]


def list_athletes() -> list[str]:
    """Distinct stored athlete names, one spelling per name key."""
    names = {}
    for m in list_metas():
        names.setdefault(slugify(m.athlete), m.athlete)
    return sorted(names.values(), key=str.lower)


def _raw_path(key: str) -> str:
    if not _KEY_PATTERN.match(key or ""):
        raise ValueError(f"Invalid trial key: {key!r}")
    return os.path.join(RAW_DIR, f"{key}.txt")


@lru_cache(maxsize=128)
def _load_cached(key: str, _raw_mtime: float, stored_json: str) -> Trial:
    return Trial.from_source(_raw_path(key), meta=_meta_from(key, json.loads(stored_json)))


def load_trial(key: str) -> Trial:
    # Cached per raw file and per this trial's own metadata, so editing one
    # trial's metadata does not force every other trial to be re-parsed
    stored = _read_meta().get(key, {})
    return _load_cached(key, os.path.getmtime(_raw_path(key)), json.dumps(stored, sort_keys=True))


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
    update_metas([meta])


def update_metas(metas: list[TrialMeta]) -> None:
    """Store several trials' metadata with a single read and write of meta.json."""
    if not metas:
        return
    all_meta = _read_meta()
    for meta in metas:
        _raw_path(meta.key)  # validates the key
        all_meta[meta.key] = {k: v for k, v in asdict(meta).items() if k != "key"}
    _write_meta(all_meta)


def delete_trials(keys: list[str]) -> None:
    paths = [_raw_path(k) for k in keys]  # validate every key before deleting anything
    for path in paths:
        if os.path.exists(path):
            os.remove(path)
    all_meta = _read_meta()
    # List (not generator) so every key is popped, not just up to the first hit
    if any([all_meta.pop(k, None) is not None for k in keys]):
        _write_meta(all_meta)


def delete_trial(key: str) -> None:
    delete_trials([key])
