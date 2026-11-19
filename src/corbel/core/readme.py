"""README de una librería del alumno (`plantilla-libreria`), generado desde el código.

La parte generada va entre dos marcas; lo que el alumno escribe fuera de ellas no se toca.
Sale de `library.json` (nombre, versión, repositorio, cabeceras exportadas), de los objetivos
del Makefile y de los docblocks de las cabeceras públicas. Una función sin docblock, o con el
esqueleto de `corbel scaffold` o `gaff fix` sin completar, aparece como pendiente: el README no
la presenta como documentada.

Es determinista: sin fechas y con las cabeceras en orden alfabético. Regenerar sin cambios en el
código no cambia nada, así que `corbel readme --check` sirve para la CI.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from corbel.core.doc_parser import parse_header_documentation
from corbel.core.models import DocumentedFunction, ModuleDoc
from corbel.core.placeholder import analyze_missing_documentation

INICIO = "<!-- corbel:readme:inicio — generado por `corbel readme`: no editar a mano -->"
FIN = "<!-- corbel:readme:fin -->"
_BLOQUE = re.compile(re.escape(INICIO.split(" — ")[0]) + r".*?" + re.escape(FIN), re.DOTALL)
# Qué hace cada objetivo del Makefile de la plantilla, en el orden en que se muestran.
_OBJETIVOS = [
    ("all", "make", "compila la librería, el ejemplo y las pruebas"),
    ("test", "make test", "corre las pruebas"),
    ("run", "make run", "corre el programa de ejemplo"),
    ("doc", "make doc", "genera la documentación en `doc/`"),
    ("clean", "make clean", "borra lo compilado"),
]


class ErrorLibreria(Exception):
    """La carpeta no es una librería que se pueda describir (falta include/ o library.json roto)."""


@dataclass
class Cabecera:
    ruta: str                                    # relativa a la raíz de la librería
    doc: ModuleDoc
    pendientes: Dict[str, str] = field(default_factory=dict)  # nombre → firma, sin documentar
    con_relleno: List[str] = field(default_factory=list)      # esqueletos sin completar


def _leer_manifiesto(raiz: Path) -> dict:
    for nombre in ("library.json",):
        ruta = raiz / nombre
        if ruta.is_file():
            try:
                datos = json.loads(ruta.read_text(encoding="utf-8"))
            except ValueError as e:
                raise ErrorLibreria(f"{nombre} no es JSON válido: {e}") from e
            if not isinstance(datos, dict):
                raise ErrorLibreria(f"{nombre} tiene que ser un objeto JSON")
            return datos
    return {}


def _cabeceras(raiz: Path, manifiesto: dict) -> List[Path]:
    exportadas = (manifiesto.get("exports") or {}).get("headers") or []
    rutas = [raiz / h["source"] for h in exportadas if isinstance(h, dict) and h.get("source")]
    if not rutas:
        rutas = list((raiz / "include").rglob("*.h"))
    rutas = sorted({r for r in rutas if r.is_file()}, key=lambda r: r.relative_to(raiz).as_posix())
    if not rutas:
        raise ErrorLibreria(f"No hay cabeceras públicas en {raiz} (se buscan en include/ y en library.json)")
    return rutas


def _objetivos_make(raiz: Path) -> List[str]:
    makefile = raiz / "Makefile"
    if not makefile.is_file():
        return []
    texto = makefile.read_text(encoding="utf-8", errors="replace")
    return re.findall(r"^([A-Za-z][\w-]*)\s*:(?!=)", texto, re.MULTILINE)


def analizar(raiz: Path) -> tuple[dict, List[Cabecera], List[str]]:
    manifiesto = _leer_manifiesto(raiz)
    cabeceras = []
    for ruta in _cabeceras(raiz, manifiesto):
        texto = ruta.read_text(encoding="utf-8", errors="replace")
        cab = Cabecera(ruta=ruta.relative_to(raiz).as_posix(), doc=parse_header_documentation(ruta))
        for m in analyze_missing_documentation(texto, ruta.name):
            if m["type"] == "placeholder sin completar":
                cab.con_relleno.append(m["name"])
            elif m["type"] == "función":
                cab.pendientes[m["name"]] = m["signature"]
        cabeceras.append(cab)
    return manifiesto, cabeceras, _objetivos_make(raiz)


def _celda(texto: str) -> str:
    return " ".join(texto.split()).replace("|", "\\|")


def _funcion(fn: DocumentedFunction) -> List[str]:
    lineas = [f"#### `{fn.name}`", "", "```c", fn.signature, "```", ""]
    if fn.brief:
        lineas += [fn.brief + (f" {fn.description}" if fn.description else ""), ""]
    if fn.params:
        lineas += ["| Parámetro | Descripción |", "| :-- | :-- |"]
        lineas += [f"| `{p.name}` | {_celda(p.description) or '—'} |" for p in fn.params]
        lineas.append("")
    if fn.returns:
        lineas += [f"**Devuelve:** {fn.returns}", ""]
    if fn.preconditions:
        lineas += ["**Precondiciones:**", ""] + [f"- {p}" for p in fn.preconditions] + [""]
    if fn.postconditions:
        lineas += ["**Postcondiciones:**", ""] + [f"- {p}" for p in fn.postconditions] + [""]
    return lineas


def generar_bloque(raiz: Path) -> str:
    """La parte generada del README, con sus marcas."""
    manifiesto, cabeceras, objetivos = analizar(raiz)
    nombre = manifiesto.get("name") or raiz.resolve().name
    lineas = [INICIO, ""]

    if manifiesto.get("version"):
        lineas += [f"**Versión:** {manifiesto['version']}", ""]

    disponibles = [(cmd, que) for obj, cmd, que in _OBJETIVOS if obj in objetivos]
    if disponibles:
        ancho = max(len(cmd) for cmd, _ in disponibles)
        lineas += ["## Uso", "", "```bash"]
        lineas += [f"{cmd.ljust(ancho)}  # {que}" for cmd, que in disponibles]
        lineas += ["```", ""]

    repo = manifiesto.get("repository")
    lineas += ["## Cómo agregarla a un TP", "", "Desde la raíz de un TP hecho con `plantilla-TP`:", "", "```bash",
               f"./tp.sh add-lib {nombre} {repo or '<url del repositorio>'}", "```", ""]

    lineas += ["## API", ""]
    for cab in cabeceras:
        doc = cab.doc
        lineas += [f"### `{cab.ruta}`", ""]
        if not doc.brief.startswith("Documentación de interfaz para"):
            lineas += [doc.brief + (f" {doc.description}" if doc.description else ""), ""]
        documentadas = [f for f in doc.functions if f.name not in cab.con_relleno]
        # Sin docblock, el parser le inventa a la macro un «Macro de interfaz X(…)»: no la documenta.
        macros = [m for m in doc.macros if not m.brief.startswith("Macro de interfaz ")]
        if documentadas or macros:
            lineas += ["| Nombre | Qué hace |", "| :-- | :-- |"]
            lineas += [f"| [`{f.name}`](#{f.name.lower()}) | {_celda(f.brief) or '—'} |" for f in documentadas]
            lineas += [f"| `{m.name}` | {_celda(m.brief) or '—'} |" for m in macros]
            lineas.append("")
        sin_doc = ([cab.pendientes[n] for n in cab.pendientes]
                   + [f.signature for f in doc.functions if f.name in cab.con_relleno]
                   + [m.signature for m in doc.macros if m not in macros])
        if sin_doc:
            lineas += ["> [!WARNING]", "> **Sin documentar** (completá el docblock y regenerá con `corbel readme`):"]
            lineas += [f"> - `{_celda(firma).rstrip(';')}`" for firma in sin_doc]
            lineas.append("")
        for fn in documentadas:
            lineas += _funcion(fn)

    lineas.append(FIN)
    return "\n".join(lineas) + "\n"


def readme_actualizado(raiz: Path, actual: Optional[str]) -> str:
    """El README completo con el bloque generado: reemplaza el que había, o lo agrega al final."""
    bloque = generar_bloque(raiz)
    if actual is None:
        manifiesto = _leer_manifiesto(raiz)
        nombre = manifiesto.get("name") or raiz.resolve().name
        return f"# {nombre}\n\n[completar: qué hace la librería y para qué sirve]\n\n{bloque}"
    if _BLOQUE.search(actual):
        return _BLOQUE.sub(lambda _: bloque.rstrip("\n"), actual, count=1)
    return actual.rstrip("\n") + "\n\n" + bloque
