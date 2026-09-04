"""Tests smoke: verifican que el CLI y las utilerías básicas funcionan.

No requieren dependencias pesadas (pandas/fitz) salvo el test de rmpages, que se
salta si pypdf no está instalado.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from doctk.cli import build_parser, main
from doctk.common.paths import default_output, expand_inputs


def test_build_parser_ok():
    parser = build_parser()
    assert parser.prog == "doctk"


def test_help_exits_zero(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    assert "doctk" in capsys.readouterr().out


@pytest.mark.parametrize("group", ["cfdi", "pdf", "spei"])
def test_group_help_exits_zero(group):
    with pytest.raises(SystemExit) as exc:
        main([group, "--help"])
    assert exc.value.code == 0


def test_missing_command_errors():
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code != 0


def test_default_output():
    assert default_output("/tmp/foo.pdf").name == "foo_modificado.pdf"


def test_expand_inputs_dir_and_glob(tmp_path: Path):
    (tmp_path / "a.pdf").write_bytes(b"%PDF-1.4")
    (tmp_path / "b.PDF").write_bytes(b"%PDF-1.4")
    (tmp_path / "c.txt").write_text("no")
    found = expand_inputs([tmp_path], {".pdf"})
    assert {p.name for p in found} == {"a.pdf", "b.PDF"}
    # deduplica al pasar carpeta + glob que apuntan a lo mismo
    found2 = expand_inputs([tmp_path, str(tmp_path / "*.pdf")], {".pdf"})
    assert len(found2) == 2


def _make_pdf(path: Path, pages: int) -> None:
    import pypdf

    writer = pypdf.PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=200)
    with path.open("wb") as f:
        writer.write(f)


def test_rmpages_removes_page(tmp_path: Path):
    pypdf = pytest.importorskip("pypdf")

    src = tmp_path / "in.pdf"
    _make_pdf(src, 3)

    out = tmp_path / "out.pdf"
    rc = main(["pdf", "rmpages", "-i", str(src), "--pages", "2", "-o", str(out)])
    assert rc == 0
    assert len(pypdf.PdfReader(str(out)).pages) == 2


def test_join_preserves_pages_in_order(tmp_path: Path):
    pypdf = pytest.importorskip("pypdf")

    a = tmp_path / "a.pdf"
    b = tmp_path / "b.pdf"
    _make_pdf(a, 2)
    _make_pdf(b, 3)

    out = tmp_path / "unido.pdf"
    rc = main(["pdf", "join", "-i", str(a), str(b), "-o", str(out)])
    assert rc == 0
    assert len(pypdf.PdfReader(str(out)).pages) == 5


def test_split_one_pdf_per_page(tmp_path: Path):
    pypdf = pytest.importorskip("pypdf")

    src = tmp_path / "doc.pdf"
    _make_pdf(src, 3)

    out_dir = tmp_path / "paginas"
    rc = main(["pdf", "split", "-i", str(src), "-o", str(out_dir)])
    assert rc == 0
    produced = sorted(out_dir.glob("*.pdf"))
    assert len(produced) == 3
    assert [p.name for p in produced] == ["doc_p1.pdf", "doc_p2.pdf", "doc_p3.pdf"]
    assert all(len(pypdf.PdfReader(str(p)).pages) == 1 for p in produced)
