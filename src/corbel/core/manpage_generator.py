"""Generador e instalador de páginas de manual UNIX (man 3) para cabeceras y librerías de la cátedra."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

from corbel.core.doc_parser import parse_header_documentation
from corbel.core.models import (
    DocumentedFunction,
    DocumentedMacro,
    FunctionParam,
    ModuleDoc,
)
from corbel.core.renderers import render_man_page

# Catálogo embebido de respaldo para librerías de la cátedra cuando se invoca fuera del árbol de fuentes
_TREADSTONE_FALLBACK = ModuleDoc(
    header_name="treadstone.h",
    brief="Framework de pruebas unitarias, contratos de TDAs y utilidades seguras en C99 de la cátedra (Treadstone).",
    description=(
        "La librería treadstone provee los encabezados de cátedra p1_test.h, p1_stdio.h, "
        "p1_arrays.h, p1_files.h y tda/contracts.h para pruebas unitarias livianas sin memoria "
        "dinámica, ingreso seguro por consola y contratos de Tipos de Datos Abstractos."
    ),
    functions=[
        DocumentedFunction(
            name="p1_read_int",
            return_type="int",
            signature="int p1_read_int(const char *prompt);",
            brief="Lee un número entero de forma segura desde la entrada estándar mostrando un mensaje.",
            params=[FunctionParam(name="prompt", description="Mensaje a mostrar antes de leer.")],
            returns="Valor entero leído.",
        ),
        DocumentedFunction(
            name="p1_read_double",
            return_type="double",
            signature="double p1_read_double(const char *prompt);",
            brief="Lee un número de punto flotante de doble precisión desde stdin.",
            params=[FunctionParam(name="prompt", description="Mensaje a mostrar antes de leer.")],
            returns="Valor double leído.",
        ),
        DocumentedFunction(
            name="p1_read_line",
            return_type="bool",
            signature="bool p1_read_line(const char *prompt, char *buffer, size_t tamano);",
            brief="Lee una línea de texto de stdin eliminando el salto de línea final.",
            params=[
                FunctionParam(name="prompt", description="Mensaje descriptivo."),
                FunctionParam(name="buffer", description="Arreglo destino donde almacenar la cadena."),
                FunctionParam(name="tamano", description="Capacidad máxima del arreglo en bytes."),
            ],
            returns="true si la lectura fue exitosa, false en EOF o error.",
            preconditions=["buffer != NULL", "tamano > 0"],
        ),
        DocumentedFunction(
            name="p1_array_print_int",
            return_type="void",
            signature="void p1_array_print_int(const int *arreglo, size_t n);",
            brief="Imprime en salida estándar los elementos de un arreglo de enteros.",
            params=[
                FunctionParam(name="arreglo", description="Puntero al arreglo de enteros."),
                FunctionParam(name="n", description="Cantidad de elementos."),
            ],
        ),
    ],
    macros=[
        DocumentedMacro(
            name="TEST",
            signature="#define TEST(nombre)",
            brief="Declara una función de prueba unitaria estática.",
            params=[FunctionParam(name="nombre", description="Identificador de la prueba.")],
        ),
        DocumentedMacro(
            name="RUN_TEST",
            signature="#define RUN_TEST(nombre)",
            brief="Ejecuta una función de prueba unitaria y registra su resultado.",
            params=[FunctionParam(name="nombre", description="Identificador de la prueba a ejecutar.")],
        ),
        DocumentedMacro(
            name="ASSERT_TRUE",
            signature="#define ASSERT_TRUE(condicion)",
            brief="Verifica que la condición booleana sea verdadera.",
            params=[FunctionParam(name="condicion", description="Expresión booleana a evaluar.")],
        ),
        DocumentedMacro(
            name="ASSERT_FALSE",
            signature="#define ASSERT_FALSE(condicion)",
            brief="Verifica que la condición booleana sea falsa.",
            params=[FunctionParam(name="condicion", description="Expresión booleana a evaluar.")],
        ),
        DocumentedMacro(
            name="ASSERT_EQ",
            signature="#define ASSERT_EQ(esperado, actual)",
            brief="Verifica igualdad entre dos valores enteros.",
            params=[
                FunctionParam(name="esperado", description="Valor entero esperado."),
                FunctionParam(name="actual", description="Valor entero obtenido."),
            ],
        ),
        DocumentedMacro(
            name="ASSERT_STR_EQ",
            signature="#define ASSERT_STR_EQ(esperado, actual)",
            brief="Verifica igualdad lexicográfica entre dos cadenas C terminadas en '\\0'.",
            params=[
                FunctionParam(name="esperado", description="Cadena esperada."),
                FunctionParam(name="actual", description="Cadena obtenida."),
            ],
        ),
        DocumentedMacro(
            name="TDA_REQUIRE",
            signature="#define TDA_REQUIRE(condicion)",
            brief="Verifica una precondición de contrato en una primitiva de TDA.",
            params=[FunctionParam(name="condicion", description="Predicado de precondición.")],
        ),
        DocumentedMacro(
            name="TDA_ENSURE",
            signature="#define TDA_ENSURE(condicion)",
            brief="Verifica una postcondición de contrato en una primitiva de TDA.",
            params=[FunctionParam(name="condicion", description="Predicado de postcondición.")],
        ),
    ],
)


def _buscar_directorio_treadstone() -> Optional[Path]:
    cwd = Path.cwd().resolve()
    este_archivo = Path(__file__).resolve()
    bases = [cwd, *cwd.parents[:3], *este_archivo.parents[:5]]
    for base in bases:
        cand = base / "librerias" / "treadstone" / "include"
        if cand.is_dir():
            return cand
        cand2 = base / "treadstone" / "include"
        if cand2.is_dir():
            return cand2
    return None


def _combinar_headers_en_modulo(
    headers: List[Path],
    header_name: str,
    brief_default: str,
) -> ModuleDoc:
    funciones: List[DocumentedFunction] = []
    macros: List[DocumentedMacro] = []
    seen_fn: set[str] = set()
    seen_mc: set[str] = set()
    descripciones: List[str] = []

    for h in headers:
        if not h.is_file():
            continue
        sub = parse_header_documentation(h)
        if sub.brief and not sub.brief.startswith("Documentación de interfaz para"):
            descripciones.append(f"{h.name}: {sub.brief}")
        for fn in sub.functions:
            if fn.name not in seen_fn:
                seen_fn.add(fn.name)
                funciones.append(fn)
        for mc in sub.macros:
            if mc.name not in seen_mc:
                seen_mc.add(mc.name)
                macros.append(mc)

    for fn_fb in _TREADSTONE_FALLBACK.functions:
        if fn_fb.name not in seen_fn and header_name.startswith("treadstone"):
            seen_fn.add(fn_fb.name)
            funciones.append(fn_fb)
    for mc_fb in _TREADSTONE_FALLBACK.macros:
        if mc_fb.name not in seen_mc and header_name.startswith("treadstone"):
            seen_mc.add(mc_fb.name)
            macros.append(mc_fb)

    return ModuleDoc(
        header_name=header_name,
        brief=brief_default,
        description=" ".join(descripciones) if descripciones else _TREADSTONE_FALLBACK.description,
        functions=funciones,
        macros=macros,
    )


def resolve_module_doc(target: str) -> ModuleDoc:
    """Resuelve un archivo .h, directorio de cabeceras o librería de la cátedra (ej. treadstone.h) en un ModuleDoc."""
    ruta = Path(target)
    nombre_limpio = ruta.name.lower()
    stem = nombre_limpio[:-2] if nombre_limpio.endswith(".h") else nombre_limpio

    if ruta.is_file():
        doc = parse_header_documentation(ruta)
        if stem == "treadstone" and not doc.functions and not doc.macros:
            return _TREADSTONE_FALLBACK.model_copy(update={"header_name": ruta.name})
        return doc

    if ruta.is_dir():
        headers = sorted(ruta.rglob("*.h"))
        if not headers:
            raise FileNotFoundError(f"No se encontraron archivos .h en {ruta}")
        return _combinar_headers_en_modulo(
            headers,
            header_name=f"{ruta.name}.h",
            brief_default=f"Documentación de la biblioteca {ruta.name}",
        )

    treadstone_dir = _buscar_directorio_treadstone()
    if stem == "treadstone":
        if treadstone_dir is not None:
            headers = sorted(treadstone_dir.rglob("*.h"))
            return _combinar_headers_en_modulo(
                headers,
                header_name="treadstone.h",
                brief_default=_TREADSTONE_FALLBACK.brief,
            )
        return _TREADSTONE_FALLBACK

    if treadstone_dir is not None:
        cand_h = treadstone_dir / (nombre_limpio if nombre_limpio.endswith(".h") else f"{nombre_limpio}.h")
        if cand_h.is_file():
            return parse_header_documentation(cand_h)
        cand_sub = treadstone_dir / "tda" / (nombre_limpio if nombre_limpio.endswith(".h") else f"{nombre_limpio}.h")
        if cand_sub.is_file():
            return parse_header_documentation(cand_sub)

    raise FileNotFoundError(f"No se encontró el encabezado o librería «{target}».")


def instalar_manpage_usuario(
    module_name: str,
    troff_content: str,
    install_dir: Optional[Path] = None,
) -> List[Path]:
    """Instala el archivo <module_name>.3 en man3/ de install_dir y en rutas man3 escribibles del usuario."""
    base_name = module_name[:-2] if module_name.endswith(".h") else module_name
    instalados: List[Path] = []

    destinos_base: List[Path] = []
    if install_dir is not None:
        destinos_base.append(install_dir)
    else:
        home = Path.home()
        for cand in (
            home / ".local" / "share" / "man",
            home / "miniconda3" / "share" / "man",
            home / "miniconda3" / "man",
        ):
            if cand.parent.is_dir() and os.access(cand.parent, os.W_OK):
                destinos_base.append(cand)

    for base in destinos_base:
        try:
            man3_dir = base if base.name == "man3" else base / "man3"
            man3_dir.mkdir(parents=True, exist_ok=True)
            archivo_3 = man3_dir / f"{base_name}.3"
            archivo_3.write_text(troff_content, encoding="utf-8")
            instalados.append(archivo_3)
        except OSError:
            continue

    return instalados


def generate_manpage(
    target: str,
    output_file: Optional[Path] = None,
    install_dir: Optional[Path] = None,
    auto_install: bool = True,
) -> Dict[str, object]:
    """Genera la página man 3 para target y opcionalmente la escribe/instala."""
    doc = resolve_module_doc(target)
    troff = render_man_page(doc)
    base_name = doc.header_name[:-2] if doc.header_name.endswith(".h") else doc.header_name

    written_path: Optional[Path] = None
    if output_file is not None:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(troff, encoding="utf-8")
        written_path = output_file

    installed_paths: List[Path] = []
    if auto_install or install_dir is not None:
        installed_paths = instalar_manpage_usuario(base_name, troff, install_dir=install_dir)

    return {
        "module": base_name,
        "header_name": doc.header_name,
        "functions_count": len(doc.functions),
        "macros_count": len(doc.macros),
        "output_file": str(written_path) if written_path else None,
        "installed_paths": [str(p) for p in installed_paths],
        "troff": troff,
    }
