"""Punto de entrada del CLI ``doctk``.

Construye un árbol de subcomandos agrupados por dominio (``cfdi``, ``pdf``, ``spei``).
Cada módulo de :mod:`doctk.commands` expone ``add_arguments(parser)`` y ``run(args)``,
de modo que agregar un comando nuevo sólo requiere registrarlo en ``GROUPS``.
"""

from __future__ import annotations

import argparse
from importlib import import_module

from doctk import __version__

# Estructura: grupo -> lista de (nombre_subcomando, módulo, ayuda breve).
# Los módulos se importan de forma perezosa para no cargar dependencias pesadas
# (pandas, fitz, ...) hasta que el subcomando se usa realmente.
GROUPS: dict[str, tuple[str, list[tuple[str, str, str]]]] = {
    "cfdi": (
        "Procesar CFDI/XML del SAT (deducciones, ingresos, renombrado).",
        [
            ("deductions", "cfdi_deductions", "Concentrar deducciones personales a Excel."),
            ("income", "cfdi_income", "Concentrar ingresos por nómina a Excel."),
            ("rename", "cfdi_rename", "Copiar y renombrar XML de forma legible."),
        ],
    ),
    "pdf": (
        "Utilerías de PDF e imágenes.",
        [
            ("search", "pdf_search", "Buscar texto/patrón en PDFs y listar páginas."),
            ("form", "pdf_form", "Listar/rellenar/aplanar campos de un formulario PDF."),
            ("merge", "img2pdf", "Compilar imágenes y PDFs en un solo PDF tamaño Carta."),
            ("split", "pdf_split", "Dividir un PDF en un archivo por página."),
            ("duplex", "pdf_duplex", "Intercalar frentes y reversos en un PDF doble cara."),
            ("rmpages", "pdf_rmpages", "Eliminar páginas de un PDF."),
        ],
    ),
    "spei": (
        "Procesar comprobantes SPEI.",
        [
            ("extract", "spei_extract", "Extraer fecha/monto de comprobantes SPEI a Excel."),
        ],
    ),
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="doctk",
        description="Utilerías de línea de comandos para procesar documentos.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    group_sub = parser.add_subparsers(dest="group", metavar="GRUPO")
    group_sub.required = True

    for group_name, (group_help, commands) in GROUPS.items():
        group_parser = group_sub.add_parser(group_name, help=group_help)
        cmd_sub = group_parser.add_subparsers(dest="command", metavar="COMANDO")
        cmd_sub.required = True
        for cmd_name, module_name, cmd_help in commands:
            cmd_parser = cmd_sub.add_parser(cmd_name, help=cmd_help, description=cmd_help)
            cmd_parser.set_defaults(_module=f"doctk.commands.{module_name}")
            module = import_module(f"doctk.commands.{module_name}")
            module.add_arguments(cmd_parser)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    module = import_module(args._module)
    return int(module.run(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
