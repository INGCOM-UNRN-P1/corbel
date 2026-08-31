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
from corbel.core.placeholder import inject_placeholders, analyze_missing_documentation

app = typer.Typer(
    name="corbel",
    help="Generador liviano de documentación de APIs, TDAs, man pages (man 3) y scaffolding de comentarios en C",
    add_completion=True
)
console = Console()


@app.command()
def doc(
    header_path: Path = typer.Argument(..., help="Archivo .h a documentar", exists=True),
    format_type: str = typer.Option("markdown", "--format", "-f", help="Formato de salida: markdown, man, json"),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o", help="Archivo de destino (por defecto imprime en consola o genera archivo según formato)"),
    placeholders: bool = typer.Option(False, "--placeholders", "--scaffold", "-p", help="Inyectar placeholders Doxygen en el código fuente en lugar de exportar documentación"),
    in_place: bool = typer.Option(False, "--in-place", "-i", help="Modificar el archivo .h directamente al usar --placeholders"),
):
    """Genera documentación a partir de comentarios estructurados o inyecta placeholders en cabeceras C."""
    if placeholders:
        scaffold(target=header_path, in_place=in_place, output_file=output_file, file_header=True)
        return

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


@app.command("scaffold")
@app.command("stub")
def scaffold(
    target: Path = typer.Argument(..., help="Archivo .h o .c a documentar", exists=True),
    in_place: bool = typer.Option(False, "--in-place", "-i", help="Modificar el archivo directamente in-place."),
    output_file: Optional[Path] = typer.Option(None, "--output", "-o", help="Archivo de destino."),
    file_header: bool = typer.Option(True, "--file-header/--no-file-header", help="Incluir encabezado general @file al inicio del archivo."),
):
    """
    Agrega placeholders estructurados de documentación (@brief, @param, @return, @pre, @post)
    a todas las funciones, estructuras, uniones, enumeraciones y tipos indocumentados.
    """
    source_code = target.read_text(encoding="utf-8", errors="replace")
    updated_code = inject_placeholders(
        source_code=source_code,
        filename=target.name,
        include_file_header=file_header
    )

    if in_place:
        target.write_text(updated_code, encoding="utf-8")
        console.print(f"[bold green]✓ Placeholders inyectados in-place en:[/bold green] {target}")
    elif output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(updated_code, encoding="utf-8")
        console.print(f"[bold green]✓ Archivo con placeholders generado en:[/bold green] {output_file}")
    else:
        print(updated_code)


def generar_seccion_markdown(target: Path, missing: list = None) -> str:
    """Genera sección de auditoría de documentación de API para Dredd."""
    lines = ["## Documentación de API y TDAs (Corbel)\n"]
    lines.append(f"- **Archivo analizado:** `{target.name}`")
    if missing is not None:
        lines.append(f"- **Elementos sin documentar:** {len(missing)}")
        if not missing:
            lines.append("\n> [!TIP]\n> **Cobertura Completa:** Todas las funciones, estructuras y tipos cuentan con comentarios de documentación estructurados.\n")
        else:
            lines.append("\n> [!WARNING]\n> **Elementos Indocumentados:** Se detectaron funciones o estructuras sin docstrings Doxygen canónicos.\n")
            lines.append("| Línea | Tipo | Nombre / Firma |")
            lines.append("| :---: | :---: | :--- |")
            for m in missing:
                lines.append(f"| {m.get('line', '-')} | {m.get('type', '-')} | `{m.get('signature', '-')}` |")
            lines.append("")
    return "\n".join(lines)


@app.command("check")
@app.command("lint")
def check(
    target: Path = typer.Argument(..., help="Archivo .h o .c a auditar", exists=True),
    output_md: Optional[Path] = typer.Option(None, "--md", "--output-md", help="Generar sección de reporte en formato Markdown para fusión en Dredd."),
):
    """Audita e informa todos los elementos C que carecen de comentarios Doxygen."""
    source_code = target.read_text(encoding="utf-8", errors="replace")
    missing = analyze_missing_documentation(source_code=source_code, filename=target.name)

    if output_md:
        md_text = generar_seccion_markdown(target, missing=missing)
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(md_text, encoding="utf-8")
        console.print(f"[bold green]✓ Sección Markdown generada en:[/bold green] {output_md}")
        raise typer.Exit(code=0 if not missing else 1)

    if not missing:
        console.print(f"[bold green]✓ 100% Documentado:[/bold green] Todos los elementos en '{target.name}' cuentan con bloques Doxygen.")
        return

    table = Table(title=f"Elementos sin Documentar en {target.name}", show_header=True, header_style="bold red")
    table.add_column("Línea", justify="right", style="dim")
    table.add_column("Tipo", style="yellow")
    table.add_column("Nombre / Firma", style="cyan")

    for item in missing:
        table.add_row(str(item["line"]), item["type"], item["signature"])

    console.print(table)
    console.print(f"\n[bold yellow]Se encontraron {len(missing)} elemento(s) sin documentar.[/bold yellow] Podés generar los placeholders con:")
    console.print(f"  [cyan]corbel scaffold {target} --in-place[/cyan]")
    raise typer.Exit(code=1)


@app.command("report")
def report(
    target: Path = typer.Argument(..., help="Archivo .h o .c a auditar", exists=True),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Ruta de destino del archivo Markdown."),
):
    """Genera directamente la sección de reporte Markdown de CORBEL para Dredd."""
    source_code = target.read_text(encoding="utf-8", errors="replace")
    missing = analyze_missing_documentation(source_code=source_code, filename=target.name)
    md_content = generar_seccion_markdown(target, missing=missing)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(md_content, encoding="utf-8")
        console.print(f"[bold green]✓ Reporte Markdown generado en:[/bold green] {output}")
    else:
        print(md_content)


@app.command()
def version():
    """Muestra la versión de CORBEL."""
    from corbel import __version__
    console.print(f"[bold cyan]CORBEL[/bold cyan] versión [green]{__version__}[/green]")


if __name__ == "__main__":
    app()
