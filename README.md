# CORBEL — Generador Liviano de Documentación y man pages (man 3) en C

**CORBEL** extrae comentarios estructurados Doxygen (`@brief`, `@param`, `@return`, `@pre`, `@post`) desde cabeceras C (`.h`) y genera páginas estáticas en Markdown o páginas de manual para terminal (`man 3 <modulo>`).

---

## 🚀 Uso Rápido

```bash
# Visualizar documentación en terminal
corbel doc tda_lista.h

# Exportar a Markdown
corbel doc tda_lista.h --format markdown -o LISTA_API.md

# Generar página man 3 para UNIX
corbel doc tda_lista.h --format man -o /usr/local/man/man3/tda_lista.3
```
