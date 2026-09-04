"""Utilerías de imagen y PDF compartidas por los comandos ``pdf merge`` y ``pdf duplex``.

Convierte imágenes/PDFs a páginas tamaño Carta usando PIL + PyMuPDF (sin poppler).
Los imports de PIL/fitz son perezosos para no exigirlos al construir el CLI.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL.Image import Image

IMG_SUFFIXES = {".jpg", ".jpeg", ".png"}
PDF_SUFFIXES = {".pdf"}


@dataclass(frozen=True)
class PageConfig:
    """Configuración de página para el lienzo de salida."""

    dpi: int = 300
    margin_px: int = 60
    force_portrait: bool = True
    background: str = "white"
    width_in: float = 8.5
    height_in: float = 11.0

    @property
    def page_w(self) -> int:
        return int(self.width_in * self.dpi)

    @property
    def page_h(self) -> int:
        return int(self.height_in * self.dpi)


def natural_key(path: Path):
    """Clave de orden natural: números como enteros para ordenar 2 < 10."""
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", path.name)]


def whatsapp_key(path: Path) -> str:
    """Orden por timestamp de WhatsApp si aplica; si no, orden natural con padding."""
    name = path.stem
    m = re.search(
        r"(\d{4}-\d{2}-\d{2}) at (\d{2})\.(\d{2})\.(\d{2}) (AM|PM)(?:\s*\((\d+)\))?",
        name,
        re.IGNORECASE,
    )
    if m:
        date = m.group(1)
        hh, mm, ss = int(m.group(2)), int(m.group(3)), int(m.group(4))
        idx = int(m.group(6)) if m.group(6) else 0
        if m.group(5).upper() == "PM" and hh != 12:
            hh += 12
        elif m.group(5).upper() == "AM" and hh == 12:
            hh = 0
        return f"1_{date}_{hh:02d}{mm:02d}{ss:02d}_{idx:06d}"
    return "0_" + re.sub(r"(\d+)", lambda x: x.group().zfill(10), name.lower())


def load_image(img_path: Path, cfg: PageConfig) -> Image:
    """Abre una imagen, corrige orientación EXIF y opcionalmente fuerza vertical."""
    from PIL import Image as PILImage
    from PIL import ImageOps

    img = PILImage.open(img_path)
    img = ImageOps.exif_transpose(img)
    if img.mode != "RGB":
        img = img.convert("RGB")
    if cfg.force_portrait and img.width > img.height:
        img = img.rotate(-90, expand=True)
    return img


def place_on_page(img: Image, cfg: PageConfig) -> Image:
    """Centra la imagen (escalada a los márgenes) en un lienzo tamaño página."""
    from PIL import Image as PILImage

    canvas = PILImage.new("RGB", (cfg.page_w, cfg.page_h), cfg.background)
    max_w = cfg.page_w - 2 * cfg.margin_px
    max_h = cfg.page_h - 2 * cfg.margin_px
    scale = min(max_w / img.width, max_h / img.height)
    new_w = max(1, int(img.width * scale))
    new_h = max(1, int(img.height * scale))
    resized = img.resize((new_w, new_h), PILImage.LANCZOS)
    x = (cfg.page_w - new_w) // 2
    y = (cfg.page_h - new_h) // 2
    canvas.paste(resized, (x, y))
    return canvas


def pdf_to_images(pdf_path: Path, cfg: PageConfig) -> list[Image]:
    """Rasteriza cada página de un PDF a imágenes PIL usando PyMuPDF."""
    import fitz  # PyMuPDF
    from PIL import Image as PILImage

    images: list[Image] = []
    try:
        with fitz.open(pdf_path) as doc:
            for page in doc:
                pix = page.get_pixmap(dpi=cfg.dpi)
                images.append(PILImage.frombytes("RGB", [pix.width, pix.height], pix.samples))
    except Exception as exc:  # noqa: BLE001 - fitz lanza excepciones variadas
        print(f"⚠️  Error procesando PDF {pdf_path.name}: {exc}")
    return images


def pages_from_file(path: Path, cfg: PageConfig) -> list[Image]:
    """Devuelve las páginas (lienzos tamaño Carta) para un archivo imagen o PDF."""
    ext = path.suffix.lower()
    try:
        if ext in PDF_SUFFIXES:
            return [place_on_page(img, cfg) for img in pdf_to_images(path, cfg)]
        if ext in IMG_SUFFIXES:
            img = load_image(path, cfg)
            page = place_on_page(img, cfg)
            img.close()
            return [page]
    except Exception as exc:  # noqa: BLE001
        print(f"⚠️  Error con {path.name}: {exc}")
    return []


def save_pages_as_pdf(pages: list[Image], output: Path, dpi: int) -> None:
    """Guarda una lista de páginas PIL en un único PDF."""
    if not pages:
        raise SystemExit("⚠️  No hubo páginas válidas. Abortando.")
    first, rest = pages[0], pages[1:]
    first.save(output, format="PDF", resolution=dpi, save_all=True, append_images=rest)
    for page in pages:
        page.close()
