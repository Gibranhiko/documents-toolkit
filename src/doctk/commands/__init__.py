"""Subcomandos del CLI doctk.

Cada módulo expone ``add_arguments(parser)`` y ``run(args) -> int``.
Los imports pesados (pandas, fitz, pypdf, ...) se hacen dentro de ``run`` para que
construir el parser del CLI sea barato.
"""
