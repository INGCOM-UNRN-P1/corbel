# corbel: documentación de proyectos completos e integración con make

> Especificación funcional y técnica · Estado: **propuesta** · Ámbito: `corbel`,
> `plantilla-TP` (`tp.sh`), `plantilla-libreria`, y consumidores (`jonesy`, `ripley`,
> `dredd`).

## 1. Contexto y objetivo

Hoy `corbel doc` documenta **un** `.h` por vez, y `corbel coverage` mide la
documentación de una lista de cabeceras. Un trabajo práctico de la cátedra, en cambio,
es un **proyecto** con varias bibliotecas (`libs/*`) y ejercicios (`ejercicios/*`), cada
uno con su Makefile (ver `plantilla-TP` y `plantilla-libreria`). Para documentar un TP el
alumno tiene que invocar `corbel` cabecera por cabecera y no obtiene un índice ni una
vista del conjunto.

Objetivo: que `corbel` genere **la documentación de todas las funciones de un
proyecto** (sus bibliotecas y ejercicios) con un solo comando, en Markdown, `man 3` y
JSON, y que eso se pueda pedir con **`make doc`** desde cualquier nivel del proyecto,
igual que `make test`.

Resultado esperado para el alumno:

```bash
make doc          # en la raíz: doc/ con un índice y una página por biblioteca y ejercicio
make doc-check    # ¿falta documentar algo? sale 1 si la cobertura está bajo el mínimo
man -l doc/man/man3/lista_crear.3
```

## 2. Alcance

### Qué cubre
- Descubrimiento de los módulos de un proyecto (raíz, bibliotecas, ejercicios) con el
  mismo modelo que usan `jonesy` y el Makefile raíz de `plantilla-TP`.
- Extracción de la documentación Doxygen (`@brief`, `@param`, `@return`, `@pre`,
  `@post`, `@see`, `@note`) de **funciones y tipos** de cada módulo, vinculando la
  declaración (`.h`) con la definición (`.c`).
- Generación de un **sitio de documentación del proyecto**: índice, una página por
  módulo, páginas `man 3` y un `api.json` versionado.
- Cobertura por módulo y total, con mínimo configurable para la CI.
- Objetivos de make (`doc`, `doc-check`, `doc-clean`) en las plantillas y en los
  Makefiles que regenera `tp.sh sync`.

### Qué no cubre
- HTML (sigue fuera de alcance: Markdown se ve en GitHub y en `jonesy`).
- Verificación formal de `@pre`/`@post` (`callahan`), opacidad de TDAs (`motoko`) y
  estilo (`gaff`).
- Documentación de proyectos que no sean C.

## 3. Conceptos

| Término | Definición |
|---|---|
| **Proyecto** | Directorio raíz del TP. Se detecta por `Makefile`, `tp.sh`, `.git` o `corbel.toml`. |
| **Módulo** | Directorio con Makefile dentro del proyecto (hasta dos niveles), o declarado en `corbel.toml`. |
| **Biblioteca** | Módulo bajo `libs/` (o `lib/`, `librerias/`), o con `library.json`, o cuyo Makefile arma un `lib*.a`. |
| **Ejercicio** | Módulo bajo `ejercicios/` o con `main.c`. |
| **API pública** | Funciones y tipos declarados en los `.h` del módulo (`include/` en bibliotecas estructuradas, la raíz del módulo en las planas). |
| **Funciones internas** | Funciones `static` o definidas en un `.c` sin prototipo en ningún `.h`. Se documentan sólo con `--internas`. |
| **Documento de módulo** | Página con la API del módulo, agrupada por cabecera. |

La clasificación tiene que coincidir con la de `jonesy` (`jonesy-core/src/estructura.rs`)
para que el alumno vea los mismos módulos en el IDE, en la documentación y en `make`.

## 4. Requisitos funcionales

### RF-1 — Descubrimiento del proyecto `[M]`

- **RF-1.1.** `corbel proyecto [RAIZ]` (por defecto `.`) recorre la raíz y sus
  subdirectorios hasta dos niveles buscando Makefiles; ignora directorios ocultos,
  `build/`, `testing/`, `doc/` y `node_modules/`.
- **RF-1.2.** Clasifica cada módulo según §3 y lee:
  - de `library.json`: `name`, `version`, `repository`;
  - del Makefile: `LIB_NAME` (bibliotecas que usa un ejercicio) y `PROG_TARGET`.
- **RF-1.3.** Si `RAIZ` es un módulo suelto (una biblioteca clonada sola, por ejemplo),
  lo trata como proyecto de un único módulo.
- **RF-1.4.** `corbel.toml` en la raíz puede agregar, excluir o renombrar módulos (§6).

### RF-2 — Extracción `[M]`

- **RF-2.1. Funciones públicas**: todas las funciones declaradas en los `.h` del módulo,
  con su firma normalizada (como hoy en `DocumentedFunction.signature`).
- **RF-2.2. Declaración y definición**: para cada función pública se busca su definición
  en los `.c` del módulo y se registran ambas ubicaciones (`archivo:línea`).
  - El docblock se toma de la declaración (`.h`). Si la declaración no tiene y la
    definición sí, se usa el de la definición y se emite el aviso
    `documentacion-en-c` («la documentación de una función pública va en el .h»).
  - Si ambos tienen docblock y difieren en `@param`, se emite `documentacion-divergente`.
- **RF-2.3. Tipos**: `struct`, `union`, `enum` y `typedef` de los `.h`, con su
  `@brief`, sus campos o constantes (y la documentación de cada uno, si la tienen) y si el
  tipo es opaco (`typedef struct nodo nodo_t;` sin definición en el `.h`).
- **RF-2.4. Funciones internas** (`--internas`): las `static` y las que no tienen
  prototipo público, en una sección aparte del documento de módulo. `main` nunca se
  documenta como función.
- **RF-2.5. Referencias cruzadas**: `@see f`, y cualquier `f()` en el texto que nombre
  una función documentada del proyecto, se convierten en enlaces (Markdown) o en
  referencias `SEE ALSO` (man).
- **RF-2.6.** Los textos de relleno de `corbel scaffold` y `gaff fix`
  (`[Descripción breve…]`, `[completar: …]`) cuentan como documentación ausente, igual
  que hoy en `corbel check`.

### RF-3 — Salidas `[M]`

Todo bajo un directorio de salida (por defecto `doc/` en la raíz del proyecto):

```text
doc/
├── index.md                  # proyecto: módulos, cobertura y funciones por módulo
├── libs/arreglos.md          # un documento por módulo, con la ruta del módulo
├── ejercicios/ejercicio1.md
├── man/man3/
│   ├── arreglos.3            # página del módulo (lista de funciones)
│   ├── arreglo_crear.3       # una página por función pública
│   └── …
└── api.json                  # modelo completo, versionado (§5)
```

- **RF-3.1. `index.md`**: nombre del proyecto, tabla de módulos (tipo, versión,
  cobertura, cantidad de funciones) con enlace a cada documento, y para cada ejercicio
  las bibliotecas que usa (`LIB_NAME`).
- **RF-3.2. Documento de módulo**: resumen del módulo (docblock de archivo del `.h`
  principal, si existe), y por cada cabecera sus tipos y funciones con firma, `@brief`,
  descripción, parámetros, retorno, pre y poscondiciones, ubicación de la declaración y la
  definición, y referencias. Las funciones sin documentar figuran igual, marcadas como
  «sin documentar», para que el documento sea también una lista de pendientes.
- **RF-3.3. `man 3`**: una página por función (`NAME`, `SYNOPSIS` con el `#include`,
  `DESCRIPTION`, `RETURN VALUE`, `NOTES` con pre/poscondiciones, `SEE ALSO`) y una por
  módulo. Sección `3` y título en mayúsculas como las de la libc. Legibles con
  `man -l` sin instalarlas.
- **RF-3.4. `api.json`**: el modelo completo con `schema_version`, para otras
  herramientas (§5).
- **RF-3.5. Formatos**: `--formato markdown,man,json` (por defecto los tres).
- **RF-3.6. Determinismo**: misma entrada, misma salida byte a byte (orden alfabético de
  módulos, cabeceras y funciones; sin fechas salvo con `--fecha`). Así `doc/` se puede
  versionar y los cambios se ven en `git diff`.
- **RF-3.7. Limpieza**: los archivos de `doc/` que corbel generó en una corrida anterior
  y ya no corresponden (una función borrada) se eliminan. corbel sólo borra lo que
  registró en `doc/.corbel-manifest` y nunca toca otros archivos de `doc/`.

### RF-4 — Cobertura y verificación `[M]`

- **RF-4.1.** La cobertura de un módulo es el porcentaje de funciones y tipos públicos
  con docblock completo (mismo criterio que `corbel coverage`). La del proyecto es la
  suma de todos los módulos (no el promedio).
- **RF-4.2.** `--min N` sale con código 1 si la cobertura del proyecto queda bajo `N`.
  `corbel.toml` puede fijar mínimos por módulo.
- **RF-4.3.** `corbel proyecto --check` no escribe nada: informa la cobertura y los
  avisos, y sale con código 1 si la cobertura está bajo el mínimo **o** si `doc/` está
  desactualizado respecto del código (con `--actualizada`). Para la CI de las plantillas.
- **RF-4.4.** `--json` imprime el resumen (módulos, cobertura, avisos, archivos
  escritos) para `ripley`, `dredd` y `jonesy`.

### RF-5 — Selección `[S]`

- **RF-5.1.** `--modulo NOMBRE` (repetible) restringe la generación a esos módulos; el
  índice se regenera igual con todos (los que no se procesaron conservan su entrada
  anterior, leída del manifiesto).
- **RF-5.2.** Desde un subdirectorio, `corbel proyecto --aca` documenta sólo el módulo
  actual pero escribe en el `doc/` de la raíz (lo usa `make doc` dentro de un módulo).

### RF-6 — Integración con make `[M]`

Ver §7 para el código de los Makefiles.

- **RF-6.1.** Objetivos en el **Makefile raíz** de `plantilla-TP`:
  - `doc`: documentación de todo el proyecto en `doc/`;
  - `doc-check`: cobertura y avisos; sale 1 bajo `DOC_MIN`;
  - `doc-clean`: borra lo generado (según el manifiesto).
- **RF-6.2.** Objetivos en el **Makefile de cada biblioteca y ejercicio** (los que genera
  `tp.sh`): `doc` y `doc-check` del módulo, que escriben en el `doc/` de la raíz.
- **RF-6.3.** Cada objetivo lleva un comentario arriba que dice qué hace (así lo muestran
  `jonesy` y `make help`).
- **RF-6.4.** Si `corbel` no está instalado, `make doc` avisa y sale con 0 (como `fallos`
  con `vasquez`); con `DOC_ESTRICTO=1` (la CI) sale con 1.
- **RF-6.5.** Variables sobreescribibles: `CORBEL ?= corbel`, `DOC_DIR ?= doc`,
  `DOC_MIN ?= 0`, `DOC_FORMATOS ?= markdown,man,json`, `DOC_FLAGS ?=`.
- **RF-6.6.** `make doc` no depende de compilar: no lleva prerrequisitos de objetos.
- **RF-6.7.** `tp.sh sync` regenera los Makefiles con estos objetivos, y `tp.sh doc
  [modulo]` llama a `make doc` (o `make -C <módulo> doc`).
- **RF-6.8.** `plantilla-libreria` agrega `doc` y `doc-check` a su Makefile y declara las
  páginas `man 3` en `library.json` (`exports.docs`) para que un TP que la clona pueda
  incorporarlas a su `doc/`.

### RF-7 — Configuración `[S]`

`corbel.toml` en la raíz del proyecto (opcional; todo tiene valor por defecto):

```toml
[proyecto]
nombre = "TP3: listas enlazadas"   # título del índice (por defecto el nombre del directorio)
salida = "doc"
formatos = ["markdown", "man", "json"]
internas = false                    # documentar funciones static y sin prototipo público
minimo = 80                         # cobertura mínima del proyecto (%)

[[modulo]]
dir = "libs/arreglos"
minimo = 100                        # una biblioteca de la cátedra tiene que estar completa

[[modulo]]
dir = "ejercicios/ejercicio3"
excluir = true                      # borrador: no se documenta ni cuenta para la cobertura

[[modulo]]
dir = "extra/utilidades"            # módulo sin Makefile
tipo = "libreria"
```

Las variables de make (`DOC_MIN`, `DOC_FORMATOS`) ganan sobre `corbel.toml` cuando se
pasan explícitamente.

### RF-8 — Mensajes `[M]`

En español rioplatense y orientados a la acción. Ejemplos:

- `lista_insertar (libs/lista/lista.h:23) no tiene documentación: corré «corbel scaffold libs/lista/lista.h» para generar el esqueleto.`
- `nodo_crear está documentada en lista.c pero no en lista.h: la documentación de la API va en el .h.`
- `@param cantidad no está en la firma de arreglo_sumar (¿se renombró?).`
- `Cobertura del proyecto 72,4 % (mínimo 80 %): faltan 9 funciones. «make doc-check» lista cuáles.`

## 5. Modelo de datos (`api.json`)

```json
{
  "schema_version": "1.0.0",
  "proyecto": { "nombre": "tp3", "raiz": "." },
  "cobertura": { "total": 34, "documentados": 30, "porcentaje": 88.2 },
  "modulos": [
    {
      "nombre": "arreglos",
      "dir": "libs/arreglos",
      "tipo": "libreria",
      "version": "1.1.0",
      "usa": [],
      "cobertura": { "total": 12, "documentados": 12, "porcentaje": 100.0 },
      "cabeceras": [
        {
          "archivo": "libs/arreglos/arreglos.h",
          "brief": "Operaciones sobre arreglos de enteros.",
          "tipos": [
            { "nombre": "arreglo_t", "clase": "typedef", "opaco": true, "brief": "…", "declaracion": "arreglos.h:12" }
          ],
          "funciones": [
            {
              "nombre": "arreglo_crear",
              "firma": "arreglo_t *arreglo_crear(size_t capacidad)",
              "brief": "Crea un arreglo vacío.",
              "descripcion": "",
              "parametros": [{ "nombre": "capacidad", "descripcion": "…" }],
              "retorno": "El arreglo, o NULL si no hay memoria.",
              "pre": [], "post": [],
              "ver": ["arreglo_destruir"],
              "declaracion": "libs/arreglos/arreglos.h:20",
              "definicion": "libs/arreglos/arreglos.c:15",
              "documentada": true,
              "faltan": []
            }
          ]
        }
      ],
      "internas": []
    }
  ],
  "avisos": [
    { "codigo": "documentacion-en-c", "funcion": "nodo_crear", "archivo": "libs/lista/lista.c", "linea": 40, "mensaje": "…" }
  ]
}
```

- Extiende los modelos actuales (`ModuleDoc`, `DocumentedFunction`) en lugar de
  reemplazarlos: `corbel doc archivo.h --format json` sigue emitiendo el formato de hoy.
- `faltan` lista los tags ausentes (`brief`, `param:capacidad`, `return`), como
  `corbel check --completitud`.
- Las rutas son relativas a la raíz y usan `/` en todas las plataformas.
- Cambios incompatibles suben la versión mayor de `schema_version`.

## 6. CLI

```text
corbel proyecto [RAIZ]            (alias: corbel project)
    --salida DIR                  directorio de salida (por defecto doc/)
    --formato LISTA               markdown,man,json (por defecto los tres)
    --modulo NOMBRE               sólo ese módulo (repetible)
    --aca                         sólo el módulo del directorio actual, escribiendo en el doc/ de la raíz
    --internas                    incluir funciones static y sin prototipo público
    --min N                       cobertura mínima del proyecto; bajo N sale 1
    --check                       no escribir: informar y verificar el mínimo
    --actualizada                 con --check: falla si doc/ no coincide con el código
    --limpiar                     borrar lo generado (según el manifiesto) y salir
    --fecha                       incluir la fecha de generación (rompe el determinismo)
    --json                        resumen estructurado por stdout
```

Códigos de salida: `0` bien; `1` cobertura bajo el mínimo o documentación desactualizada;
`2` error de uso o del proyecto (no hay módulos, `corbel.toml` inválido).

`corbel coverage` gana `--proyecto [RAIZ]` con la tabla por módulo (mismo cálculo que
RF-4.1) para quien sólo quiere el número.

## 7. Integración con los Makefiles

### 7.1. Makefile raíz (`plantilla-TP`, generado por `tp.sh sync`)

```make
# Documentación (corbel): variables que se pueden cambiar al invocar make
CORBEL ?= corbel
DOC_DIR ?= doc
DOC_MIN ?= 0
DOC_FORMATOS ?= markdown,man,json
DOC_FLAGS ?=

.PHONY: doc doc-check doc-clean

# Genera la documentación de todas las bibliotecas y ejercicios en doc/
doc:
	@if command -v $(CORBEL) >/dev/null 2>&1; then \
		$(CORBEL) proyecto . --salida $(DOC_DIR) --formato $(DOC_FORMATOS) $(DOC_FLAGS); \
	else \
		echo "corbel no está instalado: se saltea la documentación"; \
		test -z "$(DOC_ESTRICTO)"; \
	fi

# Verifica que la API esté documentada (sale 1 bajo DOC_MIN %)
doc-check:
	@if command -v $(CORBEL) >/dev/null 2>&1; then \
		$(CORBEL) proyecto . --check --min $(DOC_MIN) $(DOC_FLAGS); \
	else \
		echo "corbel no está instalado: se saltea la verificación de documentación"; \
		test -z "$(DOC_ESTRICTO)"; \
	fi

# Borra la documentación generada (sólo lo que corbel registró en su manifiesto)
doc-clean:
	@if command -v $(CORBEL) >/dev/null 2>&1; then \
		$(CORBEL) proyecto . --salida $(DOC_DIR) --limpiar; \
	fi
```

La raíz **no** recorre los módulos con `$(MAKE) -C` (a diferencia de `test`): una sola
invocación de corbel ve todo el proyecto y arma un índice coherente.

### 7.2. Makefile de biblioteca y de ejercicio (generados por `tp.sh`)

```make
# Documentación de este módulo (escribe en el doc/ de la raíz del proyecto)
CORBEL ?= corbel
DOC_MIN ?= 0

.PHONY: doc doc-check

# Genera la documentación de este módulo en doc/ de la raíz
doc:
	@if command -v $(CORBEL) >/dev/null 2>&1; then \
		$(CORBEL) proyecto $(ROOT_DIR) --aca; \
	else \
		echo "corbel no está instalado: se saltea la documentación"; \
		test -z "$(DOC_ESTRICTO)"; \
	fi

# Verifica que la API de este módulo esté documentada (sale 1 bajo DOC_MIN %)
doc-check:
	@if command -v $(CORBEL) >/dev/null 2>&1; then \
		$(CORBEL) proyecto $(ROOT_DIR) --aca --check --min $(DOC_MIN); \
	else \
		echo "corbel no está instalado: se saltea la verificación de documentación"; \
		test -z "$(DOC_ESTRICTO)"; \
	fi
```

`ROOT_DIR` ya existe en esos Makefiles (`ROOT_DIR = ../..`). Para que `--aca` funcione
desde el directorio del módulo, corbel resuelve el módulo por el directorio actual y el
proyecto por `RAIZ`.

### 7.3. `tp.sh`

- `sync`: los tres heredocs (raíz, biblioteca plana, ejercicio) incluyen los bloques de
  §7.1 y §7.2. Las bibliotecas estructuradas (clonadas de `plantilla-libreria`)
  conservan su Makefile; `sync` no lo toca.
- `doc [modulo]`: sin argumento, `make doc` en la raíz; con un módulo,
  `make -C <libs|ejercicios>/<modulo> doc`.
- La ayuda de `tp.sh` suma la línea de `doc`, con el formato que ya lee `jonesy`.

### 7.4. `plantilla-libreria`

- Objetivos `doc` y `doc-check` como en §7.2, pero con `corbel proyecto .` (la biblioteca
  es su propio proyecto).
- `library.json` agrega en `exports` las páginas generadas:

  ```json
  "docs": [
    { "source": "doc/man/man3", "destination": "doc/man/man3" }
  ]
  ```

- La CI de la plantilla corre `make doc-check DOC_MIN=100 DOC_ESTRICTO=1`.

### 7.5. CI de `plantilla-TP`

Un paso `make doc-check DOC_ESTRICTO=1` con el `DOC_MIN` que fije cada cátedra
(por defecto 0: informa sin fallar).

## 8. Integración con el ecosistema

| Herramienta | Uso |
|---|---|
| **jonesy** | Lee `doc/api.json` para que el quick-doc muestre la documentación de las funciones del propio proyecto (hoy sólo extrae prototipos del archivo activo). Los objetivos `doc` y `doc-check` aparecen solos en la vista Proyecto con su descripción. Si `api.json` no existe o es viejo, `jonesy` no lo regenera: ofrece `make doc`. |
| **ripley** | El plugin `documentation` usa `corbel proyecto --check --json` cuando analiza un directorio de proyecto, y `corbel check` como hoy para un archivo suelto. |
| **dredd** | `corbel report --proyecto` emite la sección de documentación con la tabla de cobertura por módulo. |
| **gaff** | Sin cambios: sus placeholders cuentan como ausentes (RF-2.6). |
| **voight** | Sin cambios. |

## 9. Requisitos no funcionales

- **RNF-1. Tiempo**: un TP típico (≈ 10 módulos, 20 cabeceras, 150 funciones) en
  ≤ 2 s; `--check` en ≤ 1 s.
- **RNF-2. Sin red ni dependencias nuevas**: sigue usando el parser de tree-sitter que ya
  tiene corbel.
- **RNF-3. Multiplataforma**: Linux, macOS y Windows (UCRT64 del `entorno`); rutas con
  `/` en las salidas.
- **RNF-4. Determinismo**: ver RF-3.6. La prueba de aceptación compara dos corridas byte a
  byte.
- **RNF-5. Seguridad de archivos**: escritura atómica (temporal + renombre) y borrado
  limitado al manifiesto (RF-3.7).
- **RNF-6. Compatibilidad**: `corbel doc`, `check`, `coverage`, `report` y sus JSON no
  cambian de comportamiento.

## 10. Criterios de aceptación

1. **Plantilla-TP**: en una copia de `plantilla-TP` (dos bibliotecas, tres ejercicios),
   `make doc` crea `doc/index.md` con cinco módulos, un documento por módulo, páginas
   `man 3` de cada función pública y `doc/api.json` válido contra el esquema.
2. **Ejercicio**: `make -C ejercicios/ejercicio1 doc` actualiza
   `doc/ejercicios/ejercicio1.md` e `index.md` sin tocar los documentos de los otros
   módulos.
3. **Sin documentar**: con una función sin docblock, `make doc-check DOC_MIN=100` sale con
   1 y el mensaje dice qué función, dónde y cómo generar el esqueleto.
4. **Documentación en el .c**: una función documentada sólo en su `.c` aparece en la
   documentación y produce el aviso `documentacion-en-c`.
5. **Determinismo**: dos `make doc` seguidos dejan `git status` limpio.
6. **Limpieza**: al borrar una función y correr `make doc`, su página `man 3`
   desaparece; un `doc/notas.md` escrito a mano no se toca.
7. **Sin corbel**: con `corbel` fuera del `PATH`, `make doc` imprime el aviso y sale 0;
   con `DOC_ESTRICTO=1`, sale 1.
8. **jonesy**: con `doc/api.json` presente, el quick-doc muestra el `@brief` y los
   parámetros de una función de `libs/arreglos` al escribirla en un ejercicio.
9. **tp.sh**: después de `./tp.sh add-ex ejercicio4 arreglos` y `./tp.sh sync`, el
   Makefile del ejercicio nuevo tiene `doc` y `doc-check`.

## 11. Plan de implementación

| Fase | Contenido | Repositorio |
|---|---|---|
| 1 | Descubrimiento del proyecto (RF-1) y modelo extendido con tipos, ubicaciones y `api.json` (RF-2.1–2.3, §5) | corbel |
| 2 | `corbel proyecto` con Markdown, man e índice; manifiesto y limpieza (RF-3) | corbel |
| 3 | Cobertura por módulo, `--check`, `--min`, `--json`, `corbel.toml` (RF-4, RF-7) | corbel |
| 4 | `--modulo` y `--aca` (RF-5); internas y referencias cruzadas (RF-2.4, RF-2.5) | corbel |
| 5 | Makefiles y `tp.sh` (RF-6.1–6.7), CI de la plantilla | plantilla-TP |
| 6 | `plantilla-libreria`: objetivos y `exports.docs` (RF-6.8) | plantilla-libreria |
| 7 | Consumidores: quick-doc de `jonesy`, plugin de `ripley`, sección de `dredd` | jonesy, ripley, dredd |

Cada fase con sus pruebas: proyectos de ejemplo en `tests/datos/` (TP plano, biblioteca
estructurada, módulo suelto), prueba de determinismo, prueba de limpieza y una prueba de
los Makefiles que corre `make doc` con un `corbel` falso en el `PATH`.

## 12. Preguntas abiertas

1. ¿`doc/` se versiona en el repositorio del alumno o se ignora (`.gitignore`) y se genera
   en la CI? La especificación permite ambos; la plantilla tiene que elegir uno.
2. ¿El mínimo de cobertura por defecto de `plantilla-TP` es 0 (sólo informar) o la
   cátedra fija uno por TP?
3. ¿`man 3` de funciones del alumno con nombres que chocan con la libc (`strlen` propia)
   se generan igual? Propuesta: sí, con un aviso, porque `man -l` las abre por ruta.
4. ¿Hace falta un objetivo `make man` que copie las páginas a `~/.local/share/man/man3`
   para usar `man arreglo_crear` sin `-l`?
