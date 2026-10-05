# CORBEL — Generador Liviano de Documentación y man pages (man 3) en C

> 📖 **Manual de Usuario:** Para una guía exhaustiva de comandos, banderas, arquitectura y ejemplos, consultá el [Manual de Uso](MANUAL.md).

**CORBEL** extrae comentarios estructurados Doxygen (`@brief`, `@param`, `@return`, `@pre`, `@post`) desde cabeceras C (`.h`) y genera páginas estáticas en Markdown o páginas de manual para terminal (`man 3 <modulo>`).

---

## 🎯 Alcance

### Qué cubre
- Extracción estática de comentarios de documentación estructurada (tipo Doxygen/Javadoc, incluidos los tags `@pre`/`@post`) en archivos de cabecera C (`.h`). No interpreta anotaciones ACSL (`/*@ requires … */`): esas las verifica `callahan`.
- Generación de documentación técnica en Markdown, JSON y páginas de manual Unix (`man 3`). No genera HTML.
- Validación de completitud documental: advertencias sobre funciones públicas sin documentar o discrepancias con los prototipos.

### Qué no cubre (Límites y Delegación)
- Demostración matemática formal de los contratos (delegado a `callahan`).
- Verificación de encapsulamiento y opacidad de TDAs (delegado a `motoko`).
- Verificación de reglas de estilo de código (delegado a `gaff`).

---

## 📋 Requisitos

### Requisitos de Sistema y Entorno
- Multiplataforma. Python >= 3.10.

### Dependencias Externas y Binarios
- `groff` o `man` (opcional, para visualización de páginas `man 3`).

### Integración en el Ecosistema
- CLI `corbel`. Plugin registrado en `ripley.plugins` (`documentation`).

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

```bash
# Qué falta documentar (y, con --completitud, qué tags le faltan a cada docblock)
corbel check tda_lista.h --completitud

# Porcentaje de la API documentada; con --min sale 1 por debajo (para el CI de la plantilla)
corbel coverage include/ --min 80
```

Un docblock que todavía tiene el texto de relleno de `corbel scaffold` o de `gaff fix`
(`[Descripción breve…]`, `[completar: …]`) cuenta como **documentación ausente**: el esqueleto
no es documentación. Con `--completitud` también se marcan los docblocks desactualizados: un
`@param` que ya no está en la firma (se renombró o se sacó) o un `@return` en una función `void`.

<!-- p1:referencia:inicio — generado por p1-tools/scripts/readme_generado.py: no editar a mano -->

## Referencia rápida

### Requisitos

- Python ≥ 3.11 y [uv](https://docs.astral.sh/uv/getting-started/installation/).

### Comandos

| Comando | Descripción |
|:--|:--|
| `corbel doc` | Genera documentación a partir de comentarios estructurados o inyecta placeholders en cabeceras C. |
| `corbel stub`, `corbel scaffold` | Agrega placeholders estructurados de documentación (@brief, @param, @return, @pre, @post) a todas las funciones, estructuras, uniones, enumeraciones y tipos indocumentados. |
| `corbel lint`, `corbel check` | Audita e informa todos los elementos C que carecen de comentarios Doxygen. |
| `corbel coverage` | Porcentaje de la API pública documentada por completo (docblock, sin relleno y con todos sus tags). |
| `corbel report` | Genera directamente la sección de reporte Markdown de CORBEL para Dredd. |
| `corbel doctor` | Verifica el estado del entorno de documentación CORBEL (Python, man). |
| `corbel version` | Muestra la versión de CORBEL. |

Ayuda de cada comando: `corbel <comando> -h`.

### Salida JSON

Con `--json`, estos comandos emiten el resultado como JSON por la salida estándar, para usarlo desde scripts, ripley o dredd: `corbel lint`, `corbel check`, `corbel coverage`, `corbel doctor`. El de `doctor --json` lleva `schema_version` y `ok`.

### Códigos de salida

| Código | Significado |
|:--|:--|
| `0` | Terminó bien (en `doctor`: está todo lo requerido). |
| `1` | El comando encontró problemas (hallazgos, pruebas que fallan, un umbral que no se alcanza) o un dato no se pudo usar (un archivo ilegible, un formato inválido). |
| `2` | Error de uso: comando, opción o argumento inválido. |

<!-- p1:referencia:fin -->
