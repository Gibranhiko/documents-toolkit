"""Concentra deducciones personales (CFDI) de una carpeta de XML a un Excel.

Deduplica por UUID, filtra por año y agrega totales por UsoCFDI.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from doctk.common import cfdi
from doctk.common.excel import write_detail_and_totals


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-i", "--input", required=True, type=Path,
        help="Carpeta con los XML de deducciones.",
    )
    parser.add_argument(
        "-y", "--year", type=int, required=True,
        help="Año a filtrar (ej. 2024).",
    )
    parser.add_argument(
        "-o", "--output", type=Path,
        help="Excel de salida (por defecto: hoja_deducciones_<año>.xlsx).",
    )


def run(args: argparse.Namespace) -> int:
    import pandas as pd

    folder: Path = args.input
    if not folder.is_dir():
        raise SystemExit(f"No existe la carpeta: {folder}")

    year = args.year
    output: Path = args.output or Path(f"hoja_deducciones_{year}.xlsx")

    uuids: set[str] = set()
    dups: list[dict] = []
    rows: list[dict] = []
    acum_por_uso: dict[str, float] = {}

    for xml_path, root in cfdi.iter_xml(folder):
        uuid = cfdi.get_uuid(root)
        if not uuid:
            continue
        if uuid in uuids:
            dups.append({"UUID": uuid, "Archivo": xml_path.name})
            continue
        uuids.add(uuid)

        fecha = cfdi.get_fecha(root)
        if not fecha:
            print(f"⚠️  Sin fecha en {xml_path.name}; omitido.")
            continue
        if not fecha.startswith(str(year)):
            continue

        subtotal = float(root.attrib.get("SubTotal", 0))
        total = float(root.attrib.get("Total", 0))

        impuestos = root.find("cfdi:Impuestos", cfdi.NS)
        iva = (
            float(impuestos.attrib.get("TotalImpuestosTrasladados", 0))
            if impuestos is not None
            else 0.0
        )

        emisor = root.find("cfdi:Emisor", cfdi.NS)
        receptor = root.find("cfdi:Receptor", cfdi.NS)
        emisor_rfc = emisor.attrib.get("Rfc") if emisor is not None else "?"
        emisor_nom = emisor.attrib.get("Nombre") if emisor is not None else "?"
        uso_cfdi = receptor.attrib.get("UsoCFDI") if receptor is not None else "?"

        rows.append({
            "UUID": uuid,
            "Fecha": fecha,
            "UsoCFDI": uso_cfdi,
            "RFCEmisor": emisor_rfc,
            "NombreEmisor": emisor_nom,
            "SubTotal": round(subtotal, 2),
            "IVA": round(iva, 2),
            "Total": round(total, 2),
            "Archivo": xml_path.name,
        })
        acum_por_uso[uso_cfdi] = acum_por_uso.get(uso_cfdi, 0) + total

    if not rows:
        print("No se encontraron comprobantes que cumplan el filtro.")
        return 1

    df_detalle = pd.DataFrame(rows)
    df_totales = pd.DataFrame({
        "UsoCFDI": list(acum_por_uso.keys()) + ["TOTAL GENERAL"],
        "Importe": [round(v, 2) for v in acum_por_uso.values()]
        + [round(sum(acum_por_uso.values()), 2)],
    })
    df_dups = pd.DataFrame(dups)

    write_detail_and_totals(
        output, f"Deducciones {year}", df_detalle, df_totales, extra=df_dups,
    )
    print(f"✅ Hoja de deducciones creada: {output}")

    if dups:
        print("\n⚠️  XML duplicados encontrados (omitidos):")
        for d in dups:
            print(f"  • {d['Archivo']}  → UUID {d['UUID']}")
    else:
        print("\n✅ No se encontraron XML duplicados.")
    return 0
