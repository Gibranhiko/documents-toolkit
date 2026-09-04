"""Intercala dos carpetas (frentes y reversos) en un PDF doble cara.

Orden resultante: frente1, reverso1, frente2, reverso2, ...
Útil cuando escaneas los reversos en orden inverso (usa --reverse-backs).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from doctk.common.pdfimg import (
    IMG_SUFFIXES,
    PDF_SUFFIXES,
    PageConfig,
    pages_from_file,
    save_pages_as_pdf,
    whatsapp_key,
)


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-f", "--fronts", required=True, type=Path, help="Carpeta de frentes.")
    parser.add_argument("-b", "--backs", required=True, type=Path, help="Carpeta de reversos.")
    parser.add_argument(
        "-o", "--output", type=Path, default=Path("documento_doble_cara.pdf"),
        help="PDF de salida (por defecto: documento_doble_cara.pdf).",
    )
    parser.add_argument(
        "--reverse-fronts", action="store_true", help="Procesar frentes en orden inverso.",
    )
    parser.add_argument(
        "--reverse-backs", action="store_true", help="Procesar reversos en orden inverso.",
    )
    parser.add_argument("--dpi", type=int, default=300, help="Resolución (por defecto 300).")
    parser.add_argument("--margin", type=int, default=60, help="Margen en px (por defecto 60).")


def _files_in(folder: Path) -> list[Path]:
    accepted = IMG_SUFFIXES | PDF_SUFFIXES
    return sorted(
        (p for p in folder.iterdir() if p.suffix.lower() in accepted),
        key=whatsapp_key,
    )


def run(args: argparse.Namespace) -> int:
    for folder, label in [(args.fronts, "frentes"), (args.backs, "reversos")]:
        if not folder.is_dir():
            raise SystemExit(f"⚠️  La carpeta de {label} no existe: {folder}")

    cfg = PageConfig(dpi=args.dpi, margin_px=args.margin)
    frentes = _files_in(args.fronts)
    reversos = _files_in(args.backs)

    if args.reverse_fronts:
        frentes.reverse()
        print("🔄 Frentes  : orden invertido")
    if args.reverse_backs:
        reversos.reverse()
        print("🔄 Reversos : orden invertido")

    if not frentes:
        raise SystemExit(f"⚠️  No se encontraron archivos en frentes: {args.fronts.resolve()}")
    if not reversos:
        raise SystemExit(f"⚠️  No se encontraron archivos en reversos: {args.backs.resolve()}")
    if len(frentes) != len(reversos):
        print(f"⚠️  {len(frentes)} frentes vs {len(reversos)} reversos. Se intercala hasta el mínimo.")

    print(f"📂 Frentes  : {len(frentes)} archivo(s)")
    print(f"📂 Reversos : {len(reversos)} archivo(s)")

    pages = []
    total_pares = min(len(frentes), len(reversos))
    for i in range(total_pares):
        print(f"  [{i + 1}/{total_pares}] {frentes[i].name}  +  {reversos[i].name}")
        pages.extend(pages_from_file(frentes[i], cfg))
        pages.extend(pages_from_file(reversos[i], cfg))
    for i in range(total_pares, len(frentes)):
        print(f"  [frente extra] {frentes[i].name}")
        pages.extend(pages_from_file(frentes[i], cfg))

    save_pages_as_pdf(pages, args.output, cfg.dpi)
    print(f"\n✅ PDF generado: {args.output}  ({len(pages)} páginas)")
    return 0
