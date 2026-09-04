"""Copia XML de deducciones a una carpeta destino con nombres legibles.

Nuevo nombre: ``<UsoCFDI legible> - <MES> - <RFC emisor> - <UUID>.xml``.
Deduplica por UUID.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from doctk.common import cfdi


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-i", "--input", required=True, type=Path,
        help="Carpeta origen con los XML.",
    )
    parser.add_argument(
        "-o", "--output", type=Path, default=Path("./xml_renombrados"),
        help="Carpeta destino (por defecto: ./xml_renombrados).",
    )


def run(args: argparse.Namespace) -> int:
    origen: Path = args.input
    destino: Path = args.output
    if not origen.is_dir():
        raise SystemExit(f"No existe la carpeta origen: {origen}")
    destino.mkdir(parents=True, exist_ok=True)

    uuids_vistos: set[str] = set()
    copiados = saltados = 0

    for xml_path, root in cfdi.iter_xml(origen):
        uuid = cfdi.get_uuid(root)
        if not uuid:
            print(f"⚠️  Sin timbre/UUID en {xml_path.name}; omitido.")
            continue
        if uuid in uuids_vistos:
            saltados += 1
            continue
        uuids_vistos.add(uuid)

        fecha = cfdi.get_fecha(root)
        if not fecha:
            print(f"⚠️  Sin fecha en {xml_path.name}; omitido.")
            continue
        try:
            mes_es = cfdi.MES_ES[int(fecha[5:7])]
        except (ValueError, IndexError):
            mes_es = "MES_DESCONOCIDO"

        receptor = root.find("cfdi:Receptor", cfdi.NS)
        uso_cfdi = receptor.attrib.get("UsoCFDI") if receptor is not None else "SIN_USO"
        etiqueta_uso = cfdi.USO_MAP.get(uso_cfdi, uso_cfdi)

        emisor = root.find("cfdi:Emisor", cfdi.NS)
        rfc_emisor = emisor.attrib.get("Rfc") if emisor is not None else "RFC_DESCONOCIDO"

        nuevo_nombre = cfdi.sanitize(
            f"{etiqueta_uso} - {mes_es} - {rfc_emisor} - {uuid}.xml"
        )
        try:
            shutil.copy2(xml_path, destino / nuevo_nombre)
            copiados += 1
        except OSError as exc:
            print(f"⚠️  Error al copiar {xml_path.name}: {exc}")

    print(f"\n✅ Copiados únicos: {copiados}")
    print(f"🚫 Duplicados omitidos: {saltados}")
    print(f"📂 Carpeta destino: {destino.resolve()}")
    return 0
