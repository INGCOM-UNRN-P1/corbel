"""Tests unitarios y de integración para CORBEL."""

from pathlib import Path
from typer.testing import CliRunner
from corbel.cli import app
from corbel.core.doc_parser import parse_header_documentation
from corbel.core.renderers import render_markdown, render_man_page
from corbel.core.placeholder import (
    inject_placeholders,
    analyze_missing_documentation,
    split_c_params,
    extract_param_name
)
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


def test_cli_doc_formats_and_stdout(tmp_path):
    h = tmp_path / "tda.h"
    h.write_text("/** @brief Test */\nint foo(void);\n/** @brief Bar */\nvoid bar(int a);")

    # JSON a stdout
    res_json = runner.invoke(app, ["doc", str(h), "-f", "json"])
    assert res_json.exit_code == 0
    assert '"header_name": "tda.h"' in res_json.stdout

    # JSON a archivo
    out_json = tmp_path / "doc.json"
    res_json_f = runner.invoke(app, ["doc", str(h), "-f", "json", "-o", str(out_json)])
    assert res_json_f.exit_code == 0
    assert out_json.is_file()

    # Man a stdout
    res_man = runner.invoke(app, ["doc", str(h), "-f", "man"])
    assert res_man.exit_code == 0
    assert '.TH "TDA" 3' in res_man.stdout

    # Man a archivo
    out_man = tmp_path / "doc.3"
    res_man_f = runner.invoke(app, ["doc", str(h), "-f", "man", "-o", str(out_man)])
    assert res_man_f.exit_code == 0
    assert out_man.is_file()

    # Markdown a stdout (tabla rica en consola)
    res_term = runner.invoke(app, ["doc", str(h)])
    assert res_term.exit_code == 0
    assert "Funciones Documentadas en tda.h" in res_term.stdout


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


# ---------------------------------------------------------------------------
# Tests para generación e inyección de placeholders
# ---------------------------------------------------------------------------

def test_extract_param_names():
    assert extract_param_name("int a") == "a"
    assert extract_param_name("const char *str") == "str"
    assert extract_param_name("void") is None
    assert extract_param_name("int (*cmp)(const void *, const void *)") == "cmp"
    assert extract_param_name("int *") == "param1"
    assert extract_param_name("...") == "..."
    assert extract_param_name("const uint32_t *") == "param1"


def test_split_c_params():
    params = "int a, void (*cb)(int x, int y), char *b"
    res = split_c_params(params)
    assert len(res) == 3
    assert res[0] == "int a"
    assert res[1] == "void (*cb)(int x, int y)"
    assert res[2] == "char *b"


def test_inject_placeholders_full_header():
    code = """#ifndef ARBOL_H
#define ARBOL_H

typedef struct nodo_arbol {
    int valor;
    struct nodo_arbol *izq;
    struct nodo_arbol *der;
} nodo_arbol_t;

typedef enum tipo_recorrido {
    IN_ORDER,
    PRE_ORDER,
    POST_ORDER
} tipo_recorrido_t;

typedef void (*visitar_fn)(int valor, void *extra);
typedef unsigned long hash_t;

nodo_arbol_t *arbol_crear(int valor_raiz);

bool arbol_insertar(nodo_arbol_t *arbol, int valor);

void arbol_recorrer(nodo_arbol_t *arbol, tipo_recorrido_t tipo, visitar_fn fn, void *extra);

void arbol_destruir(nodo_arbol_t *arbol);

#endif
"""
    result = inject_placeholders(code, filename="arbol.h", include_file_header=True)

    # 1. File header
    assert "@file arbol.h" in result
    # 2. Struct & Enum
    assert "@brief [Descripción de typedef struct nodo_arbol]" in result
    assert "@brief [Descripción de typedef enum tipo_recorrido]" in result
    # 3. Typedef fn & simple
    assert "@brief [Descripción del puntero a función visitar_fn]" in result
    assert "@brief [Descripción del tipo hash_t]" in result
    # 4. Functions
    assert "@brief [Descripción breve de la función arbol_crear]" in result
    assert "@param valor_raiz" in result
    assert "@return [Descripción del valor de retorno]" in result
    assert "@brief [Descripción breve de la función arbol_insertar]" in result
    assert "@param arbol" in result
    assert "@param valor" in result
    assert "@brief [Descripción breve de la función arbol_destruir]" in result
    assert "@param arbol" in result
    # void return no debe tener @return
    assert "@return" not in result[result.find("arbol_destruir") - 150:result.find("arbol_destruir")]


def test_inject_placeholders_preserves_existing_docs():
    code = """/**
 * @file modulo.h
 * @brief Archivo ya documentado
 */

/**
 * @brief Estructura existente
 */
struct punto {
    int x;
    int y;
};

/**
 * @brief Suma dos números ya documentada
 * @param a Primer sumando
 * @param b Segundo sumando
 * @return Suma
 */
int sumar(int a, int b);

int restar(int a, int b);
"""
    result = inject_placeholders(code, filename="modulo.h")

    # Modulo.h no debe duplicarse
    assert result.count("@file modulo.h") == 1
    # Punto no debe duplicarse
    assert result.count("Estructura existente") == 1
    # Sumar no debe duplicarse
    assert result.count("Suma dos números ya documentada") == 1
    # Restar debe recibir placeholder
    assert "@brief [Descripción breve de la función restar]" in result
    assert "@param a" in result
    assert "@param b" in result


def test_analyze_missing_documentation():
    code = """int func_sin_doc(int a, int b);
/** @brief Doc */
int func_con_doc(void);
struct mi_struct { int x; };
typedef void (*cb_t)(int);
"""
    missing = analyze_missing_documentation(code, filename="test.h")
    nombres = [m["name"] for m in missing]
    assert "test.h" in nombres  # Falta header
    assert "func_sin_doc" in nombres
    assert "mi_struct" in nombres
    assert "cb_t" in nombres
    assert "func_con_doc" not in nombres


def test_cli_scaffold_output_file(tmp_path):
    h = tmp_path / "calc.h"
    h.write_text("int sumar(int a, int b);\nvoid imprimir(const char *msg);\n")
    out = tmp_path / "calc_scaffolded.h"

    res = runner.invoke(app, ["scaffold", str(h), "-o", str(out)])
    assert res.exit_code == 0
    assert out.is_file()
    contenido = out.read_text(encoding="utf-8")
    assert "@file calc.h" in contenido
    assert "@brief [Descripción breve de la función sumar]" in contenido
    assert "@param a" in contenido
    assert "@param b" in contenido
    assert "@brief [Descripción breve de la función imprimir]" in contenido
    assert "@param msg" in contenido


def test_cli_scaffold_in_place_and_stdout(tmp_path):
    h = tmp_path / "calc.h"
    h.write_text("double dividir(double num, double den);\n")

    # stdout
    res_stdout = runner.invoke(app, ["scaffold", str(h)])
    assert res_stdout.exit_code == 0
    assert "@brief [Descripción breve de la función dividir]" in res_stdout.stdout

    # in-place
    res = runner.invoke(app, ["scaffold", str(h), "-i"])
    assert res.exit_code == 0
    contenido = h.read_text(encoding="utf-8")
    assert "@brief [Descripción breve de la función dividir]" in contenido
    assert "@param num" in contenido
    assert "@param den" in contenido
    assert "@return" in contenido


def test_cli_doc_with_placeholders_flag(tmp_path):
    h = tmp_path / "calc.h"
    h.write_text("int multiplicar(int a, int b);\n")
    out = tmp_path / "calc_doc.h"

    res = runner.invoke(app, ["doc", str(h), "--placeholders", "-o", str(out)])
    assert res.exit_code == 0
    assert out.is_file()
    assert "@brief [Descripción breve de la función multiplicar]" in out.read_text(encoding="utf-8")


def test_cli_check_command(tmp_path):
    h_sin_doc = tmp_path / "sin_doc.h"
    h_sin_doc.write_text("void f(int x);\n")

    res = runner.invoke(app, ["check", str(h_sin_doc)])
    assert res.exit_code == 1
    assert "sin_doc.h" in res.stdout

    # Inyectar placeholders
    runner.invoke(app, ["scaffold", str(h_sin_doc), "-i"])
    res2 = runner.invoke(app, ["check", str(h_sin_doc)])
    assert res2.exit_code == 0
    assert "100% Documentado" in res2.stdout


def test_ripley_plugin_scaffold_mode(tmp_path):
    h = tmp_path / "modulo.h"
    h.write_text("int operacion(int x);\n")

    plugin = CorbelPlugin()
    res = plugin.run({"source_dir": str(tmp_path), "scaffold": True})
    assert res["passed"] is True
    assert len(res["scaffolded_files"]) == 1
    assert "@brief [Descripción breve de la función operacion]" in h.read_text(encoding="utf-8")
