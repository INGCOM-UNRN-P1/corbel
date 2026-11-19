"""Texto de un tag Doxygen que sigue en las líneas siguientes."""

from corbel.core.doc_parser import parse_docblock


def test_el_texto_de_un_tag_sigue_en_las_lineas_siguientes():
    """Como en Doxygen: hasta una línea en blanco o el próximo tag (corbel doc, man y readme)."""
    info = parse_docblock("""
 * @brief Recorre la cadena y reporta
 * si hay un ciclo.
 *
 * Detalle en la descripción.
 * @param max_nodos Cota de nodos, para no colgar
 * la batería ante corrupción grave.
 * @return 0 si no hay ciclo,
 * 1 si lo hay.
 * @pre primero apunta
 * a un nodo válido.
 * @note Algo aparte.
 * Sigue la nota.
 """)
    assert info["brief"] == "Recorre la cadena y reporta si hay un ciclo."
    assert info["params"][0].description == "Cota de nodos, para no colgar la batería ante corrupción grave."
    assert info["returns"] == "0 si no hay ciclo, 1 si lo hay."
    assert info["preconditions"] == ["primero apunta a un nodo válido."]
    assert info["description"] == "Detalle en la descripción. Sigue la nota."
