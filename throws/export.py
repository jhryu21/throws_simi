"""Excel export in the layout of the original MATLAB report sheet."""

from __future__ import annotations

import io

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .metrics import event_snapshot_table, phase_table, release_params
from .models import Trial, format_date

_BOLD = Font(bold=True)
_HEAD = Font(bold=True, color="FFFFFF")
_HEAD_FILL = PatternFill("solid", fgColor="004185")
_TITLE = Font(bold=True, size=13, color="004185")


def _header_row(ws, row, labels):
    for c, label in enumerate(labels, start=1):
        cell = ws.cell(row, c, label)
        cell.font, cell.fill = _HEAD, _HEAD_FILL
        cell.alignment = Alignment(wrap_text=True, vertical="center")


def _write_sheet(ws, trial: Trial):
    m = trial.meta
    ws["A1"], ws["B1"] = "Name:", m.display_name
    ws["D1"], ws["E1"] = "Throw #:", m.throw_label
    ws["A2"], ws["B2"] = "Date:", format_date(m.date)
    ws["D2"], ws["E2"] = "Distance (m):", m.distance
    for ref in ("A1", "D1", "A2", "D2"):
        ws[ref].font = _BOLD

    ws["A4"] = "Release Parameters"
    ws["A4"].font = _TITLE
    rel = release_params(trial)
    _header_row(ws, 5, ["Release Speed (m/s)", "Release Angle (deg)", "Vert Release Velocity (m/s)",
                        "Horz Release Velocity (m/s)", "Release Height (m)"])
    for c, key in enumerate(["speed", "angle", "v_vertical", "v_horizontal", "height"], start=1):
        ws.cell(6, c, round(rel[key], 4))
    ws["A7"] = "Release angle: path tangent (central difference) at release - 1 frame"
    ws["A7"].font = Font(italic=True, color="64748B")

    ws["A9"] = "Support Phase Data"
    ws["A9"].font = _TITLE
    _header_row(ws, 10, ["Phase", "Duration (s)", "Change in Speed (m/s)", "Accumulative Timing (s)",
                         "Duration (%)"])
    for r, row in enumerate(phase_table(trial).itertuples(), start=11):
        ws.cell(r, 1, row.phase)
        ws.cell(r, 2, round(row.duration, 4))
        ws.cell(r, 3, round(row.speed_change, 4))
        ws.cell(r, 4, round(row.cumulative, 4))
        ws.cell(r, 5, round(row.duration_pct, 1))

    ws["A16"] = "Key Positions"
    ws["A16"].font = _TITLE
    _header_row(ws, 17, ["Event", "Time (s)", "ML (m)", "AP (m)", "VT (m)", "Speed (m/s)"])
    for r, row in enumerate(event_snapshot_table(trial).itertuples(), start=18):
        ws.cell(r, 1, row.event)
        for c, v in enumerate([row.time, row.ml, row.ap, row.vt, row.speed], start=2):
            ws.cell(r, c, round(float(v), 4))

    for c, width in enumerate([28, 18, 22, 22, 18, 14], start=1):
        ws.column_dimensions[get_column_letter(c)].width = width
    ws.row_dimensions[5].height = ws.row_dimensions[10].height = 32


def report_workbook(trials: list[Trial]) -> bytes:
    """One report sheet per trial plus a time-series sheet per trial."""
    wb = Workbook()
    wb.remove(wb.active)
    for trial in trials:
        name = trial.meta.key[:31]
        _write_sheet(wb.create_sheet(name), trial)
        ts = wb.create_sheet(f"{name[:27]}_ts")
        cols = ["time", "ml", "ap", "vt", "ml_f", "ap_f", "vt_f", "v_ml", "v_ap", "v_vt", "speed"]
        ts.append(cols)
        for row in trial.data[cols].itertuples(index=False):
            ts.append([float(v) for v in row])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
