"""CLI principal de CORBEL."""

import json
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from corbel.core.doc_parser import parse_header_documentation
from corbel.core.renderers import render_markdown, render_man_page

app = typer.Typer(
    name="corbel",
    help="Generador liviano de documentación de APIs, TDAs y man pages (man 3) en C",
    add_completion=True
)
console = Console()


@app.command()
def doc(
    header_path: Path = typer.Argument(..., help="Archivo .h a documentar", exists=True),
    format_type: str = typer.Option("markdown", "--format", "-f", help="Formato de salida: markdown, man, json"),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o", help="Archivo de destino (por defecto imprime en consola o genera archivo según formato)")
):
    """Genera documentación a partir de comentarios estructurados en cabeceras C."""
    module_doc = parse_header_documentation(header_path)

    if format_type.lower() == "json":
        data = module_doc.model_dump()
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        if output_file:
            output_file.write_text(json_str, encoding="utf-8")
        else:
            print(json_str)
        return

    elif format_type.lower() == "man":
        man_content = render_man_page(module_doc)
        if output_file:
            output_file.write_text(man_content, encoding="utf-8")
            console.print(f"[bold green]✓ Man page (man 3) generada exitosamente en:[/bold green] {output_file}")
        else:
            print(man_content)
        return

    else:
        md_content = render_markdown(module_doc)
        if output_file:
            output_file.write_text(md_content, encoding="utf-8")
            console.print(f"[bold green]✓ Documentación Markdown generada exitosamente en:[/bold green] {output_file}")
        else:
            # Render en terminal
            table = Table(title=f"Funciones Documentadas en {header_path.name}", show_header=True, header_style="bold green")
            table.add_column("Función", style="cyan")
            table.add_column("Descripción / @brief", style="white")
            table.add_column("Parámetros", style="yellow")
            table.add_column("Retorno", style="blue")

            for fn in module_doc.functions:
                params_str = ", ".join(f"{p.name}" for p in fn.params) if fn.params else "—"
                table.add_row(fn.name, fn.brief, params_str, fn.returns or "void")

            console.print(table)


@app.command()
def version():
    """Muestra la versión de CORBEL."""
    from corbel import __version__
    console.print(f"[bold cyan]CORBEL[/bold cyan] versión [green]{__version__}[/green]")


if __name__ == "__main__":
    app()
