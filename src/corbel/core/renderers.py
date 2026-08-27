"""Renderizadores de documentación en Markdown, HTML y man pages (roff)."""

import html
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


def render_man_page(doc: ModuleDoc) -> str:
    """Genera una página de manual en formato troff/groff para 'man 3'."""
    mod_name = doc.header_name.replace(".h", "").upper()
    lines = [
        f'.TH "{mod_name}" 3 "{doc.header_name}" "Cátedra de C" "Manual de TDAs"',
        f'.SH NAME',
        f'{doc.header_name} \\- {doc.brief}',
        f'.SH SYNOPSIS',
        f'.B #include <{doc.header_name}>',
        ''
    ]

    for fn in doc.functions:
        lines.append(f'.BI "{fn.return_type} {fn.name}(" "{fn.signature.split("(", 1)[1] if "(" in fn.signature else ")"}"')

    lines.append('.SH DESCRIPTION')
    for fn in doc.functions:
        lines.append(f'.SS {fn.name}')
        lines.append(fn.brief)
        if fn.params:
            lines.append('.TP')
            for p in fn.params:
                lines.append(f'.I {p.name}')
                lines.append(f'{p.description}')

        if fn.returns:
            lines.append(f'Retorno: {fn.returns}')

    return "\n".join(lines)
