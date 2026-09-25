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
