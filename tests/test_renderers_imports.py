"""Regresión de CORBEL-D0201: renderers.py importaba `html` sin usarlo."""

import ast
from pathlib import Path

import corbel.core.renderers as renderers


def test_renderers_no_tiene_imports_muertos():
    arbol = ast.parse(Path(renderers.__file__).read_text(encoding="utf-8"))
    importados = {a.asname or a.name.split(".")[0] for n in ast.walk(arbol)
                  if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names}
    usados = {n.id for n in ast.walk(arbol) if isinstance(n, ast.Name)}
    assert not (importados - usados), importados - usados
