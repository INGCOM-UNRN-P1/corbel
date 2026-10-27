"""Renderizadores de documentación en Markdown y man pages (roff)."""

from corbel.core.models import ModuleDoc


def render_markdown(doc: ModuleDoc) -> str:
    """Genera un archivo Markdown estructurado de la API."""
    lines = [
        f"# {doc.header_name}",
        "",
        doc.brief,
        "",
        "---",
        "",
        "## Índice de Funciones",
        ""
    ]
    for fn in doc.functions:
        lines.append(f"- [`{fn.name}`](#{fn.name.lower()}): {fn.brief}")

    lines.append("\n## Detalle de Funciones\n")

    for fn in doc.functions:
        lines.append(f"### `{fn.name}`\n")
        lines.append(f"```c\n{fn.signature}\n```\n")
        lines.append(f"**Descripción**: {fn.brief}\n")

        if fn.preconditions:
            lines.append("**Precondiciones**:")
            for pre in fn.preconditions:
                lines.append(f"- `{pre}`")
            lines.append("")

        if fn.params:
            lines.append("**Parámetros**:")
            for p in fn.params:
                lines.append(f"- `{p.name}`: {p.description}")
            lines.append("")

        if fn.returns:
            lines.append(f"**Retorno**: {fn.returns}\n")

        if fn.postconditions:
            lines.append("**Postcondiciones**:")
            for post in fn.postconditions:
                lines.append(f"- `{post}`")
            lines.append("")

        lines.append("---\n")

    return "\n".join(lines)


def _escape_troff(text: str) -> str:
    s = text.replace("\\", "\\\\").replace("-", "\\-")
    if s.startswith((".", "'")):
        s = "\\&" + s
    return s


def render_man_page(doc: ModuleDoc) -> str:
    """Genera una página de manual en formato troff/groff estándar para 'man 3'."""
    base_name = doc.header_name[:-2] if doc.header_name.endswith(".h") else doc.header_name
    mod_name = base_name.upper()
    brief_clean = _escape_troff(doc.brief or f"Interfaz C de {doc.header_name}")
    lines = [
        f'.TH "{mod_name}" 3 "{doc.header_name}" "Cátedra de C" "Manual de TDAs"',
        '.SH NAME',
        f'{base_name} \\- {brief_clean}',
        '.SH SYNOPSIS',
        '.nf',
        f'.B #include <{doc.header_name}>',
        '',
    ]

    for fn in doc.functions:
        args_part = fn.signature.split("(", 1)[1] if "(" in fn.signature else ");"
        lines.append(f'.BI "{fn.return_type} {fn.name}(" "{args_part}"')

    for macro in doc.macros:
        lines.append(f'.B {_escape_troff(macro.signature)}')

    lines.append('.fi')
    lines.append('.SH DESCRIPTION')
    lines.append(_escape_troff(doc.description or doc.brief))

    if doc.functions:
        lines.append('.SH FUNCTIONS')
        for fn in doc.functions:
            lines.append(f'.SS {fn.name}')
            lines.append(_escape_troff(fn.brief))
            if fn.description:
                lines.append(_escape_troff(fn.description))
            if fn.params:
                for p in fn.params:
                    lines.append('.TP')
                    lines.append(f'.I {p.name}')
                    lines.append(_escape_troff(p.description))
            if fn.preconditions:
                lines.append('.PP')
                lines.append('.B Precondiciones:')
                for pre in fn.preconditions:
                    lines.append(f'\\(bu {_escape_troff(pre)}')
            if fn.postconditions:
                lines.append('.PP')
                lines.append('.B Postcondiciones:')
                for post in fn.postconditions:
                    lines.append(f'\\(bu {_escape_troff(post)}')
            if fn.returns:
                lines.append('.PP')
                lines.append(f'Retorno: {_escape_troff(fn.returns)}')

    if doc.macros:
        lines.append('.SH MACROS')
        for macro in doc.macros:
            lines.append(f'.SS {_escape_troff(macro.signature)}')
            lines.append(_escape_troff(macro.brief))
            if macro.description:
                lines.append(_escape_troff(macro.description))
            if macro.params:
                for p in macro.params:
                    lines.append('.TP')
                    lines.append(f'.I {p.name}')
                    lines.append(_escape_troff(p.description))

    lines.append('.SH SEE ALSO')
    lines.append('.BR gcc (1),')
    lines.append('.BR man (7)')
    return "\n".join(lines) + "\n"
