"""Une varios PDFs en uno solo, sin pérdida y conservando el formato original.

A diferencia de ``pdf merge`` (que rasteriza imágenes/PDFs a páginas tamaño Carta),
``pdf join`` concatena las páginas tal cual, preservando texto vectorial, tamaño de
página y calidad. El orden de los PDFs es exactamente el orden en que se pasan.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from doctk.common.paths import expand_inputs


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-i", "--input", required=True, nargs="+",
        help="PDFs a unir, EN ORDEN. También acepta carpetas o globs (orden natural).",
    )
    parser.add_argument(
        "-o", "--output", type=Path, default=Path("unido.pdf"),
        help="PDF de salida (por defecto: unido.pdf).",
    )


def run(args: argparse.Namespace) -> int:
    from pypdf import PdfWriter

    pdfs = expand_inputs(args.input, {".pdf"})
    if not pdfs:
        print("No se encontraron PDFs en las rutas indicadas.")
        return 1
    if len(pdfs) == 1:
        print("⚠️  Sólo se encontró un PDF; nada que unir.")
        return 1

    writer = PdfWriter()
    for pdf in pdfs:
        writer.append(str(pdf))  # append preserva páginas, marcadores y estructura
        print(f"  + {pdf.name}")

    n_pages = len(writer.pages)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("wb") as f:
        writer.write(f)
    writer.close()

    print(f"✅ PDF unido: {args.output} ({n_pages} páginas)")
    return 0
