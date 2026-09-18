"""Corbel pasa a ser el propietario real de R-A13 (CORBEL-D0902).

Ripley mantenía `core/doxygen.py` auditando completitud en paralelo al `check`
de corbel. Para que ripley pueda delegar sin perder detalle, corbel audita
ahora también los docblocks existentes — pero solo cuando se lo pide, para no
endurecer el criterio de los consumidores actuales.
"""

from corbel.core.placeholder import analyze_missing_documentation

INCOMPLETA = """/** @file caso.c */
/**
 * @brief Documentada pero incompleta.
 * @param a primer sumando
 */
int incompleta(int a, int b) { return a + b; }
"""

COMPLETA = """/** @file caso.c */
/**
 * @brief Suma dos enteros.
 * @param a primer sumando
 * @param b segundo sumando
 * @return la suma
 */
int completa(int a, int b) { return a + b; }
"""


def test_por_defecto_solo_detecta_documentacion_ausente():
    """El contrato previo no cambia: un docblock incompleto no se reporta."""
    assert analyze_missing_documentation(INCOMPLETA, "caso.c") == []


def test_con_completitud_reporta_los_tags_faltantes():
    faltantes = analyze_missing_documentation(INCOMPLETA, "caso.c", verificar_completitud=True)
    assert len(faltantes) == 1
    assert faltantes[0]["type"] == "documentación incompleta"
    assert faltantes[0]["missing_tags"] == ["@param b", "@return"]


def test_una_funcion_bien_documentada_no_se_reporta():
    assert analyze_missing_documentation(COMPLETA, "caso.c", verificar_completitud=True) == []


def test_funcion_sin_docblock_detalla_todos_los_tags():
    """Decirle al estudiante qué escribir, no solo que falta documentar."""
    codigo = "/** @file caso.c */\nint pelado(int a, int b) { return a + b; }\n"
    faltantes = analyze_missing_documentation(codigo, "caso.c", verificar_completitud=True)
    tags = faltantes[0]["missing_tags"]
    assert any("@brief" in t for t in tags)
    assert "@param a" in tags and "@param b" in tags
    assert "@return" in tags


def test_funcion_void_no_exige_return():
    codigo = "/** @file caso.c */\n/** @brief Saluda. */\nvoid saludar(void) { }\n"
    assert analyze_missing_documentation(codigo, "caso.c", verificar_completitud=True) == []
