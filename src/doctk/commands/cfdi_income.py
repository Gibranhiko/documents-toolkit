"""Concentra ingresos por nómina (CFDI nómina 1.2) de una carpeta de XML a Excel.

Deduplica por UUID, filtra por año, separa percepciones gravadas/exentas y calcula
ISR retenido y subsidio al empleo.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from doctk.common import cfdi
from doctk.common.excel import write_detail_and_totals


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-i", "--input", required=True, type=Path,
        help="Carpeta con los XML de ingresos (nómina).",
    )
    parser.add_argument(
        "-y", "--year", type=int, required=True,
        help="Año a filtrar (ej. 2024).",
    )
    parser.add_argument(
        "-o", "--output", type=Path,
        help="Excel de salida (por defecto: hoja_sueldos_<año>.xlsx).",
    )


def run(args: argparse.Namespace) -> int:
    import pandas as pd

    folder: Path = args.input
    if not folder.is_dir():
        raise SystemExit(f"No existe la carpeta: {folder}")

    year = args.year
    output: Path = args.output or Path(f"hoja_sueldos_{year}.xlsx")

    uuids_vistos: set[str] = set()
    rows: list[dict] = []
    acum = dict.fromkeys(
        ("gravadas", "exentas", "percepciones", "ajustes", "isr", "subsidio"), 0.0
    )

    for xml_path, root in cfdi.iter_xml(folder):
        uuid = cfdi.get_uuid(root)
        if not uuid or uuid in uuids_vistos:
            continue
        uuids_vistos.add(uuid)

        for nom in root.findall(".//nom:Nomina", cfdi.NS):
            fecha_pago = nom.attrib.get("FechaFinalPago") or nom.attrib.get("FechaPago")
            if not fecha_pago or not fecha_pago.startswith(str(year)):
                continue

            tipo_nom = nom.attrib.get("TipoNomina")  # O / E
            total_perc = float(nom.attrib.get("TotalPercepciones", 0))
            total_ded = float(nom.attrib.get("TotalDeducciones", 0))

            ded_node = nom.find("nom:Deducciones", cfdi.NS)
            isr_ret = (
                float(ded_node.attrib.get("TotalImpuestosRetenidos", 0))
                if ded_node is not None
                else 0.0
            )

            otro = nom.find(".//nom:OtroPago[@TipoOtroPago='002']", cfdi.NS)
            subsidio = float(otro.attrib.get("Importe", 0)) if otro is not None else 0.0

            gravadas = exentas = 0.0
            for p in nom.findall(".//nom:Percepcion", cfdi.NS):
                gravadas += float(p.attrib.get("ImporteGravado", 0))
                exentas += float(p.attrib.get("ImporteExento", 0))

            # Ajustes: CFDI con percepciones 0 y deducciones > 0 (tipo Ordinario).
            if total_perc == 0 and total_ded > 0 and tipo_nom == "O":
                acum["ajustes"] += total_ded
            else:
                acum["percepciones"] += total_perc
                acum["gravadas"] += gravadas
                acum["exentas"] += exentas

            acum["isr"] += isr_ret
            acum["subsidio"] += subsidio

            rows.append({
                "UUID": uuid,
                "FechaPago": fecha_pago,
                "TipoNomina": tipo_nom,
                "PercGravadas": round(gravadas, 2),
                "PercExentas": round(exentas, 2),
                "TotalPercepciones": round(total_perc, 2),
                "TotalDeducciones": round(total_ded, 2),
                "ISRRetenido": round(isr_ret, 2),
                "SubsidioEmpleado": round(subsidio, 2),
                "NetoPagado": round(total_perc - total_ded, 2),
                "ArchivoXML": xml_path.name,
            })

    if not rows:
        print("No se encontraron comprobantes de nómina que cumplan el filtro.")
        return 1

    df_detalle = pd.DataFrame(rows)
    df_totales = pd.DataFrame({
        "Concepto": [
            "Percepciones gravadas",
            "Percepciones exentas",
            "Ingresos por sueldos y salarios",
            "(-) Ajustes sueldos y salarios",
            "Total ingresos según SAT",
            "ISR retenido",
            "Subsidio al empleo entregado",
        ],
        "Importe": [
            round(acum["gravadas"], 2),
            round(acum["exentas"], 2),
            round(acum["percepciones"], 2),
            round(acum["ajustes"], 2),
            round(acum["percepciones"] - acum["ajustes"], 2),
            round(acum["isr"], 2),
            round(acum["subsidio"], 2),
        ],
    })

    write_detail_and_totals(output, f"Hoja {year}", df_detalle, df_totales)
    print(f"✅ Hoja de trabajo creada: {output}")
    return 0
