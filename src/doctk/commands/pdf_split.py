"""Divide un PDF en un archivo independiente por cada página."""

from __future__ import annotations

import argparse
from pathlib import Path


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-i", "--input", required=True, type=Path, help="PDF de entrada.")
    parser.add_argument(
        "-o", "--output", type=Path,
        help="Carpeta de salida (por defecto: <nombre>_paginas junto al PDF).",
    )
    parser.add_argument(
        "--prefix", default=None,
        help="Prefijo de los archivos generados (por defecto: el nombre del PDF).",
    )


def run(args: argparse.Namespace) -> int:
    from pypdf import PdfReader, PdfWriter

    in_path: Path = args.input
    if not in_path.is_file():
        raise SystemExit(f"No existe el PDF: {in_path}")

    reader = PdfReader(str(in_path))
    total = len(reader.pages)
    if total == 0:
        print("El PDF no tiene páginas.")
        return 1

    out_dir: Path = args.output or in_path.with_name(f"{in_path.stem}_paginas")
    out_dir.mkdir(parents=True, exist_ok=True)

    prefix = args.prefix or in_path.stem
    width = len(str(total))  # padding para orden léxico correcto (p01, p02, ...)

    for i, page in enumerate(reader.pages, start=1):
        writer = PdfWriter()
        writer.add_page(page)
        out_path = out_dir / f"{prefix}_p{i:0{width}d}.pdf"
        with out_path.open("wb") as f:
            writer.write(f)
        print(f"  → {out_path.name}")

    print(f"✅ {total} página(s) exportada(s) en: {out_dir.resolve()}")
    return 0
