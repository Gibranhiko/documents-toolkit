"""Elimina páginas de un PDF por números sueltos o por rangos (base 1, inclusivos)."""

from __future__ import annotations

import argparse
from pathlib import Path

from doctk.common.paths import default_output


def _parse_range(text: str) -> tuple[int, int]:
    """Convierte ``'40-45'`` o ``'7'`` en una tupla (inicio, fin) inclusiva."""
    if "-" in text:
        start_s, end_s = text.split("-", 1)
        start, end = int(start_s), int(end_s)
    else:
        start = end = int(text)
    if start < 1 or end < start:
        raise argparse.ArgumentTypeError(f"Rango inválido: {text!r}")
    return start, end


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-i", "--input", required=True, type=Path, help="PDF de entrada.")
    parser.add_argument(
        "-o", "--output", type=Path,
        help="PDF de salida (por defecto: <nombre>_modificado.pdf).",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--pages", nargs="+", type=int, metavar="N",
        help="Páginas sueltas a eliminar (ej. --pages 2 5 7).",
    )
    group.add_argument(
        "--ranges", nargs="+", type=_parse_range, metavar="A-B",
        help="Rangos inclusivos a eliminar (ej. --ranges 1-5 40-45).",
    )


def run(args: argparse.Namespace) -> int:
    from pypdf import PdfReader, PdfWriter

    in_path: Path = args.input
    if not in_path.is_file():
        raise SystemExit(f"No existe el PDF: {in_path}")

    ranges = args.ranges if args.ranges else [(p, p) for p in args.pages]
    remove_indices: set[int] = set()
    for start, end in ranges:
        remove_indices.update(range(start - 1, end))

    reader = PdfReader(str(in_path))
    writer = PdfWriter()
    for i, page in enumerate(reader.pages):
        if i not in remove_indices:
            writer.add_page(page)

    output: Path = args.output or default_output(in_path)
    with output.open("wb") as f:
        writer.write(f)

    print(f"✅ PDF guardado en: {output} ({len(writer.pages)} páginas)")
    return 0
