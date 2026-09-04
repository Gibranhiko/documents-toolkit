"""Helpers para leer comprobantes CFDI 4.0 del SAT (XML).

Centraliza namespaces, extracción de UUID/fecha y utilidades de texto usadas por
los comandos ``cfdi_*``.
"""

from __future__ import annotations

import unicodedata
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from pathlib import Path

# Namespaces CFDI / nómina 1.2 / timbre fiscal digital.
NS = {
    "cfdi": "http://www.sat.gob.mx/cfd/4",
    "nom": "http://www.sat.gob.mx/nomina12",
    "tfd": "http://www.sat.gob.mx/TimbreFiscalDigital",
}

# Etiquetas legibles para cada UsoCFDI de deducciones personales (D01–D10).
USO_MAP = {
    "D01": "HONORARIOS_MEDICOS",
    "D02": "MEDICOS_DISCAPACIDAD",
    "D03": "GASTOS_FUNERALES",
    "D04": "DONATIVOS",
    "D05": "INTERESES_HIPOTECARIOS",
    "D06": "APORTACIONES_SAR",
    "D07": "SEGURO_GASTOS_MEDICOS",
    "D08": "TRANSPORTE_ESCOLAR",
    "D09": "AHORRO_PENSIONES",
    "D10": "COLEGIATURAS",
}

MES_ES = [
    "", "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
    "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE",
]


def iter_xml(folder: Path) -> Iterator[tuple[Path, ET.Element]]:
    """Itera los ``*.xml`` de una carpeta devolviendo (ruta, raíz parseada).

    Los archivos que no se pueden parsear se omiten con una advertencia.
    """
    for xml_path in sorted(folder.glob("*.xml")):
        try:
            root = ET.parse(xml_path).getroot()
        except ET.ParseError as exc:
            print(f"⚠️  No pude leer {xml_path.name}: {exc}")
            continue
        yield xml_path, root


def get_timbre(root: ET.Element) -> ET.Element | None:
    """Devuelve el nodo TimbreFiscalDigital o ``None``."""
    return root.find(".//tfd:TimbreFiscalDigital", NS)


def get_uuid(root: ET.Element) -> str | None:
    """Devuelve el UUID del timbre fiscal, o ``None`` si no existe."""
    timbre = get_timbre(root)
    if timbre is None:
        return None
    return timbre.attrib.get("UUID") or None


def get_fecha(root: ET.Element) -> str | None:
    """Fecha del comprobante (``AAAA-MM-DD``) con fallback a la del timbre."""
    timbre = get_timbre(root)
    fecha_str = root.attrib.get("Fecha")
    if not fecha_str and timbre is not None:
        fecha_str = timbre.attrib.get("FechaTimbrado")
    return fecha_str[:10] if fecha_str else None


def sanitize(text: str) -> str:
    """Quita acentos y caracteres no ASCII (seguro para nombres de archivo en Windows)."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
