"""Generador y analizador de placeholders de documentación Doxygen para C usando Tree-Sitter AST."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from corbel.core.doc_parser import parse_docblock

import tree_sitter_c as tsc
from tree_sitter import Language, Parser, Node, Tree

_C_LANGUAGE: Optional[Language] = None
_PARSER: Optional[Parser] = None


def get_c_parser() -> Parser:
    """Inicializa y retorna la instancia única del parser C de Tree-Sitter."""
    global _C_LANGUAGE, _PARSER
    if _PARSER is None:
        _C_LANGUAGE = Language(tsc.language())
        _PARSER = Parser(_C_LANGUAGE)
    return _PARSER


def _find_function_declarator(node: Node) -> Optional[Node]:
    """Busca recursivamente el nodo function_declarator desempaquetando punteros o paréntesis."""
    if node.type == "function_declarator":
        return node
    for child in node.children:
        if child.type in ("function_declarator", "pointer_declarator", "parenthesized_declarator", "attributed_declarator"):
            res = _find_function_declarator(child)
            if res is not None:
                return res
    return None


def _find_identifier(node: Node) -> Optional[str]:
    """Encuentra el identificador principal dentro de un declarador AST."""
    if node.type in ("identifier", "type_identifier", "field_identifier"):
        return node.text.decode("utf-8", errors="replace")
    for child in node.children:
        if child.type in ("identifier", "type_identifier", "field_identifier"):
            return child.text.decode("utf-8", errors="replace")
        elif child.type in ("pointer_declarator", "function_declarator", "array_declarator", "parenthesized_declarator"):
            res = _find_identifier(child)
            if res:
                return res
    return None


def _extract_param_name_from_node(param_node: Node, index: int = 1) -> Optional[str]:
    """Extrae el nombre del parámetro a partir del nodo AST parameter_declaration."""
    raw_text = param_node.text.decode("utf-8", errors="replace").strip()
    if not raw_text or raw_text == "void":
        return None
    if raw_text == "...":
        return "..."

    decl_node = param_node.child_by_field_name("declarator")
    if decl_node:
        ident = _find_identifier(decl_node)
        if ident:
            return ident

    return f"param{index}"


def _obtener_docblock_previo(source_bytes: bytes, start_byte: int) -> Optional[str]:
    """Devuelve el docblock `/** ... */` inmediatamente anterior, si existe."""
    preceding = source_bytes[:start_byte].decode("utf-8", errors="replace").rstrip()
    if not preceding.endswith("*/"):
        return None
    comment_start = preceding.rfind("/*")
    if comment_start == -1 or not preceding[comment_start:].startswith("/**"):
        return None
    docblock = preceding[comment_start:]
    # Un docblock `@file` documenta el archivo, no la función que le sigue:
    # atribuírselo la daría por documentada.
    if "@file" in docblock:
        return None
    return docblock


def _describir_funcion(node: Node, fn_decl: Node) -> Tuple[List[str], str]:
    """Extrae los nombres de parámetros y el tipo de retorno de una función."""
    nombres: List[str] = []
    lista = fn_decl.child_by_field_name("parameters")
    if lista is not None:
        indice = 1
        for hijo in lista.children:
            if hijo.type != "parameter_declaration":
                continue
            nombre = _extract_param_name_from_node(hijo, indice)
            if nombre and nombre != "...":
                nombres.append(nombre)
                indice += 1

    tipo_node = node.child_by_field_name("type")
    tipo_retorno = tipo_node.text.decode("utf-8", errors="replace").strip() if tipo_node else ""
    # Un `void *` sí devuelve algo; solo `void` a secas no.
    declarador = node.child_by_field_name("declarator")
    if declarador is not None and declarador.text.decode("utf-8", errors="replace").strip().startswith("*"):
        tipo_retorno += " *"
    return nombres, tipo_retorno


def analizar_docblock_incompleto(
    docblock: str,
    parametros: List[str],
    tipo_retorno: str,
    require_brief: bool = True,
    require_params: bool = True,
    require_return: bool = True,
) -> List[str]:
    """Lista los tags Doxygen que le faltan a un docblock existente.

    Corbel detectaba únicamente la *ausencia* de documentación. La
    completitud la auditaba en paralelo `ripley/core/doxygen.py`, duplicando
    la responsabilidad R-A13; al traerla acá, corbel pasa a ser el propietario
    real y ripley puede delegar sin perder el detalle por tag.
    """
    datos = parse_docblock(docblock)
    faltantes: List[str] = []

    if require_brief and not datos["brief"]:
        faltantes.append("@brief (descripción de la función)")

    if require_params:
        documentados = {p.name for p in datos["params"]}
        for nombre in parametros:
            if nombre not in documentados:
                faltantes.append(f"@param {nombre}")

    if require_return and tipo_retorno.strip() not in ("void", "") and not datos["returns"]:
        faltantes.append("@return")

    return faltantes


def is_already_documented(source_bytes: bytes, start_byte: int) -> bool:
    """Verifica si antes de start_byte existe un comentario docblock /** ... */."""
    preceding = source_bytes[:start_byte].decode("utf-8", errors="replace").rstrip()
    if preceding.endswith("*/"):
        comment_start = preceding.rfind("/*")
        if comment_start != -1 and preceding[comment_start:].startswith("/**"):
            return True
    return False


def generate_function_docblock(
    ret_type: str,
    fn_name: str,
    param_names: List[str],
    indent: str = ""
) -> str:
    """Genera un docblock Doxygen completo con placeholders para una función."""
    is_void_return = ret_type.strip() == "void"

    lines = [
        f"{indent}/**",
        f"{indent} * @brief [Descripción breve de la función {fn_name}]",
    ]

    if param_names:
        lines.append(f"{indent} *")
        for pname in param_names:
            lines.append(f"{indent} * @param {pname} [Descripción del parámetro {pname}]")

    if not is_void_return:
        if not param_names:
            lines.append(f"{indent} *")
        lines.append(f"{indent} * @return [Descripción del valor de retorno]")

    lines.append(f"{indent} * @pre [Precondiciones / requisitos previos]")
    lines.append(f"{indent} * @post [Postcondiciones / estado resultante]")
    lines.append(f"{indent} */\n")

    return "\n".join(lines)


def generate_struct_docblock(kind: str, name: str, indent: str = "") -> str:
    """Genera un docblock para struct, enum o union."""
    name_str = f" {name}" if name else ""
    return (
        f"{indent}/**\n"
        f"{indent} * @brief [Descripción de {kind}{name_str}]\n"
        f"{indent} */\n"
    )


def generate_typedef_docblock(name: str, is_function_pointer: bool = False, indent: str = "") -> str:
    """Genera un docblock para un typedef."""
    tipo_desc = "puntero a función" if is_function_pointer else "tipo"
    return (
        f"{indent}/**\n"
        f"{indent} * @brief [Descripción del {tipo_desc} {name}]\n"
        f"{indent} */\n"
    )


def inject_placeholders(
    source_code: str,
    filename: str = "",
    include_file_header: bool = True
) -> str:
    """
    Inyecta placeholders de documentación analizando el código C mediante Tree-Sitter AST.
    """
    parser = get_c_parser()
    source_bytes = source_code.encode("utf-8")
    tree = parser.parse(source_bytes)

    insertions: List[Tuple[int, str]] = []

    # 1. Encabezado de archivo si corresponde. No entra en `insertions`: si la
    # primera declaración empieza en el byte 0, competiría por ese offset con
    # el docblock de la función y terminaba insertándose DESPUÉS, dejando el
    # comentario de la función huérfano arriba del encabezado.
    file_doc = ""
    if include_file_header and filename:
        top_stripped = source_code.lstrip()
        if not top_stripped.startswith("/**"):
            file_doc = (
                "/**\n"
                f" * @file {filename}\n"
                f" * @brief [Descripción general del módulo {filename}]\n"
                " */\n\n"
            )

    def _get_line_indent(start_byte: int) -> str:
        line_start = source_bytes.rfind(b"\n", 0, start_byte)
        if line_start == -1:
            line_bytes = source_bytes[:start_byte]
        else:
            line_bytes = source_bytes[line_start + 1:start_byte]
        indent_chars = []
        for b in line_bytes:
            if b in (ord(" "), ord("\t")):
                indent_chars.append(chr(b))
            else:
                break
        return "".join(indent_chars)

    def _traverse(node: Node) -> None:
        if node.type in ("declaration", "function_definition"):
            # Verificar si no está adentro de una función
            if node.parent and node.parent.type == "compound_statement":
                return

            fn_decl = _find_function_declarator(node)
            if fn_decl:
                fn_name = _find_identifier(fn_decl.child_by_field_name("declarator") or fn_decl)
                if fn_name:
                    type_node = node.child_by_field_name("type")
                    ret_type = type_node.text.decode("utf-8", errors="replace") if type_node else "void"
                    params_node = fn_decl.child_by_field_name("parameters")
                    param_names = []
                    if params_node:
                        p_idx = 1
                        for p in params_node.children:
                            if p.type == "parameter_declaration":
                                pname = _extract_param_name_from_node(p, p_idx)
                                if pname:
                                    param_names.append(pname)
                                    p_idx += 1

                    if not is_already_documented(source_bytes, node.start_byte):
                        indent = _get_line_indent(node.start_byte)
                        doc = generate_function_docblock(ret_type, fn_name, param_names, indent)
                        insertions.append((node.start_byte, doc))
                return

        if node.type == "type_definition":
            # Puede ser typedef struct, enum, union o typedef función/alias
            type_node = node.child_by_field_name("type")
            type_kind = type_node.type if type_node else "type"
            decl_node = node.child_by_field_name("declarator")
            ident = _find_identifier(decl_node) if decl_node else None

            if not is_already_documented(source_bytes, node.start_byte):
                indent = _get_line_indent(node.start_byte)
                if type_kind in ("struct_specifier", "enum_specifier", "union_specifier"):
                    kind_name = type_kind.replace("_specifier", "")
                    name = ident or ""
                    doc = generate_struct_docblock(f"typedef {kind_name}", name, indent)
                elif decl_node and _find_function_declarator(decl_node):
                    doc = generate_typedef_docblock(ident or "callback", is_function_pointer=True, indent=indent)
                else:
                    doc = generate_typedef_docblock(ident or "tipo", is_function_pointer=False, indent=indent)
                insertions.append((node.start_byte, doc))
            return

        if node.type in ("struct_specifier", "enum_specifier", "union_specifier"):
            # Si no es parte de un type_definition (ya manejado arriba) ni dentro de otro nodo
            if node.parent and node.parent.type not in ("type_definition", "declaration", "field_declaration"):
                kind_name = node.type.replace("_specifier", "")
                name_node = node.child_by_field_name("name")
                name = name_node.text.decode("utf-8", errors="replace") if name_node else ""
                if not is_already_documented(source_bytes, node.start_byte):
                    indent = _get_line_indent(node.start_byte)
                    doc = generate_struct_docblock(kind_name, name, indent)
                    insertions.append((node.start_byte, doc))
            elif node.parent and node.parent.type == "declaration" and node.parent.parent and node.parent.parent.type == "translation_unit":
                # struct foo { int x; }; sin typedef
                if not _find_function_declarator(node.parent):
                    kind_name = node.type.replace("_specifier", "")
                    name_node = node.child_by_field_name("name")
                    name = name_node.text.decode("utf-8", errors="replace") if name_node else ""
                    if not is_already_documented(source_bytes, node.parent.start_byte):
                        indent = _get_line_indent(node.parent.start_byte)
                        doc = generate_struct_docblock(kind_name, name, indent)
                        insertions.append((node.parent.start_byte, doc))
                return

        for child in node.children:
            _traverse(child)

    _traverse(tree.root_node)

    # Ordenar inserciones de fin a inicio para no desfasar bytes
    insertions.sort(key=lambda x: x[0], reverse=True)

    result_bytes = bytearray(source_bytes)
    for byte_offset, doc_text in insertions:
        doc_bytes = doc_text.encode("utf-8")
        result_bytes[byte_offset:byte_offset] = doc_bytes

    if file_doc:
        result_bytes[0:0] = file_doc.encode("utf-8")

    return result_bytes.decode("utf-8", errors="replace")


def analyze_missing_documentation(
    source_code: str,
    filename: str = "",
    verificar_completitud: bool = False,
) -> List[Dict[str, Any]]:
    """Analiza y reporta elementos indocumentados en C usando Tree-Sitter AST.

    Con `verificar_completitud` además audita los docblocks que sí existen y
    reporta los tags que les faltan. Queda opt-in para no endurecer el criterio
    de los consumidores actuales, que solo esperan detectar documentación
    ausente; ripley lo activa al delegar (CORBEL-D0902).
    """
    parser = get_c_parser()
    source_bytes = source_code.encode("utf-8")
    tree = parser.parse(source_bytes)

    missing: List[Dict[str, Any]] = []

    # 1. Header de archivo
    top_stripped = source_code.lstrip()
    if filename and not top_stripped.startswith("/**"):
        missing.append({
            "type": "file_header",
            "name": filename,
            "line": 1,
            "signature": f"@file {filename}"
        })

    def _traverse(node: Node) -> None:
        if node.type in ("declaration", "function_definition"):
            if node.parent and node.parent.type == "compound_statement":
                return
            fn_decl = _find_function_declarator(node)
            if fn_decl:
                fn_name = _find_identifier(fn_decl.child_by_field_name("declarator") or fn_decl)
                if fn_name:
                    line_no = node.start_point.row + 1
                    sig = node.text.decode("utf-8", errors="replace").strip().split("{")[0].strip()
                    docblock = _obtener_docblock_previo(source_bytes, node.start_byte)
                    if docblock is None:
                        entrada = {
                            "type": "función",
                            "name": fn_name,
                            "line": line_no,
                            "signature": sig
                        }
                        if verificar_completitud:
                            # Una función sin docblock tiene TODOS los tags
                            # faltantes: detallarlos le dice al estudiante qué
                            # escribir, en vez de solo que falta documentar.
                            parametros, tipo_retorno = _describir_funcion(node, fn_decl)
                            entrada["missing_tags"] = analizar_docblock_incompleto(
                                "", parametros, tipo_retorno
                            )
                        missing.append(entrada)
                    elif verificar_completitud:
                        parametros, tipo_retorno = _describir_funcion(node, fn_decl)
                        faltantes = analizar_docblock_incompleto(docblock, parametros, tipo_retorno)
                        if faltantes:
                            missing.append({
                                "type": "documentación incompleta",
                                "name": fn_name,
                                "line": line_no,
                                "signature": sig,
                                "missing_tags": faltantes,
                            })
                return

        if node.type == "type_definition":
            decl_node = node.child_by_field_name("declarator")
            ident = _find_identifier(decl_node) if decl_node else "anónimo"
            if not is_already_documented(source_bytes, node.start_byte):
                line_no = node.start_point.row + 1
                type_node = node.child_by_field_name("type")
                type_kind = type_node.type if type_node else "type"
                if type_kind in ("struct_specifier", "enum_specifier", "union_specifier"):
                    kind_name = type_kind.replace("_specifier", "")
                    sig = f"typedef {kind_name} {ident}"
                elif decl_node and _find_function_declarator(decl_node):
                    sig = f"typedef function {ident}"
                else:
                    sig = f"typedef {ident}"

                missing.append({
                    "type": "typedef",
                    "name": ident,
                    "line": line_no,
                    "signature": sig
                })
            return

        if node.type in ("struct_specifier", "enum_specifier", "union_specifier"):
            if node.parent and node.parent.type not in ("type_definition", "declaration", "field_declaration"):
                name_node = node.child_by_field_name("name")
                name = name_node.text.decode("utf-8", errors="replace") if name_node else "anónimo"
                if not is_already_documented(source_bytes, node.start_byte):
                    line_no = node.start_point.row + 1
                    kind_name = node.type.replace("_specifier", "")
                    missing.append({
                        "type": kind_name,
                        "name": name,
                        "line": line_no,
                        "signature": f"{kind_name} {name}"
                    })
            elif node.parent and node.parent.type == "declaration" and node.parent.parent and node.parent.parent.type == "translation_unit":
                if not _find_function_declarator(node.parent):
                    name_node = node.child_by_field_name("name")
                    name = name_node.text.decode("utf-8", errors="replace") if name_node else "anónimo"
                    if not is_already_documented(source_bytes, node.parent.start_byte):
                        line_no = node.parent.start_point.row + 1
                        kind_name = node.type.replace("_specifier", "")
                        missing.append({
                            "type": kind_name,
                            "name": name,
                            "line": line_no,
                            "signature": f"{kind_name} {name}"
                        })
                return

        for child in node.children:
            _traverse(child)

    _traverse(tree.root_node)
    return missing
