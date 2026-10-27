"""Tests para la exportación de contratos formales ACSL desde docblocks Doxygen (Ola 15 — Paso 2)."""

import json
from pathlib import Path
import shutil
import subprocess

from typer.testing import CliRunner

from corbel.cli import app
from corbel.core.acsl_exporter import export_header_contracts_dict, render_acsl
from corbel.core.doc_parser import parse_header_documentation

runner = CliRunner()


def test_export_acsl_desde_docblocks(tmp_path: Path):
    header = tmp_path / "contador.h"
    header.write_text(
        "#ifndef CONTADOR_H\n"
        "#define CONTADOR_H\n\n"
        "typedef struct contador {\n"
        "    int valor;\n"
        "} contador_t;\n\n"
        "/**\n"
        " * @brief Incrementa el contador en uno.\n"
        " * @param c Puntero al contador.\n"
        " * @return Nuevo valor del contador.\n"
        " * @pre \\valid(c)\n"
        " * @pre c->valor < 1000\n"
        " * @assigns c->valor\n"
        " * @post c->valor == \\old(c->valor) + 1\n"
        " * @post \\result == c->valor\n"
        " */\n"
        "int contador_incrementar(contador_t *c);\n\n"
        "#endif\n",
        encoding="utf-8",
    )

    doc = parse_header_documentation(header)
    acsl_code = render_acsl(doc, source_header=header)
    assert "requires \\valid(c);" in acsl_code
    assert "requires c->valor < 1000;" in acsl_code
    assert "assigns c->valor;" in acsl_code
    assert "ensures c->valor == \\old(c->valor) + 1;" in acsl_code
    assert "ensures \\result == c->valor;" in acsl_code
    assert "typedef struct contador" in acsl_code

    datos = export_header_contracts_dict(header)
    assert datos["total_functions"] == 1
    assert datos["functions_with_contracts"] == 1
    fn = datos["functions"][0]
    assert fn["requires"] == ["\\valid(c)", "c->valor < 1000"]
    assert fn["ensures"] == ["c->valor == \\old(c->valor) + 1", "\\result == c->valor"]


def test_cli_acsl_y_verificacion_frama_c_wp(tmp_path: Path):
    header = tmp_path / "contador.h"
    header.write_text(
        "#ifndef CONTADOR_H\n"
        "#define CONTADOR_H\n\n"
        "typedef struct contador {\n"
        "    int valor;\n"
        "} contador_t;\n\n"
        "/**\n"
        " * @brief Incrementa el contador.\n"
        " * @param c Puntero válido al TDA.\n"
        " * @return Valor actualizado.\n"
        " * @pre c != NULL (puntero válido)\n"
        " * @pre c->valor < 1000\n"
        " * @assigns c->valor\n"
        " * @post c->valor == \\old(c->valor) + 1\n"
        " * @post return == c->valor\n"
        " */\n"
        "int contador_incrementar(contador_t *c);\n\n"
        "#endif\n",
        encoding="utf-8",
    )

    out_h = tmp_path / "contador_acsl.h"
    res = runner.invoke(app, ["acsl", str(header), "-o", str(out_h)])
    assert res.exit_code == 0
    assert out_h.is_file()

    res_json = runner.invoke(app, ["acsl", str(header), "--json"])
    assert res_json.exit_code == 0
    payload = json.loads(res_json.stdout)
    assert payload["functions"][0]["requires"] == ["\\valid(c)", "c->valor < 1000"]
    assert payload["functions"][0]["ensures"] == [
        "c->valor == \\old(c->valor) + 1",
        "\\result == c->valor",
    ]

    if shutil.which("frama-c") and shutil.which("alt-ergo"):
        impl_c = tmp_path / "contador.c"
        impl_c.write_text(
            '#include "contador_acsl.h"\n\n'
            "int contador_incrementar(contador_t *c)\n"
            "{\n"
            "    c->valor = c->valor + 1;\n"
            "    return c->valor;\n"
            "}\n",
            encoding="utf-8",
        )
        proc = subprocess.run(
            ["frama-c", "-wp", "-wp-prover", "alt-ergo", str(impl_c)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0
        import re as _re
        assert _re.search(r"Proved goals:\s*([1-9]\d*)\s*/\s*\1\b", proc.stdout)
