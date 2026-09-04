"""Busca una palabra o patrón en PDFs y reporta las páginas donde aparece."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from doctk.common.paths import expand_inputs


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-p", "--path", required=True, nargs="+",
        help="Uno o más PDFs, carpetas o patrones glob donde buscar.",
    )
    parser.add_argument(
        "-k", "--keyword", required=True,
        help="Texto a buscar (literal por defecto).",
    )
    parser.add_argument(
        "--regex", action="store_true",
        help="Interpretar --keyword como expresión regular.",
    )


def _pages_with_pattern(pdf: Path, rx: re.Pattern) -> list[int]:
    import fitz  # PyMuPDF

    hits: list[int] = []
    with fitz.open(pdf) as doc:
        for i, page in enumerate(doc, start=1):
            if rx.search(page.get_text("text")):
                hits.append(i)
    return hits


def run(args: argparse.Namespace) -> int:
    import fitz  # PyMuPDF

    fitz.TOOLS.mupdf_display_errors(False)
    fitz.TOOLS.mupdf_display_warnings(False)

    pattern = (
        re.compile(args.keyword, flags=re.I)
        if args.regex
        else re.compile(re.escape(args.keyword), flags=re.I)
    )

    pdfs = expand_inputs(args.path, {".pdf"})
    if not pdfs:
        print("No se encontraron PDFs en las rutas indicadas.")
        return 1

    encontrados = 0
    for pdf in pdfs:
        paginas = _pages_with_pattern(pdf, pattern)
        if paginas:
            encontrados += 1
            print(f"✅ {pdf.name}  (pág. {', '.join(map(str, paginas))})")
        else:
            print(f"   {pdf.name} … sin coincidencias")

    if encontrados == 0:
        print("Ningún PDF contiene el patrón solicitado.")
    return 0
