"""Parser de comentarios Doxygen y declaraciones de funciones C usando Tree-Sitter AST."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import tree_sitter_c as tsc
from tree_sitter import Language, Parser, Node

from corbel.core.models import ModuleDoc, DocumentedFunction, FunctionParam

_C_LANGUAGE: Optional[Language] = None
_PARSER: Optional[Parser] = None


def get_c_parser() -> Parser:
    global _C_LANGUAGE, _PARSER
    if _PARSER is None:
        _C_LANGUAGE = Language(tsc.language())
        _PARSER = Parser(_C_LANGUAGE)
    return _PARSER


def parse_docblock(raw_comment: str) -> dict:
    """Extrae tags @brief, @param, @return, @pre, @post de un comentario de documentación."""
    lines = [line.strip().lstrip("*").strip() for line in raw_comment.strip().splitlines()]
    brief = ""
    desc_lines = []
    params = []
    returns = ""
    pre = []
    post = []

    for line in lines:
        if not line:
            continue
        if line.startswith("@brief"):
            brief = line.replace("@brief", "").strip()
        elif line.startswith("@param"):
            parts = line.replace("@param", "").strip().split(maxsplit=1)
            p_name = parts[0] if parts else "param"
            p_desc = parts[1] if len(parts) > 1 else ""
            params.append(FunctionParam(name=p_name, description=p_desc))
        elif line.startswith(("@return", "@returns")):
            returns = line.split(maxsplit=1)[1] if len(line.split(maxsplit=1)) > 1 else ""
        elif line.startswith("@pre"):
            pre.append(line.replace("@pre", "").strip())
        elif line.startswith("@post"):
            post.append(line.replace("@post", "").strip())
        else:
            if not brief:
                brief = line
            else:
                desc_lines.append(line)

    return {
        "brief": brief,
        "description": " ".join(desc_lines),
        "params": params,
        "returns": returns,
        "preconditions": pre,
        "postconditions": post,
    }


def _find_function_declarator(node: Node) -> Optional[Node]:
    """Busca recursivamente el declarador de función en el AST."""
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


def _get_preceding_docblock(source_bytes: bytes, start_byte: int) -> Optional[str]:
    """Obtiene el contenido de /** ... */ inmediatamente anterior a start_byte."""
    preceding = source_bytes[:start_byte].decode("utf-8", errors="replace").rstrip()
    if preceding.endswith("*/"):
        comment_start = preceding.rfind("/*")
        if comment_start != -1 and preceding[comment_start:].startswith("/**"):
            raw = preceding[comment_start + 3:-2]
            return raw
    return None


def parse_header_documentation(header_path: Path) -> ModuleDoc:
    """Parsea un archivo .h completo extrayendo las funciones documentadas vía Tree-Sitter AST."""
    content = header_path.read_text(encoding="utf-8", errors="replace")
    source_bytes = content.encode("utf-8")
    parser = get_c_parser()
    tree = parser.parse(source_bytes)

    functions: List[DocumentedFunction] = []

    def _traverse(node: Node) -> None:
        if node.type in ("declaration", "function_definition"):
            if node.parent and node.parent.type == "compound_statement":
                return
            fn_decl = _find_function_declarator(node)
            if fn_decl:
                fn_name = _find_identifier(fn_decl.child_by_field_name("declarator") or fn_decl)
                if fn_name:
                    doc_raw = _get_preceding_docblock(source_bytes, node.start_byte)
                    if doc_raw is not None:
                        type_node = node.child_by_field_name("type")
                        ret_type = type_node.text.decode("utf-8", errors="replace") if type_node else "void"
                        sig = node.text.decode("utf-8", errors="replace").strip().rstrip(";").strip() + ";"
                        doc_data = parse_docblock(doc_raw)

                        functions.append(DocumentedFunction(
                            name=fn_name,
                            return_type=ret_type,
                            signature=sig,
                            brief=doc_data["brief"],
                            description=doc_data["description"],
                            params=doc_data["params"],
                            returns=doc_data["returns"],
                            preconditions=doc_data["preconditions"],
                            postconditions=doc_data["postconditions"]
                        ))
                return

        for child in node.children:
            _traverse(child)

    _traverse(tree.root_node)

    return ModuleDoc(
        header_name=header_path.name,
        brief=f"Documentación de interfaz para {header_path.name}",
        functions=functions
    )
