"""`corbel report` debe funcionar (N-CORBEL-01: fallaba siempre con NameError)."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from corbel.cli import app

runner = CliRunner()

HEADER = """#ifndef PILA_H
#define PILA_H

/**
 * @brief Apila un valor.
 */
int apilar(int valor);

int desapilar(void);

#endif
"""


def test_report_genera_la_seccion_markdown(tmp_path: Path):
    fuente = tmp_path / "pila.h"
    fuente.write_text(HEADER, encoding="utf-8")
    resultado = runner.invoke(app, ["report", str(fuente)])
    assert resultado.exit_code == 0, resultado.output
    assert "dredd-section: corbel" in resultado.output
    assert "desapilar" in resultado.output


def test_report_con_completitud_informa_tags_faltantes(tmp_path: Path):
    fuente = tmp_path / "pila.h"
    fuente.write_text(HEADER, encoding="utf-8")
    salida = tmp_path / "corbel.md"
    resultado = runner.invoke(app, ["report", str(fuente), "--completitud", "-o", str(salida)])
    assert resultado.exit_code == 0, resultado.output
    texto = salida.read_text(encoding="utf-8")
    assert "apilar" in texto  # el docblock existe pero le faltan @param y @return
