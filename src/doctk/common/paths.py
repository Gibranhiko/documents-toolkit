"""Resolución y expansión de rutas de entrada.

Reglas comunes a varios comandos: aceptar archivos, carpetas o patrones glob,
deduplicar por ruta absoluta y filtrar por extensión.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path


def expand_inputs(inputs: Iterable[str | Path], suffixes: set[str]) -> list[Path]:
    """Expande una lista de entradas (archivo/carpeta/glob) a archivos únicos.

    Args:
        inputs: rutas o patrones. Una carpeta se expande a su contenido directo.
        suffixes: extensiones aceptadas en minúsculas, con punto (ej. ``{".pdf"}``).

    Returns:
        Lista de :class:`~pathlib.Path` absolutas, sin duplicados, en orden estable.
    """
    files: list[Path] = []
    seen: set[Path] = set()

    def _add(path: Path) -> None:
        if path.is_file() and path.suffix.lower() in suffixes:
            resolved = path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                files.append(resolved)

    for raw in inputs:
        path = Path(raw)
        if path.is_dir():
            for child in sorted(path.iterdir()):
                _add(child)
        elif any(ch in str(raw) for ch in "*?["):
            base = path.parent if path.parent != Path("") else Path(".")
            for match in sorted(base.glob(path.name)):
                _add(match)
        else:
            _add(path)

    return files


def default_output(input_path: str | Path, suffix: str = "_modificado") -> Path:
    """Deriva una ruta de salida a partir del input: ``<stem><suffix><ext>``."""
    p = Path(input_path)
    return p.with_name(f"{p.stem}{suffix}{p.suffix}")
