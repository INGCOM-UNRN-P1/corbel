"""Tests unitarios y de integración para CORBEL."""

from pathlib import Path
from typer.testing import CliRunner
from corbel.cli import app
from corbel.core.doc_parser import parse_header_documentation
from corbel.core.renderers import render_markdown, render_man_page
from corbel.plugins.ripley_plugin import CorbelPlugin

runner = CliRunner()


def test_parse_header_doxygen(tmp_path):
    h = tmp_path / "lista.h"
    h.write_text("""
    /**
     * @brief Crea una nueva lista vacía en el Heap.
     * @param capacidad Tamaño inicial del búfer.
     * @return Puntero a la estructura t_lista creada o NULL en error.
     * @pre capacidad > 0
     * @post La lista tiene longitud 0.
     */
    t_lista* lista_crear(size_t capacidad);
    """)

    doc = parse_header_documentation(h)
    assert len(doc.functions) == 1
    fn = doc.functions[0]
    assert fn.name == "lista_crear"
    assert "Crea una nueva lista" in fn.brief
    assert len(fn.params) == 1
    assert fn.params[0].name == "capacidad"
    assert "capacidad > 0" in fn.preconditions


def test_render_markdown_and_man(tmp_path):
    h = tmp_path / "cola.h"
    h.write_text("""
    /**
     * @brief Desencola un elemento.
     * @param cola Puntero a la cola.
     * @return Elemento desencolado.
     */
    void* cola_desencolar(t_cola* cola);
    """)
    doc = parse_header_documentation(h)
    md = render_markdown(doc)
    assert "# cola.h" in md
    assert "cola_desencolar" in md

    man = render_man_page(doc)
    assert '.TH "COLA" 3' in man


def test_cli_doc_markdown(tmp_path):
    h = tmp_path / "tda.h"
    h.write_text("/** @brief Test */\nint foo(void);")
    out = tmp_path / "doc.md"
    res = runner.invoke(app, ["doc", str(h), "-f", "markdown", "-o", str(out)])
    assert res.exit_code == 0
    assert out.exists()


def test_cli_version():
    res = runner.invoke(app, ["version"])
    assert res.exit_code == 0
    assert "CORBEL" in res.output


def test_ripley_plugin(tmp_path):
    h = tmp_path / "test.h"
    h.write_text("/** @brief Test */\nvoid bar(void);")
    plugin = CorbelPlugin()
    res = plugin.run({"source_dir": str(tmp_path)})
    assert res["passed"] is True
    assert res["headers_documented"] == 1
