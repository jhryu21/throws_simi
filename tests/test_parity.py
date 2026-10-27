"""Parity tests: Python port vs. values written by thorwtraj_v1.m into the Excel report."""

import os

import numpy as np
import openpyxl
import pytest

from throws import Trial, phase_table, release_params

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT = os.path.join(ROOT, "Ibrahim_20250514.xlsx")
TXT_DIRS = [ROOT, os.path.join(ROOT, "data", "raw")]


def _find_txt(sheet_name):
    for d in TXT_DIRS:
        path = os.path.join(d, f"{sheet_name}.txt")
        if os.path.exists(path):
            return path
    return None


def _sheets():
    if not os.path.exists(REPORT):
        return []
    return openpyxl.load_workbook(REPORT, read_only=True).sheetnames


@pytest.mark.parametrize("sheet_name", _sheets())
def test_matches_excel_report(sheet_name):
    txt = _find_txt(sheet_name)
    if txt is None:
        pytest.skip(f"No raw txt for {sheet_name}")

    ws = openpyxl.load_workbook(REPORT, data_only=True)[sheet_name]
    # Release angle (column B) is excluded: the report used the old mixed-frame formula
    expected_release = [ws.cell(7, c).value for c in (1, 3, 4, 5)]
    expected_phases = np.array([[ws.cell(r, c).value for c in (3, 4, 5)] for r in range(53, 57)])

    trial = Trial.from_source(txt)
    rel = release_params(trial)
    got_release = [rel["speed"], rel["v_vertical"], rel["v_horizontal"], rel["height"]]
    np.testing.assert_allclose(got_release, expected_release, rtol=1e-9)

    ph = phase_table(trial)
    got_phases = ph[["duration", "speed_change", "cumulative"]].to_numpy()
    np.testing.assert_allclose(got_phases, expected_phases, rtol=1e-9, atol=1e-12)


def test_release_angle_is_position_tangent_at_release_minus_one():
    trial = Trial.from_source(os.path.join(ROOT, "Ibrahim_517.txt"))
    d, r = trial.data, trial.release_idx - 1
    expected = np.degrees(np.arctan2(d["vt"].iat[r + 1] - d["vt"].iat[r - 1],
                                     d["ap"].iat[r + 1] - d["ap"].iat[r - 1]))
    assert release_params(trial)["angle"] == pytest.approx(expected)
    assert release_params(trial)["angle"] == pytest.approx(41.0277, abs=1e-3)


def test_sampling_rate_and_events():
    trial = Trial.from_source(os.path.join(ROOT, "Ibrahim_517.txt"))
    assert trial.fs == 160
    assert trial.implement == "Discus"
    assert list(trial.event_idx) == [0, 75, 146, 156, 210, 241]
