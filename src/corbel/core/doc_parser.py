"""Parser de comentarios Doxygen y declaraciones de funciones C usando Tree-Sitter AST."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Dict, List, Optional

import tree_sitter_c as tsc
from tree_sitter import Language, Parser, Node

from corbel.core.models import (
    DocumentedFunction,
    DocumentedMacro,
    FunctionParam,
    ModuleDoc,
)

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
    assigns = []
    macro_def = ""
    is_file_doc = False

    # Como en Doxygen, el texto de un tag sigue en las líneas siguientes hasta una línea en
    # blanco o el próximo tag: «@param n cota …\n * … de nodos.» es un solo parámetro.
    ultimo = ""  # qué recibe una línea de continuación: brief, desc, param, return, pre, post, assigns

    def _continuar(texto: str) -> None:
        nonlocal brief, returns
        if ultimo == "brief":
            brief = f"{brief} {texto}".strip()
        elif ultimo == "param" and params:
            params[-1].description = f"{params[-1].description} {texto}".strip()
        elif ultimo == "return":
            returns = f"{returns} {texto}".strip()
        elif ultimo in ("pre", "post", "assigns"):
            lista = {"pre": pre, "post": post, "assigns": assigns}[ultimo]
            lista[-1] = f"{lista[-1]} {texto}".strip()
        else:
            desc_lines.append(texto)

    for line in lines:
        if not line:
            ultimo = "desc" if brief else ""
            continue
        if line.startswith("@file"):
            is_file_doc = True
            ultimo = ""
        elif line.startswith("@def"):
            macro_def = line.replace("@def", "").strip()
            ultimo = ""
        elif line.startswith("@brief"):
            brief = line.replace("@brief", "").strip()
            ultimo = "brief"
        elif line.startswith("@param"):
            parts = line.replace("@param", "").strip().split(maxsplit=1)
            p_name = parts[0] if parts else "param"
            p_desc = parts[1] if len(parts) > 1 else ""
            params.append(FunctionParam(name=p_name, description=p_desc))
            ultimo = "param"
        elif line.startswith(("@return", "@returns")):
            returns = line.split(maxsplit=1)[1] if len(line.split(maxsplit=1)) > 1 else ""
            ultimo = "return"
        elif line.startswith("@pre"):
            pre.append(line.replace("@pre", "").strip())
            ultimo = "pre"
        elif line.startswith("@post"):
            post.append(line.replace("@post", "").strip())
            ultimo = "post"
        elif line.startswith("@assigns"):
            assigns.append(line.replace("@assigns", "").strip())
            ultimo = "assigns"
        elif not line.startswith("@"):
            if not brief:
                brief = line
                ultimo = "brief"
            elif ultimo:
                _continuar(line)
            else:
                desc_lines.append(line)
        else:
            ultimo = ""  # otro tag (@note, @see…): su texto no se mezcla con el anterior

    return {
        "brief": brief,
        "description": " ".join(desc_lines),
        "params": params,
        "returns": returns,
        "preconditions": pre,
        "postconditions": post,
        "assigns": assigns,
        "macro_def": macro_def,
        "is_file_doc": is_file_doc,
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
        return (node.text or b"").decode("utf-8", errors="replace")
    for child in node.children:
        if child.type in ("identifier", "type_identifier", "field_identifier"):
            return (child.text or b"").decode("utf-8", errors="replace")
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


def _extract_param_types_from_signature(sig: str) -> Dict[str, str]:
    """Extrae un mapa {nombre_param: tipo_c} desde una firma C."""
    if "(" not in sig or ")" not in sig:
        return {}
    inner = sig.split("(", 1)[1].rsplit(")", 1)[0].strip()
    if not inner or inner == "void":
        return {}
    result: Dict[str, str] = {}
    for raw_part in inner.split(","):
        part = raw_part.strip()
        if not part or part == "...":
            continue
        m = re.match(r"^(.*?)\b([A-Za-z_][A-Za-z0-9_]*)\s*(?:\[[^\]]*\])?$", part)
        if m:
            c_type = " ".join(m.group(1).split())
            name = m.group(2)
            if "[" in part:
                c_type = f"{c_type} *"
            result[name] = c_type
    return result


def parse_header_documentation(header_path: Path) -> ModuleDoc:
    """Parsea un archivo .h completo extrayendo las funciones y macros documentadas vía Tree-Sitter AST."""
    content = header_path.read_text(encoding="utf-8", errors="replace")
    source_bytes = content.encode("utf-8")
    parser = get_c_parser()
    tree = parser.parse(source_bytes)

    functions: List[DocumentedFunction] = []
    macros: List[DocumentedMacro] = []
    seen_macros: set[str] = set()
    module_brief = f"Documentación de interfaz para {header_path.name}"
    module_desc = ""

    for m_comment in re.finditer(r"/\*\*(.*?)\*/", content, re.DOTALL):
        info = parse_docblock(m_comment.group(1))
        if info["is_file_doc"] and info["brief"]:
            module_brief = info["brief"]
            module_desc = info["description"]
        if info["macro_def"]:
            m_name = info["macro_def"].split("(", 1)[0].strip()
            if m_name and m_name not in seen_macros:
                seen_macros.add(m_name)
                macros.append(
                    DocumentedMacro(
                        name=m_name,
                        signature=f"#define {info['macro_def']}",
                        brief=info["brief"] or f"Macro {m_name}",
                        description=info["description"],
                        params=info["params"],
                    )
                )

    for m_def in re.finditer(
        r"^[ \t]*#[ \t]*define[ \t]+([A-Z][A-Z0-9_]*)\(([^)]*)\)",
        content,
        re.MULTILINE,
    ):
        m_name = m_def.group(1)
        m_args = m_def.group(2).strip()
        if m_name.startswith("_") or m_name.endswith("_H") or m_name in seen_macros:
            continue
        doc_raw = _get_preceding_docblock(source_bytes, m_def.start())
        info = parse_docblock(doc_raw) if doc_raw else {
            "brief": f"Macro de interfaz {m_name}({m_args}).",
            "description": "",
            "params": [
                FunctionParam(name=a.strip(), description=f"Argumento {a.strip()}.")
                for a in m_args.split(",") if a.strip() and a.strip() != "..."
            ],
        }
        seen_macros.add(m_name)
        macros.append(
            DocumentedMacro(
                name=m_name,
                signature=f"#define {m_name}({m_args})",
                brief=info["brief"] or f"Macro {m_name}({m_args}).",
                description=info["description"],
                params=info["params"],
            )
        )

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
                        raw_node = (node.text or b"").decode("utf-8", errors="replace").split("{", 1)[0]
                        sig = " ".join(raw_node.strip().rstrip(";").split()) + ";"
                        prefix = sig.split(fn_name, 1)[0].strip()
                        prefix = re.sub(r"\b(static|inline|extern)\b", "", prefix).strip()
                        type_node = node.child_by_field_name("type")
                        fallback_ret = (type_node.text or b"").decode("utf-8", errors="replace") if type_node else "void"
                        ret_type = " ".join(prefix.split()) if prefix else fallback_ret
                        doc_data = parse_docblock(doc_raw)
                        param_types = _extract_param_types_from_signature(sig)
                        for p in doc_data["params"]:
                            if p.name in param_types:
                                p.c_type = param_types[p.name]

                        functions.append(DocumentedFunction(
                            name=fn_name,
                            return_type=ret_type,
                            signature=sig,
                            brief=doc_data["brief"],
                            description=doc_data["description"],
                            params=doc_data["params"],
                            returns=doc_data["returns"],
                            preconditions=doc_data["preconditions"],
                            postconditions=doc_data["postconditions"],
                            assigns=doc_data["assigns"],
                        ))
                return

        for child in node.children:
            _traverse(child)

    _traverse(tree.root_node)

    return ModuleDoc(
        header_name=header_path.name,
        brief=module_brief,
        description=module_desc,
        functions=functions,
        macros=macros,
    )
