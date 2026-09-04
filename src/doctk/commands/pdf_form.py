"""Listar, rellenar y aplanar campos de formularios PDF (AcroForm) con pypdf.

Modos:
  --list                    lista campos con tipo, páginas y rect
  --list --export-yaml F    además genera una plantilla YAML con todos los campos
  --data F --output O       rellena el PDF con {campo: valor} desde YAML/JSON
  --data F --output O --flatten   aplana (texto fijo, sin campos; requiere reportlab)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import DictionaryObject


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-i", "--input", required=True, type=Path, help="PDF de entrada (form).")
    parser.add_argument("--list", action="store_true", help="Sólo listar campos.")
    parser.add_argument("--export-yaml", type=Path, help="Exporta plantilla YAML con los campos.")
    parser.add_argument("--data", type=Path, help="YAML/JSON con {campo: valor} para rellenar.")
    parser.add_argument("-o", "--output", type=Path, help="PDF de salida.")
    parser.add_argument("--flatten", action="store_true", help="Aplanar (requiere reportlab).")


# ---------------- Utilidades ----------------
def _load_data(path: Path | None) -> dict[str, Any]:
    if not path:
        return {}
    if not path.exists():
        raise SystemExit(f"No existe el archivo de datos: {path}")
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yml", ".yaml"):
        try:
            import yaml
        except ImportError:
            raise SystemExit("Instala PyYAML: pip install pyyaml") from None
        return yaml.safe_load(text) or {}
    return json.loads(text)


def _set_need_appearances(writer: PdfWriter) -> None:
    from pypdf.generic import BooleanObject, DictionaryObject, NameObject

    root = writer._root_object
    if "/AcroForm" in root:
        root["/AcroForm"].update({NameObject("/NeedAppearances"): BooleanObject(True)})
    else:
        root.update({
            NameObject("/AcroForm"): writer._add_object(
                DictionaryObject({NameObject("/NeedAppearances"): BooleanObject(True)})
            )
        })


def _field_type(widget: DictionaryObject) -> str:
    from pypdf.generic import DictionaryObject

    ft = widget.get("/FT")
    if ft == "/Btn":
        ap = widget.get("/AP")
        if ap and "/N" in ap and isinstance(ap["/N"], DictionaryObject):
            if len(list(ap["/N"].keys())) > 2:
                return "radio"
        return "checkbox"
    if ft == "/Tx":
        return "text"
    if ft == "/Ch":
        return "choice"
    return "unknown"


def _widgets_by_name(reader: PdfReader) -> dict[str, list[DictionaryObject]]:
    mapping: dict[str, list] = {}
    for page in reader.pages:
        annots = page.get("/Annots")
        if not annots:
            continue
        for w in annots:
            if w.get("/Subtype") != "/Widget":
                continue
            name = w.get("/T")
            if not name:
                continue
            mapping.setdefault(str(name), []).append(w)
    return mapping


# ---------------- Listado / Export ----------------
def _list_fields(reader: PdfReader) -> list[dict]:
    from pypdf.generic import DictionaryObject

    root = reader.trailer["/Root"]
    acro = root.get("/AcroForm")
    if not acro or "/Fields" not in acro:
        print("No se encontraron campos de formulario.")
        return []

    name_to_widgets = _widgets_by_name(reader)
    results = []
    for name, widgets in name_to_widgets.items():
        types = {_field_type(w) for w in widgets}
        ftype = " / ".join(sorted(types)) or "text"

        pages_rects = []
        for page_idx, page in enumerate(reader.pages):
            for w in page.get("/Annots") or []:
                if w.get("/Subtype") != "/Widget" or str(w.get("/T")) != name:
                    continue
                rect = tuple(int(float(x)) for x in (w.get("/Rect") or [0, 0, 0, 0]))
                pages_rects.append((page_idx + 1, rect))

        options = []
        for w in widgets:
            ap = w.get("/AP")
            if ap and "/N" in ap and isinstance(ap["/N"], DictionaryObject):
                options.extend(str(k) for k in ap["/N"].keys())
        options = sorted({o for o in options if o not in ("None", "/Off")})

        results.append({"name": name, "type": ftype, "pages": pages_rects, "options": options})

    results.sort(key=lambda x: x["name"].lower())
    for r in results:
        p_str = ", ".join(f"p{p}" for p, _ in r["pages"]) or "?"
        rect0 = r["pages"][0][1] if r["pages"] else (0, 0, 0, 0)
        opt_str = f"  opciones={r['options']}" if r["options"] else ""
        print(f"{r['name']}\n  tipo={r['type']}  páginas={p_str}  rect={rect0}{opt_str}")
    return results


def _export_yaml(fields_info: list[dict], out_path: Path) -> None:
    try:
        import yaml
    except ImportError:
        raise SystemExit("Para exportar YAML instala pyyaml: pip install pyyaml") from None

    data: dict[str, Any] = {}
    for f in fields_info:
        data[f["name"]] = False if "checkbox" in f["type"] else ""
    out_path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=True), encoding="utf-8")
    print(f"Plantilla YAML creada: {out_path}")


# ---------------- Relleno / Aplanado ----------------
def _fill_fields(reader: PdfReader, data: dict[str, Any]):
    from pypdf import PdfWriter
    from pypdf.generic import NameObject, TextStringObject

    writer = PdfWriter()
    _set_need_appearances(writer)
    name_to_widgets = _widgets_by_name(reader)

    for name, value in data.items():
        for w in name_to_widgets.get(name, []):
            ftype = _field_type(w)
            if isinstance(value, bool) and "checkbox" in ftype:
                state = NameObject("/Yes") if value else NameObject("/Off")
                w.update({NameObject("/V"): state, NameObject("/AS"): state})
            elif "radio" in ftype:
                choice = str(value)
                if not choice:
                    continue
                if not choice.startswith("/"):
                    choice = "/" + choice
                obj = NameObject(choice)
                w.update({NameObject("/V"): obj, NameObject("/AS"): obj})
            else:
                w.update({NameObject("/V"): TextStringObject(str(value))})

    coords_por_pagina: list[list[tuple[str, tuple[float, float, float, float]]]] = []
    for page in reader.pages:
        draw_list = []
        for w in page.get("/Annots") or []:
            if w.get("/Subtype") != "/Widget":
                continue
            val = w.get("/V")
            if val is None:
                continue
            rect = tuple(float(x) for x in (w.get("/Rect") or [0, 0, 0, 0]))
            txt = str(val)
            if txt.startswith("/"):
                txt = "✔" if txt == "/Yes" else ("" if txt == "/Off" else txt[1:])
            draw_list.append((txt, rect))
        coords_por_pagina.append(draw_list)
        writer.add_page(page)

    acro = reader.trailer["/Root"].get("/AcroForm")
    if acro:
        writer._root_object.update({
            NameObject("/AcroForm"): writer._add_object(acro.get_object())
        })
    _set_need_appearances(writer)
    return writer, coords_por_pagina


def _flatten(writer: PdfWriter, coords_por_pagina, out_path: Path) -> None:
    try:
        from reportlab.pdfgen import canvas as rl_canvas
    except ImportError:
        raise SystemExit("Para --flatten necesitas reportlab: pip install reportlab") from None

    from pypdf import PdfReader as R2
    from pypdf import PdfWriter as W2

    tmp = out_path.with_suffix(".tmp.pdf")
    with tmp.open("wb") as f:
        writer.write(f)

    base = R2(str(tmp))
    out = W2()
    overlays: list[Path] = []
    for i, page in enumerate(base.pages):
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        ov_path = out_path.parent / f"._ov_{i}.pdf"
        c = rl_canvas.Canvas(str(ov_path), pagesize=(width, height))
        c.setFont("Helvetica", 9)
        for text, (x1, y1, _x2, _y2) in coords_por_pagina[i]:
            c.drawString(x1 + 2, y1 + 2, str(text))
        c.save()
        overlays.append(ov_path)

    for i, page in enumerate(base.pages):
        if i < len(overlays):
            ov = R2(str(overlays[i]))
            if len(ov.pages) > 0:
                page.merge_page(ov.pages[0])
        if "/Annots" in page:
            del page["/Annots"]
        out.add_page(page)

    with out_path.open("wb") as f:
        out.write(f)

    tmp.unlink(missing_ok=True)
    for p in overlays:
        p.unlink(missing_ok=True)


# ---------------- Entry point ----------------
def run(args: argparse.Namespace) -> int:
    from pypdf import PdfReader

    in_path: Path = args.input
    if not in_path.exists():
        raise SystemExit(f"No existe: {in_path}")

    reader = PdfReader(str(in_path))

    if args.list:
        fields_info = _list_fields(reader)
        if args.export_yaml:
            _export_yaml(fields_info, args.export_yaml)
        return 0

    data = _load_data(args.data)
    if not data:
        raise SystemExit("Falta --data (YAML/JSON). Usa --list/--export-yaml para tu plantilla.")

    writer, coords = _fill_fields(reader, data)
    out_path: Path = args.output or in_path.with_name(in_path.stem + "_relleno.pdf")

    if args.flatten:
        _flatten(writer, coords, out_path)
        print(f"✅ PDF aplanado creado: {out_path}")
    else:
        with out_path.open("wb") as f:
            writer.write(f)
        print(f"✅ PDF rellenado (no aplanado): {out_path}")
        print("   Nota: NeedAppearances=True; si un visor no muestra valores, usa --flatten.")
    return 0
