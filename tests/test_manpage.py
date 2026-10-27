"""Tests para `corbel manpage` (Ola 15 — Paso 3: generador de páginas de manual UNIX man 3)."""

import json
import os
from pathlib import Path
import shutil
import subprocess

from typer.testing import CliRunner

from corbel.cli import app

runner = CliRunner()


def test_corbel_manpage_treadstone_y_consulta_man3(tmp_path: Path):
    man_base = tmp_path / "man"
    out_3 = tmp_path / "treadstone.3"

    res = runner.invoke(
        app,
        ["manpage", "treadstone.h", "-o", str(out_3), "--install-dir", str(man_base)],
    )
    assert res.exit_code == 0
    assert out_3.is_file()
    installed_3 = man_base / "man3" / "treadstone.3"
    assert installed_3.is_file()

    troff = out_3.read_text(encoding="utf-8")
    assert '.TH "TREADSTONE" 3 "treadstone.h"' in troff
    assert ".SH NAME" in troff
    assert ".SH SYNOPSIS" in troff
    assert ".SH DESCRIPTION" in troff
    assert ".SH FUNCTIONS" in troff
    assert ".SH MACROS" in troff
    assert "ASSERT_EQ" in troff
    assert "p1_read_int" in troff

    if shutil.which("man"):
        env = dict(os.environ)
        env["MANPATH"] = str(man_base)
        env["MANPAGER"] = "cat"
        env["PAGER"] = "cat"
        proc = subprocess.run(
            ["man", "3", "treadstone"],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0
        assert "TREADSTONE(3)" in proc.stdout
        assert "ASSERT_EQ" in proc.stdout


def test_corbel_manpage_stdout_json_y_error(tmp_path: Path):
    res_stdout = runner.invoke(app, ["manpage", "treadstone.h", "--no-install"])
    assert res_stdout.exit_code == 0
    assert '.TH "TREADSTONE" 3' in res_stdout.stdout

    res_json = runner.invoke(app, ["manpage", "treadstone.h", "--no-install", "--json"])
    assert res_json.exit_code == 0
    payload = json.loads(res_json.stdout)
    assert payload["module"] == "treadstone"
    assert payload["functions_count"] > 0
    assert payload["macros_count"] > 0

    res_missing = runner.invoke(app, ["manpage", "no_existe_ninguna_lib.h", "--no-install"])
    assert res_missing.exit_code != 0
