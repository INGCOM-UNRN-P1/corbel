# Manual de Uso y Referencia Técnica: corbel

> **CORBEL** — Generador liviano de documentación de APIs, TDAs y man pages (man 3) en C
> **Versión:** `0.1.0` · **CLI principal:** `corbel` · **Plugin Ripley:** `documentation`

---

## 1. Arquitectura y Propósito Pedagógico

`corbel` forma parte del ecosistema de herramientas de la cátedra de Programación 1 (UNRN). Su objetivo central es resolver de forma modular, determinista y automatizada las tareas asociadas a su dominio específico dentro del ciclo de desarrollo, evaluación y aprendizaje de software en C.

### Alcance Funcional (Qué cubre)
- Extracción estática de comentarios de documentación estructurada (tipo Doxygen/Javadoc, incluidos los tags `@pre`/`@post`) en archivos de cabecera C (`.h`). No interpreta anotaciones ACSL (`/*@ requires … */`): esas las verifica `callahan`.
- Generación de documentación técnica en Markdown, JSON y páginas de manual Unix (`man 3`). No genera HTML.
- Validación de completitud documental: advertencias sobre funciones públicas sin documentar o discrepancias con los prototipos.

### Límites de Responsabilidad y Delegación (Qué no cubre)
- Demostración matemática formal de los contratos (delegado a `callahan`).
- Verificación de encapsulamiento y opacidad de TDAs (delegado a `motoko`).
- Verificación de reglas de estilo de código (delegado a `gaff`).

### Principios de Diseño
- **Enfoque Pedagógico:** Diagnósticos y mensajes en español rioplatense orientados a facilitar la comprensión de errores conceptuales.
- **Salida Estructurada Dual:** Soporte nativo para visualización enriquecida en terminal (Rich) y salida parseable para orquestadores (`--json`).
- **Integración Contractual:** Capacidad de emitir secciones de reporte para `dredd` (`dredd-section`) y actuar como satélite orquestado por `ripley`.
- **Idempotencia y Robustez:** Validación de precondiciones y comandos de autodiagnóstico (`doctor`) para verificación del entorno.

---

## 2. Instalación y Requisitos

### Requisitos del Sistema
- **Python:** `>= 3.10` (recomendado Python 3.11 o 3.12).
- **Gestor de paquetes:** [`uv`](https://github.com/astral-sh/uv) (entorno estándar de cátedra).
- **Toolchain C (si aplica):** GCC / Clang, Make, GDB y bibliotecas estándar de desarrollo.

### Instalación en el Entorno de Usuario
Para instalar la herramienta de forma global y aislada en el sistema mediante `uv tool`:
```bash
uv tool install --editable /home/mrtin/dev/tools/corbel
```

### Verificación de Instalación
Ejecutá el comando `doctor` para constatar que todas las dependencias y binarios requeridos estén presentes y operativos:
```bash
corbel doctor
```

---

## 3. Guía Integral de Comandos (CLI)

| Comando | Descripción Breve |
| :--- | :--- |
| [`corbel doc`](#doc) | Genera documentación a partir de comentarios estructurados o inyecta placeholders en cabeceras C. |
| [`corbel stub`](#stub) | Agrega placeholders estructurados de documentación (@brief, @param, @return, @pre, @post) |
| [`corbel scaffold`](#scaffold) | Agrega placeholders estructurados de documentación (@brief, @param, @return, @pre, @post) |
| [`corbel lint`](#lint) | Audita e informa todos los elementos C que carecen de comentarios Doxygen. |
| [`corbel check`](#check) | Audita e informa todos los elementos C que carecen de comentarios Doxygen. |
| [`corbel report`](#report) | Genera directamente la sección de reporte Markdown de CORBEL para Dredd. |
| [`corbel doctor`](#doctor) | Verifica el estado del entorno de documentación CORBEL (Python, man). |
| [`corbel version`](#version) | Muestra la versión de CORBEL. |

### `corbel doc`

Genera documentación a partir de comentarios estructurados o inyecta placeholders en cabeceras C.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `header_path` | `<class 'pathlib._local.Path'>` | Archivo .h a documentar |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--format`, `-f` | `<class 'str'>` | `markdown` | Formato de salida: markdown, man, json |
| `--output`, `-o` | `Optional[pathlib._local.Path]` | `None` | Archivo de destino (por defecto imprime en consola o genera archivo según formato) |
| `--placeholders`, `--scaffold`, `-p` | `<class 'bool'>` | `False` | Inyectar placeholders Doxygen en el código fuente en lugar de exportar documentación |
| `--in-place`, `-i` | `<class 'bool'>` | `False` | Modificar el archivo .h directamente al usar --placeholders |

#### Ejemplo de Invocación
```bash
corbel doc <header_path>
```

### `corbel stub`

Agrega placeholders estructurados de documentación (@brief, @param, @return, @pre, @post)
a todas las funciones, estructuras, uniones, enumeraciones y tipos indocumentados.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `target` | `<class 'pathlib._local.Path'>` | Archivo .h o .c a documentar |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--in-place`, `-i` | `<class 'bool'>` | `False` | Modificar el archivo directamente in-place. |
| `--output`, `-o` | `Optional[pathlib._local.Path]` | `None` | Archivo de destino. |
| `--file-header/--no-file-header` | `<class 'bool'>` | `True` | Incluir encabezado general @file al inicio del archivo. |

#### Ejemplo de Invocación
```bash
corbel stub <target>
```

### `corbel scaffold`

Agrega placeholders estructurados de documentación (@brief, @param, @return, @pre, @post)
a todas las funciones, estructuras, uniones, enumeraciones y tipos indocumentados.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `target` | `<class 'pathlib._local.Path'>` | Archivo .h o .c a documentar |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--in-place`, `-i` | `<class 'bool'>` | `False` | Modificar el archivo directamente in-place. |
| `--output`, `-o` | `Optional[pathlib._local.Path]` | `None` | Archivo de destino. |
| `--file-header/--no-file-header` | `<class 'bool'>` | `True` | Incluir encabezado general @file al inicio del archivo. |

#### Ejemplo de Invocación
```bash
corbel scaffold <target>
```

### `corbel lint`

Audita e informa todos los elementos C que carecen de comentarios Doxygen.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `target` | `<class 'pathlib._local.Path'>` | Archivo .h o .c a auditar |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--json` | `<class 'bool'>` | `False` | Emitir salida en formato JSON estructurado |
| `--md`, `--output-md` | `Optional[pathlib._local.Path]` | `None` | Generar sección de reporte en formato Markdown para fusión en Dredd. |
| `--completitud` | `<class 'bool'>` | `False` | Auditar además los docblocks existentes e informar los tags que les faltan (@brief, @param, @return). |

#### Ejemplo de Invocación
```bash
corbel lint <target>
```

### `corbel check`

Audita e informa todos los elementos C que carecen de comentarios Doxygen.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `target` | `<class 'pathlib._local.Path'>` | Archivo .h o .c a auditar |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--json` | `<class 'bool'>` | `False` | Emitir salida en formato JSON estructurado |
| `--md`, `--output-md` | `Optional[pathlib._local.Path]` | `None` | Generar sección de reporte en formato Markdown para fusión en Dredd. |
| `--completitud` | `<class 'bool'>` | `False` | Auditar además los docblocks existentes e informar los tags que les faltan (@brief, @param, @return). |

#### Ejemplo de Invocación
```bash
corbel check <target>
```

### `corbel report`

Genera directamente la sección de reporte Markdown de CORBEL para Dredd.

#### Argumentos
| Argumento | Tipo | Descripción |
| :--- | :--- | :--- |
| `target` | `<class 'pathlib._local.Path'>` | Archivo .h o .c a auditar |

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--output`, `-o` | `Optional[pathlib._local.Path]` | `None` | Ruta de destino del archivo Markdown. |

#### Ejemplo de Invocación
```bash
corbel report <target>
```

### `corbel doctor`

Verifica el estado del entorno de documentación CORBEL (Python, man).

#### Opciones y Banderas
| Opción / Banderas | Tipo | Por Defecto | Descripción |
| :--- | :--- | :--- | :--- |
| `--json` | `<class 'bool'>` | `False` | Emitir diagnóstico en formato JSON estructurado. |

#### Ejemplo de Invocación
```bash
corbel doctor
```

### `corbel version`

Muestra la versión de CORBEL.

#### Ejemplo de Invocación
```bash
corbel version
```

---

## 4. Formatos de Salida e Integración con el Ecosistema

### Modo Interactivo / Terminal (Rich)
Por defecto, la herramienta renderiza paneles, árboles y tablas estilizadas para facilitar la lectura del estudiante y docente en terminales modernas con soporte ANSI.

### Modo Estructurado JSON (`--json`)
Para integración con pipelines de CI/CD, scripts de automatización u orquestadores externos, la opción `--json` emite un documento JSON estricto por la salida estándar (`stdout`), dirigiendo cualquier mensaje de logging a `stderr`:
```bash
corbel doc --json
```

### Integración con Dredd (`dredd-section`)
Cuando la herramienta genera reportes de evaluación para entregas de alumnos, produce una sección Markdown estandarizada conforme al contrato de integración de Dredd (v1.0.0):
```markdown
<!-- dredd-section: corbel, tool=corbel, version=0.1.0, status=ok -->
```
Este encabezado garantiza la agregación determinista de los hallazgos en la rúbrica docente.

### Integración con Ripley
`corbel` está registrada en el catálogo de plugins satélites de Ripley (`SATELLITE_CATALOG`). Puede invocarse directamente a través del motor de evaluación de Ripley configurando el análisis en `ripley.toml`.

---

## 5. Diagnóstico y Códigos de Salida

### Códigos de Retorno (`exit code`)
| Código | Significado |
| :---: | :--- |
| `0` | Ejecución exitosa sin hallazgos críticos ni errores de sintaxis. |
| `1` | Hallazgos pedagógicos detectados, infracción de reglas o advertencias activas. |
| `2` | Error de sintaxis en argumentos CLI o archivo fuente no encontrado. |
| `>2` | Error no recuperable del sistema, fallo de memoria o excepción interna. |

### Diagnóstico del Entorno (`doctor`)
Ante comportamientos inesperados, verificá el estado operativo con:
```bash
corbel doctor
```
Comprueba la presencia de las dependencias requeridas y la integridad de los componentes del paquete.