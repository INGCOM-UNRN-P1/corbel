"""Regresión de CORBEL-D0301: un comentario común entre el docblock y la función.

`rfind("/*")` encontraba el comentario común, `startswith("/**")` fallaba y se
inyectaba un segundo docblock encima del ya existente.
"""

import pytest

from corbel.core.placeholder import analyze_missing_documentation, inject_placeholders

def _sin_documentar(fuente):
    """Nombres de funciones sin documentar (se ignora el aviso de encabezado de archivo)."""
    return [f["name"] for f in analyze_missing_documentation(fuente, "m.h") if f["name"] != "m.h"]


DOC = "/**\n * @brief Suma.\n * @param a x\n * @param b y\n * @return z\n */\n"


@pytest.mark.parametrize(
    "intermedio",
    [
        "/* nota de implementación */\n",
        "/* una */\n/* dos */\n",
        "// nota de línea\n",
        "/* bloque */\n// linea\n",
    ],
)
def test_un_comentario_comun_no_oculta_el_docblock(intermedio):
    fuente = DOC + intermedio + "int suma(int a, int b);\n"
    assert _sin_documentar(fuente) == []


@pytest.mark.parametrize("intermedio", ["/* nota */\n", "// nota\n"])
def test_inyectar_no_duplica_el_docblock(intermedio):
    fuente = "/**\n * @file m.h\n */\n" + DOC + intermedio + "int suma(int a, int b);\n"
    salida = inject_placeholders(fuente, "m.h")
    assert salida.count("@brief Suma.") == 1
    assert salida.count("/**") == fuente.count("/**")


def test_un_comentario_comun_sin_docblock_sigue_sin_estar_documentado():
    fuente = "/* solo una nota */\nint suma(int a, int b);\n"
    assert _sin_documentar(fuente) == ["suma"]


def test_el_codigo_previo_no_se_confunde_con_un_comentario():
    fuente = "int x; // trailing\nint suma(int a, int b);\n"
    assert _sin_documentar(fuente) == ["suma"]


def test_check_e_inject_coinciden_con_un_docblock_de_archivo_previo():
    """Un `@file` no documenta la función que le sigue ni para check ni para inject."""
    fuente = "/** @file m.h */\nint suma(int a, int b);\n"
    assert _sin_documentar(fuente) == ["suma"]
    assert "@brief" in inject_placeholders(fuente, "m.h")
