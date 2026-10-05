"""Placeholders sin completar (revisión 07), @param desactualizados (QoL #122, #123) y cobertura (#124)."""

import json
from pathlib import Path

from typer.testing import CliRunner

from corbel.cli import app
from corbel.core.placeholder import analizar_docblock_incompleto, analyze_missing_documentation, cobertura

runner = CliRunner()
LISTA = Path(__file__).parent / "datos" / "lista_cobertura.h"


def test_el_placeholder_cuenta_como_ausente_aun_sin_completitud():
    faltan = {m["name"]: m["type"] for m in analyze_missing_documentation(LISTA.read_text(encoding="utf-8"), "lista.h")}
    assert faltan["lista_agregar"] == "placeholder sin completar"
    assert "lista_largo" not in faltan  # sin --completitud, un docblock real alcanza


def test_el_placeholder_de_gaff_tambien():
    fuente = "/**\n * @brief [completar: qué hace f]\n */\nint f(void);\n"
    (m,) = analyze_missing_documentation(fuente)
    assert m["type"] == "placeholder sin completar"


def test_param_desactualizado_y_return_que_sobra():
    doc = "/**\n * @brief Suma.\n * @param x primero\n * @param y segundo\n * @return nada\n */"
    faltan = analizar_docblock_incompleto(doc, ["a", "y"], "void")
    assert "@param a" in faltan
    assert "@param x (no está en la firma: ¿se renombró?)" in faltan
    assert "@return sobra: la función es void" in faltan


def test_cobertura():
    c = cobertura(LISTA.read_text(encoding="utf-8"), "lista.h")
    assert (c["documentados"], c["total"], c["porcentaje"]) == (2, 5, 40.0)


def test_cli_coverage_con_minimo():
    res = runner.invoke(app, ["coverage", str(LISTA), "--json", "--min", "50"])
    datos = json.loads(res.stdout)
    assert res.exit_code == 1 and datos["porcentaje"] == 40.0 and not datos["passed"]
    assert runner.invoke(app, ["coverage", str(LISTA), "--min", "30"]).exit_code == 0
