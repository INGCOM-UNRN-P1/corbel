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


def test_los_esqueletos_viejos_de_gaff_sin_corchetes_tambien():
    """Los mismos textos que reconoce gaff (`_RE_DOC_ESQUELETO`): los de `gaff fix` anteriores."""
    fuente = ("/**\n * @brief Descripción de la función\n * @param a Descripción del parámetro\n"
              " * @return Descripción del valor de retorno\n */\nint f(int a);\n")
    (m,) = analyze_missing_documentation(fuente)
    assert m["type"] == "placeholder sin completar"
    assert m["missing_tags"] == ["@brief", "@param a", "@return"]


def test_una_descripcion_real_que_empieza_igual_no_es_placeholder():
    fuente = ("/**\n * @brief Descripción de la función de hash usada por la tabla.\n"
              " * @param a Descripción del parámetro en texto plano.\n */\nint f(int a);\n")
    assert analyze_missing_documentation(fuente) == []


def test_check_no_sugiere_scaffold_si_solo_faltan_completar_los_esqueletos(tmp_path):
    h = tmp_path / "p.h"
    h.write_text("/**\n * @file p.h\n * @brief Prueba.\n */\n"
                 "/**\n * @brief [completar: qué hace f]\n */\nint f(void);\n", encoding="utf-8")
    res = runner.invoke(app, ["check", str(h)])
    assert res.exit_code == 1
    assert "corbel scaffold p.h" not in res.stdout.replace("\n", " ") and "texto de relleno" in res.stdout
