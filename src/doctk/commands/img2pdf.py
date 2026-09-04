"""Compila imágenes (JPEG/PNG) y PDFs de una carpeta en un único PDF tamaño Carta.

Usa PyMuPDF (fitz) para rasterizar PDFs, sin necesidad de poppler.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from doctk.common.pdfimg import (
    IMG_SUFFIXES,
    PDF_SUFFIXES,
    PageConfig,
    natural_key,
    pages_from_file,
    save_pages_as_pdf,
)


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-i", "--input", required=True, type=Path,
        help="Carpeta con imágenes y/o PDFs a compilar.",
    )
    parser.add_argument(
        "-o", "--output", type=Path, default=Path("salida.pdf"),
        help="PDF de salida (por defecto: salida.pdf).",
    )
    parser.add_argument("--dpi", type=int, default=300, help="Resolución (por defecto 300).")
    parser.add_argument("--margin", type=int, default=60, help="Margen en px (por defecto 60).")
    parser.add_argument(
        "--no-portrait", action="store_true",
        help="No forzar orientación vertical de las imágenes.",
    )


def run(args: argparse.Namespace) -> int:
    folder: Path = args.input
    if not folder.is_dir():
        raise SystemExit(f"No existe la carpeta: {folder}")

    cfg = PageConfig(dpi=args.dpi, margin_px=args.margin, force_portrait=not args.no_portrait)
    accepted = IMG_SUFFIXES | PDF_SUFFIXES
    archivos = sorted(
        (p for p in folder.iterdir() if p.suffix.lower() in accepted),
        key=natural_key,
    )
    if not archivos:
        raise SystemExit(f"⚠️  No se encontraron archivos válidos en {folder.resolve()}")

    pages = []
    for p in archivos:
        pages.extend(pages_from_file(p, cfg))

    save_pages_as_pdf(pages, args.output, cfg.dpi)
    print(f"✅ PDF generado: {args.output} ({len(pages)} páginas, Carta vertical)")
    return 0
