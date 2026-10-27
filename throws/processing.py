"""Signal processing helpers: sampling rate, filtering, event indexing."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.signal import butter, filtfilt

FILTER_CUTOFF_HZ = 10.0
FILTER_ORDER = 2


def detect_fs(time: np.ndarray) -> float:
    """Sampling rate from the median time step (rounded to 0.01 Hz)."""
    dt = np.median(np.diff(np.asarray(time, dtype=float)))
    return round(1.0 / dt, 2)


def lowpass(signal: np.ndarray, fs: float, cutoff: float = FILTER_CUTOFF_HZ,
            order: int = FILTER_ORDER) -> np.ndarray:
    """Zero-lag Butterworth low-pass (MATLAB ``butter`` + ``filtfilt``)."""
    b, a = butter(order, cutoff / (fs / 2))
    return filtfilt(b, a, signal)


def event_frames(event_times: np.ndarray, fs: float) -> np.ndarray:
    """0-based frame indices of events (MATLAB ``round(t*fs)+1`` minus one)."""
    return np.round(np.asarray(event_times) * fs).astype(int)


def to_lab_frame(raw: pd.DataFrame, fs: float) -> pd.DataFrame:
    """Map Simi axes to ML / AP / VT and add filtered positions.

    Axis convention follows the MATLAB script: X is sign-flipped to ML,
    Y is antero-posterior (throw direction), Z is vertical.
    """
    df = pd.DataFrame({
        "time": raw["time"].to_numpy(),
        "ml": -raw["x"].to_numpy(),
        "ap": raw["y"].to_numpy(),
        "vt": raw["z"].to_numpy(),
        "v_ml": -raw["vx"].to_numpy(),
        "v_ap": raw["vy"].to_numpy(),
        "v_vt": raw["vz"].to_numpy(),
        "speed": raw["vabs"].to_numpy(),
    })
    for axis in ("ml", "ap", "vt"):
        df[f"{axis}_f"] = lowpass(df[axis].to_numpy(), fs)
    return df
