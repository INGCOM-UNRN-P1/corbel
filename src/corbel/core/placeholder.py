"""Generador y analizador de placeholders de documentación Doxygen para C."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


KNOWN_TYPES = {
    "int", "char", "float", "double", "void", "short", "long", "unsigned",
    "signed", "size_t", "ssize_t", "uint8_t", "uint16_t", "uint32_t", "uint64_t",
    "int8_t", "int16_t", "int32_t", "int64_t", "bool", "FILE", "const",
    "volatile", "restrict", "struct", "enum", "union", "intptr_t", "uintptr_t",
    "ptrdiff_t", "time_t"
}

CONTROL_WORDS = {"if", "while", "for", "switch", "return", "sizeof", "typeof"}


def split_c_params(params_str: str) -> List[str]:
    """Divide parámetros C respetando paréntesis anidados (punteros a función)."""
    parts = []
    current = []
    depth = 0
    for char in params_str:
        if char == "(":
            depth += 1
            current.append(char)
        elif char == ")":
            depth -= 1
            current.append(char)
        elif char == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    if current:
        last = "".join(current).strip()
        if last:
            parts.append(last)
    return parts


def extract_param_name(param_str: str, index: int = 1) -> Optional[str]:
    """Extrae el nombre de un parámetro a partir de su declaración."""
    p = param_str.strip()
    if not p or p == "void":
        return None
    if p == "...":
        return "..."

    # Puntero a función: void (*callback)(int a, int b)
    fp = re.search(r"\(\s*\*\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\)", p)
    if fp:
        return fp.group(1)

    # Si termina con '*' sin identificador posterior (ej: const char *, void *)
    if p.rstrip().endswith("*"):
        return f"param{index}"

    # Limpiar corchetes de arreglos: int vector[] -> int vector
    p_clean = re.sub(r"\[[^\]]*\]", "", p).strip()
    words = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", p_clean)
    if not words:
        return f"param{index}"

    last_word = words[-1]
    if len(words) == 1 and (last_word in KNOWN_TYPES or last_word.endswith("_t")):
        return f"param{index}"
    if last_word in ("const", "volatile", "restrict", "unsigned", "signed", "struct", "enum", "union"):
        return f"param{index}"

    return last_word


def is_already_documented(code: str, start_index: int) -> bool:
    """Verifica si la declaración en start_index ya tiene un bloque de documentación encima."""
    preceding = code[:start_index].rstrip()
    if preceding.endswith("*/"):
        comment_start = preceding.rfind("/*")
        if comment_start != -1 and preceding[comment_start:].startswith("/**"):
            return True
    return False


def generate_function_docblock(
    ret_type: str,
    fn_name: str,
    params_str: str,
    indent: str = ""
) -> str:
    """Genera un docblock Doxygen completo con placeholders para una función."""
    params = split_c_params(params_str)
    param_names: List[Tuple[str, str]] = []
    for i, p in enumerate(params, 1):
        pname = extract_param_name(p, i)
        if pname:
            param_names.append((pname, p))

    is_void_return = ret_type.strip() == "void"

    lines = [
        f"{indent}/**",
        f"{indent} * @brief [Descripción breve de la función {fn_name}]",
    ]

    if param_names:
        lines.append(f"{indent} *")
        for pname, _ in param_names:
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
    Inyecta placeholders de documentación en todo elemento C que carezca de docblock:
    - Encabezado general de archivo (@file)
    - Declaraciones de estructuras, uniones y enumeraciones
    - Typedefs y punteros a función
    - Prototipos y definiciones de funciones
    """
    insertions: List[Tuple[int, str]] = []

    # 1. Encabezado de archivo si corresponde y no existe docblock al inicio
    if include_file_header and filename:
        top_stripped = source_code.lstrip()
        if not top_stripped.startswith("/**"):
            file_doc = (
                "/**\n"
                f" * @file {filename}\n"
                f" * @brief [Descripción general del módulo {filename}]\n"
                " */\n\n"
            )
            insertions.append((0, file_doc))

    # 2. Structs, Enums y Unions
    struct_pattern = re.compile(
        r"^([ \t]*)"
        r"((?:typedef\s+)?(?:struct|enum|union))\s+([a-zA-Z0-9_]+)?\s*\{",
        re.MULTILINE
    )
    for m in struct_pattern.finditer(source_code):
        if not is_already_documented(source_code, m.start()):
            indent = m.group(1)
            kind = m.group(2).strip()
            name = m.group(3) or ""
            doc = generate_struct_docblock(kind, name, indent)
            insertions.append((m.start(), doc))

    # 3. Typedefs de punteros a función: typedef void (*fn_t)(...);
    typedef_fp_pattern = re.compile(
        r"^([ \t]*)"
        r"typedef\s+([a-zA-Z0-9_* ]+?)\s*\(\s*\*\s*([a-zA-Z0-9_]+)\s*\)\s*\(([\s\S]*?)\)\s*;",
        re.MULTILINE
    )
    for m in typedef_fp_pattern.finditer(source_code):
        if not is_already_documented(source_code, m.start()):
            indent = m.group(1)
            name = m.group(3).strip()
            doc = generate_typedef_docblock(name, is_function_pointer=True, indent=indent)
            insertions.append((m.start(), doc))

    # 4. Typedefs simples: typedef unsigned long hash_t;
    typedef_simple_pattern = re.compile(
        r"^([ \t]*)"
        r"typedef\s+(?:const\s+|unsigned\s+|signed\s+|struct\s+|enum\s+|union\s+)*[a-zA-Z0-9_]+(?:\s*[*]+)?\s+([a-zA-Z0-9_]+)\s*;",
        re.MULTILINE
    )
    for m in typedef_simple_pattern.finditer(source_code):
        if not is_already_documented(source_code, m.start()):
            indent = m.group(1)
            name = m.group(2).strip()
            doc = generate_typedef_docblock(name, is_function_pointer=False, indent=indent)
            insertions.append((m.start(), doc))

    # 5. Funciones (prototipos o definiciones)
    fn_pattern = re.compile(
        r"^([ \t]*)"
        r"((?:(?:extern|static|inline|const|unsigned|signed|struct\s+[a-zA-Z0-9_]+|enum\s+[a-zA-Z0-9_]+|[a-zA-Z0-9_]+)\s+[*&]*)+)"
        r"([a-zA-Z_][a-zA-Z0-9_]*)"
        r"\s*\(([\s\S]*?)\)"
        r"\s*(?:;|\{)",
        re.MULTILINE
    )
    for m in fn_pattern.finditer(source_code):
        indent = m.group(1)
        ret_type = m.group(2).strip()
        fn_name = m.group(3).strip()
        params = m.group(4).strip()

        if fn_name in CONTROL_WORDS or ret_type.startswith("#") or "typedef" in ret_type:
            continue

        if not is_already_documented(source_code, m.start()):
            doc = generate_function_docblock(ret_type, fn_name, params, indent)
            insertions.append((m.start(), doc))

    # Ordenar inserciones de fin a inicio para no alterar los índices de caracteres
    insertions.sort(key=lambda x: x[0], reverse=True)

    result = source_code
    for idx, doc in insertions:
        result = result[:idx] + doc + result[idx:]

    return result


def analyze_missing_documentation(source_code: str, filename: str = "") -> List[Dict[str, Any]]:
    """Analiza y lista los elementos del código C que carecen de documentación."""
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

    # 2. Structs, Enums y Unions
    struct_pattern = re.compile(
        r"^([ \t]*)"
        r"((?:typedef\s+)?(?:struct|enum|union))\s+([a-zA-Z0-9_]+)?\s*\{",
        re.MULTILINE
    )
    for m in struct_pattern.finditer(source_code):
        if not is_already_documented(source_code, m.start()):
            line_no = source_code[:m.start()].count("\n") + 1
            kind = m.group(2).strip()
            name = m.group(3) or "anónimo"
            missing.append({
                "type": kind,
                "name": name,
                "line": line_no,
                "signature": f"{kind} {name}"
            })

    # 3. Typedefs
    typedef_fp_pattern = re.compile(
        r"^([ \t]*)"
        r"typedef\s+([a-zA-Z0-9_* ]+?)\s*\(\s*\*\s*([a-zA-Z0-9_]+)\s*\)\s*\(([\s\S]*?)\)\s*;",
        re.MULTILINE
    )
    for m in typedef_fp_pattern.finditer(source_code):
        if not is_already_documented(source_code, m.start()):
            line_no = source_code[:m.start()].count("\n") + 1
            name = m.group(3).strip()
            missing.append({
                "type": "typedef (función)",
                "name": name,
                "line": line_no,
                "signature": m.group(0).strip()
            })

    # 4. Funciones
    fn_pattern = re.compile(
        r"^([ \t]*)"
        r"((?:(?:extern|static|inline|const|unsigned|signed|struct\s+[a-zA-Z0-9_]+|enum\s+[a-zA-Z0-9_]+|[a-zA-Z0-9_]+)\s+[*&]*)+)"
        r"([a-zA-Z_][a-zA-Z0-9_]*)"
        r"\s*\(([\s\S]*?)\)"
        r"\s*(?:;|\{)",
        re.MULTILINE
    )
    for m in fn_pattern.finditer(source_code):
        ret_type = m.group(2).strip()
        fn_name = m.group(3).strip()
        params = m.group(4).strip()

        if fn_name in CONTROL_WORDS or ret_type.startswith("#") or "typedef" in ret_type:
            continue

        if not is_already_documented(source_code, m.start()):
            line_no = source_code[:m.start()].count("\n") + 1
            sig = f"{ret_type} {fn_name}({params})"
            missing.append({
                "type": "función",
                "name": fn_name,
                "line": line_no,
                "signature": sig
            })

    return missing
