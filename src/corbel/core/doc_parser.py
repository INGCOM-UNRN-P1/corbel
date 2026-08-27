"""Parser de comentarios Doxygen/Javadoc y declaraciones de funciones C."""

import re
from pathlib import Path
from typing import List, Optional
from corbel.core.models import ModuleDoc, DocumentedFunction, FunctionParam

DOC_BLOCK_PATTERN = re.compile(r'/\*\*(.*?)\*/\s*([a-zA-Z0-9_* ]+?)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)\s*;', re.DOTALL)


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


def parse_header_documentation(header_path: Path) -> ModuleDoc:
    """Parsea un archivo .h completo extrayendo las funciones documentadas."""
    content = header_path.read_text(encoding="utf-8", errors="replace")
    functions: List[DocumentedFunction] = []

    for match in DOC_BLOCK_PATTERN.finditer(content):
        doc_raw = match.group(1)
        ret_type = match.group(2).strip()
        fn_name = match.group(3).strip()
        params_raw = match.group(4).strip()

        doc_data = parse_docblock(doc_raw)
        sig = f"{ret_type} {fn_name}({params_raw});"

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

    return ModuleDoc(
        header_name=header_path.name,
        brief=f"Documentación de interfaz para {header_path.name}",
        functions=functions
    )
