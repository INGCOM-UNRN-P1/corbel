"""Exportador de cláusulas Doxygen (@pre, @post, @assigns) a contratos formales ACSL para Frama-C WP y Callahan."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from corbel.core.doc_parser import (
    _extract_param_types_from_signature,
    _find_function_declarator,
    _find_identifier,
    _get_preceding_docblock,
    get_c_parser,
    parse_header_documentation,
)
from corbel.core.models import DocumentedFunction, ModuleDoc

_EXPRESION_ACSL = re.compile(r"^[A-Za-z0-9_\s\+\-\*\/\%\=\!\<\>\&\|\(\)\[\]\.\->\\,:]+$")
_PROSA_ESP = re.compile(
    r"\b(el|la|los|las|un|una|debe|deben|devuelve|retorna|cuando|para|con|sin|del|al|es|son|tiene|tienen|fue|sea|lista|cola|pila|estructura|memoria|error|elemento|puntero|valido|nulo)\b",
    re.IGNORECASE,
)
_TIENE_OPERADOR = re.compile(
    r"(==|!=|<=|>=|<|>|&&|\|\||==>|<==>|\\valid|\\separated|\\forall|\\exists|\\initialized|\\fresh)"
)
_PREFIJO_RELACIONAL = re.compile(r"^(==|!=|<=|>=|<|>)\s*(.+)$")


def _limpiar_clausula(texto: str) -> str:
    s = texto.strip().rstrip(";").strip()
    if s.endswith(".") and not s.endswith(".."):
        s = s[:-1].strip()
    return s


def _es_predicado_formal(cand: str) -> bool:
    if not cand or not _EXPRESION_ACSL.match(cand):
        return False
    if _PROSA_ESP.search(cand):
        return False
    return bool(_TIENE_OPERADOR.search(cand)) or cand in ("\\true", "\\false", "true", "false")


def _normalizar_post(expr: str) -> str:
    s = re.sub(r"\breturn\b", r"\\result", expr.strip())
    m = _PREFIJO_RELACIONAL.match(s)
    if m:
        return f"\\result {m.group(1)} {m.group(2)}"
    return s


def _extraer_predicado(
    clausula: str,
    es_post: bool,
    param_types: Dict[str, str],
) -> Optional[str]:
    limpia = _limpiar_clausula(clausula)
    if not limpia:
        return None

    # 1. Si menciona explícitamente validez de puntero en prosa o comentario adjunto
    low = limpia.lower()
    if not es_post and any(k in low for k in ("válid", "valid", "inicializ", "cread", "apunta")):
        for p_name, c_type in param_types.items():
            if "*" in c_type and re.search(rf"\b{re.escape(p_name)}\b", limpia):
                pred = "\\valid_read" if "const" in c_type else "\\valid"
                return f"{pred}({p_name})"

    # 2. Expresión formal directa (o quitando comentario final entre paréntesis)
    sin_paren = re.sub(r"\s*\([^()]*\)\s*$", "", limpia).strip()
    for cand in (limpia, sin_paren):
        cand_norm = _normalizar_post(cand) if es_post else cand
        if _es_predicado_formal(cand_norm):
            return cand_norm

    # 2. Si contiene una expresión formal entre backticks `...`
    for m_bt in re.finditer(r"`([^`]+)`", limpia):
        bt = _limpiar_clausula(m_bt.group(1))
        bt_norm = _normalizar_post(bt) if es_post else bt
        if _es_predicado_formal(bt_norm):
            return bt_norm

    # 3. Inferencia desde patrones habituales en español sobre parámetros punteros
    low = limpia.lower()
    if not es_post:
        for p_name, c_type in param_types.items():
            if "*" in c_type and re.search(rf"\b{re.escape(p_name)}\b", limpia):
                if any(k in low for k in ("null", "válid", "valid", "inicializ", "cread", "apunta")):
                    pred = "\\valid_read" if "const" in c_type else "\\valid"
                    return f"{pred}({p_name})"
        # Si hay un único parámetro puntero y la precondición exige validez/creación del TDA
        punteros = [(n, t) for n, t in param_types.items() if "*" in t]
        if len(punteros) == 1 and any(k in low for k in ("null", "válid", "valid", "inicializ", "cread", "no vac")):
            p_name, c_type = punteros[0]
            pred = "\\valid_read" if "const" in c_type else "\\valid"
            return f"{pred}({p_name})"

    return None


def build_function_contract(fn: DocumentedFunction) -> Dict[str, Any]:
    """Construye las cláusulas formales ACSL (requires, assigns, ensures) para una función documentada."""
    param_types = _extract_param_types_from_signature(fn.signature)
    for p in fn.params:
        if p.c_type and p.name not in param_types:
            param_types[p.name] = p.c_type

    requires: List[str] = []
    ensures: List[str] = []
    notas_pre: List[str] = []
    notas_post: List[str] = []

    for pre in fn.preconditions:
        pred = _extraer_predicado(pre, es_post=False, param_types=param_types)
        if pred and pred not in requires:
            requires.append(pred)
        elif not pred:
            notas_pre.append(pre)

    for post in fn.postconditions:
        pred = _extraer_predicado(post, es_post=True, param_types=param_types)
        if pred and pred not in ensures:
            ensures.append(pred)
        elif not pred:
            notas_post.append(post)

    assigns: List[str] = [_limpiar_clausula(a) for a in fn.assigns if _limpiar_clausula(a)]

    lineas = ["/*@"]
    for req in requires:
        lineas.append(f"  requires {req};")
    for np in notas_pre:
        lineas.append(f"  // @pre {np}")
    for asg in assigns:
        lineas.append(f"  assigns {asg};")
    for ens in ensures:
        lineas.append(f"  ensures {ens};")
    for nq in notas_post:
        lineas.append(f"  // @post {nq}")
    lineas.append("*/")

    tiene_clausulas = bool(requires or ensures or assigns or notas_pre or notas_post)
    bloque = "\n".join(lineas) if tiene_clausulas else ""

    return {
        "name": fn.name,
        "signature": fn.signature,
        "return_type": fn.return_type,
        "requires": requires,
        "assigns": assigns,
        "ensures": ensures,
        "pre_notes": notas_pre,
        "post_notes": notas_post,
        "acsl_block": bloque,
    }


def render_acsl(doc: ModuleDoc, source_header: Optional[Path] = None) -> str:
    """Genera un archivo de cabecera C con contratos formales ACSL legibles por Frama-C WP."""
    if source_header is not None and source_header.is_file():
        return inject_acsl_into_header(source_header)

    bloques: List[str] = [
        f"/* Contratos formales ACSL generados por corbel para {doc.header_name} */",
        "",
    ]
    for fn in doc.functions:
        info = build_function_contract(fn)
        if info["acsl_block"]:
            bloques.append(info["acsl_block"])
        bloques.append(fn.signature)
        bloques.append("")
    return "\n".join(bloques).rstrip() + "\n"


def inject_acsl_into_header(header_path: Path) -> str:
    """Inyecta bloques /*@ ... */ en el contenido original del .h conservando tipos, structs e includes."""
    content = header_path.read_text(encoding="utf-8", errors="replace")
    source_bytes = content.encode("utf-8")
    parser = get_c_parser()
    tree = parser.parse(source_bytes)

    doc = parse_header_documentation(header_path)
    contracts_by_name = {
        fn.name: build_function_contract(fn)["acsl_block"]
        for fn in doc.functions
    }

    insertions: List[tuple[int, str]] = []

    def _visit(node) -> None:
        if node.type in ("declaration", "function_definition"):
            if node.parent and node.parent.type == "compound_statement":
                return
            fn_decl = _find_function_declarator(node)
            if fn_decl:
                fn_name = _find_identifier(fn_decl.child_by_field_name("declarator") or fn_decl)
                if fn_name and contracts_by_name.get(fn_name):
                    doc_raw = _get_preceding_docblock(source_bytes, node.start_byte)
                    preceding_text = source_bytes[:node.start_byte].decode("utf-8", errors="replace")
                    if doc_raw is not None and "/*@" not in preceding_text[-200:]:
                        line_start = preceding_text.rfind("\n") + 1
                        indent = preceding_text[line_start:]
                        indent_str = indent if indent.isspace() else ""
                        indented_block = "\n".join(
                            (indent_str + ln if ln else ln)
                            for ln in contracts_by_name[fn_name].splitlines()
                        )
                        insertions.append((node.start_byte, indented_block + "\n" + indent_str))
                return
        for child in node.children:
            _visit(child)

    _visit(tree.root_node)

    if not insertions:
        return content

    result_bytes = bytearray(source_bytes)
    for byte_offset, text_to_insert in sorted(insertions, key=lambda x: x[0], reverse=True):
        result_bytes[byte_offset:byte_offset] = text_to_insert.encode("utf-8")

    return result_bytes.decode("utf-8", errors="replace")


def export_header_contracts_dict(header_path: Path) -> Dict[str, Any]:
    """Exporta los contratos ACSL de un encabezado .h como diccionario estructurado (para --json y callahan)."""
    doc = parse_header_documentation(header_path)
    funciones = [build_function_contract(fn) for fn in doc.functions]
    return {
        "header_name": doc.header_name,
        "header_path": str(header_path),
        "total_functions": len(funciones),
        "functions_with_contracts": sum(
            1 for f in funciones if f["requires"] or f["ensures"] or f["assigns"]
        ),
        "functions": funciones,
        "acsl_header": inject_acsl_into_header(header_path),
    }
