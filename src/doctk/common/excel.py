"""Escritura de resultados a Excel (openpyxl vía pandas)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd


def write_detail_and_totals(
    output: Path,
    sheet: str,
    detail: pd.DataFrame,
    totals: pd.DataFrame | None = None,
    extra: pd.DataFrame | None = None,
    gap: int = 2,
) -> None:
    """Escribe un DataFrame de detalle y, opcionalmente, totales/extra en un solo sheet.

    Cada bloque se escribe debajo del anterior con ``gap`` filas de separación.
    """
    import pandas as pd  # import perezoso: pandas es pesado

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        detail.to_excel(writer, sheet_name=sheet, index=False)
        cursor = len(detail) + gap
        if totals is not None and not totals.empty:
            totals.to_excel(writer, sheet_name=sheet, index=False, startrow=cursor)
            cursor += len(totals) + gap + 1
        if extra is not None and not extra.empty:
            extra.to_excel(writer, sheet_name=sheet, index=False, startrow=cursor)
