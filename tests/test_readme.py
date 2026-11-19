"""`corbel readme`: README de la librería del alumno (plantilla-libreria) desde el código."""

import json

import pytest
from typer.testing import CliRunner

from corbel.cli import app
from corbel.core.readme import FIN, INICIO, ErrorLibreria, generar_bloque, readme_actualizado

runner = CliRunner()

CABECERA = """#ifndef LISTA_H
#define LISTA_H
/**
 * @file lista.h
 * @brief Lista enlazada de enteros.
 *
 * Uso: lista_t *l = lista_crear(); lista_agregar(l, 1);
 */

/**
 * @brief Crea una lista vacía.
 * @return La lista, o NULL si no hay memoria.
 * @post La lista tiene largo 0.
 */
lista_t *lista_crear(void);

/**
 * @brief Agrega un valor al final.
 * @param l La lista.
 * @param valor El valor | a agregar.
 * @pre l != NULL
 */
void lista_agregar(lista_t *l, int valor);

/**
 * @brief [completar: qué hace lista_largo]
 * @param l [completar: qué representa l]
 */
int lista_largo(const lista_t *l);

void lista_destruir(lista_t *l,
                    int liberar);
#endif
"""


@pytest.fixture
def libreria(tmp_path):
    (tmp_path / "include").mkdir()
    (tmp_path / "include" / "lista.h").write_text(CABECERA, encoding="utf-8")
    (tmp_path / "library.json").write_text(json.dumps({
        "name": "lista", "version": "2.0.0", "repository": "https://github.com/alumno/lista.git",
        "exports": {"headers": [{"source": "include/lista.h", "destination": "include/lista.h"}]},
    }), encoding="utf-8")
    (tmp_path / "Makefile").write_text("CC = gcc\nall: x\ntest: y\nreadme:\nclean:\n\trm -rf build\n",
                                       encoding="utf-8")
    return tmp_path


def test_el_bloque_tiene_uso_tp_y_api(libreria):
    bloque = generar_bloque(libreria)
    assert bloque.startswith(INICIO) and bloque.rstrip().endswith(FIN)
    assert "**Versión:** 2.0.0" in bloque
    assert "make test    # corre las pruebas" in bloque and "make run" not in bloque  # sólo los objetivos que hay
    assert "./tp.sh add-lib lista https://github.com/alumno/lista.git" in bloque
    assert "Lista enlazada de enteros.\n" in bloque and "Uso: lista_t" not in bloque  # del @file, sólo el brief
    assert "make readme  # actualiza este README desde el código" in bloque
    assert "| [`lista_crear`](#lista_crear) | Crea una lista vacía. |" in bloque
    assert "| `valor` | El valor \\| a agregar. |" in bloque
    assert "**Devuelve:** La lista, o NULL si no hay memoria." in bloque
    assert "**Precondiciones:**\n\n- l != NULL" in bloque and "**Postcondiciones:**\n\n- La lista tiene largo 0." in bloque


def test_lo_que_no_esta_documentado_queda_como_pendiente(libreria):
    bloque = generar_bloque(libreria)
    assert "> - `int lista_largo(const lista_t *l)`" in bloque       # esqueleto sin completar
    assert "> - `void lista_destruir(lista_t *l, int liberar)`" in bloque  # sin docblock, en dos líneas
    assert "#### `lista_largo`" not in bloque and "completar:" not in bloque


def test_solo_reemplaza_el_bloque_y_es_estable(libreria):
    propio = "# Mi lista\n\nTexto del alumno.\n\n"
    primero = readme_actualizado(libreria, propio + "viejo\n")
    assert primero.startswith(propio + "viejo\n\n" + INICIO)
    (libreria / "README.md").write_text(primero.replace("viejo\n\n", ""), encoding="utf-8")
    actual = (libreria / "README.md").read_text(encoding="utf-8")
    segundo = readme_actualizado(libreria, actual)
    assert segundo == actual and segundo.startswith(propio)


def test_sin_readme_lo_crea_con_titulo(libreria):
    nuevo = readme_actualizado(libreria, None)
    assert nuevo.startswith("# lista\n\n[completar:")


def test_sin_cabeceras_o_con_library_json_roto(tmp_path):
    with pytest.raises(ErrorLibreria, match="No hay cabeceras"):
        generar_bloque(tmp_path)
    (tmp_path / "library.json").write_text("{", encoding="utf-8")
    with pytest.raises(ErrorLibreria, match="no es JSON válido"):
        generar_bloque(tmp_path)


def test_cli_escribe_y_check(libreria):
    assert runner.invoke(app, ["readme", str(libreria), "--check"]).exit_code == 1
    res = runner.invoke(app, ["readme", str(libreria)])
    assert res.exit_code == 0 and "Creado" in res.stdout
    assert runner.invoke(app, ["readme", str(libreria), "--check"]).exit_code == 0
    (libreria / "include" / "lista.h").write_text(CABECERA.replace("Crea una lista vacía", "Crea una lista"),
                                                   encoding="utf-8")
    assert runner.invoke(app, ["readme", str(libreria), "--check"]).exit_code == 1
    assert runner.invoke(app, ["readme", str(libreria / "no-existe")]).exit_code == 2
    assert runner.invoke(app, ["readme", str(libreria), "--stdout"]).stdout.startswith("# lista")

