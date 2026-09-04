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


def test_rmpages_removes_page(tmp_path: Path):
    pypdf = pytest.importorskip("pypdf")

    src = tmp_path / "in.pdf"
    writer = pypdf.PdfWriter()
    for _ in range(3):
        writer.add_blank_page(width=200, height=200)
    with src.open("wb") as f:
        writer.write(f)

    out = tmp_path / "out.pdf"
    rc = main(["pdf", "rmpages", "-i", str(src), "--pages", "2", "-o", str(out)])
    assert rc == 0
    assert len(pypdf.PdfReader(str(out)).pages) == 2
