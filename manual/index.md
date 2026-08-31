---
title: "Manual de Referencia: corbel"
subtitle: "Corbel — Generador de Documentación de APIs, TDAs y Verificación de Snippets C"
author: "Cátedra de Algoritmos y Programación"
date: "2026-08-31"
---

(manual-corbel)=
# Corbel — Generador de Documentación de APIs, TDAs y Verificación de Snippets C

````{abstract}
**Rol en el ecosistema:** Generación de documentación técnica a partir de encabezados C y validación de que todos los ejemplos de código compilen y ejecuten sin errores.
````

---

(manual-corbel-proposito)=
## 1. Propósito y Filosofía Pedagógica

La herramienta **`corbel`** forma parte del ecosistema oficial de software de la cátedra. Su diseño sigue principios pedagógicos rigurosos:

1. **Evidencia Técnica Directa**: Todo diagnóstico se fundamenta en la norma ISO C (C11/C23), en el modelo de memoria del sistema o en convenciones arquitectónicas formales.
2. **Acción Correctiva Concreta**: Cada advertencia incluye la prescripción técnica inmediata para resolver el defecto sin recurrir a conjeturas.
3. **Autonomía del Estudiante**: Facilita la autoevaluación local antes de la entrega final del trabajo práctico.
4. **Objetividad Docente**: Estandariza la corrección automática eliminando discrepancias subjetivas en la evaluación.

---

(manual-corbel-instalacion)=
## 2. Instalación y Diagnóstico del Entorno

````{important}
Asegurate de contar con el compilador GCC/Clang y las librerías del sistema instaladas antes de ejecutar `corbel`.
````

Para comprobar el estado de salud de tu entorno de trabajo y las dependencias auxiliares:

````{code-block} bash
# Comprobación de dependencias del sistema
corbel doctor
````

Si se detecta la falta de alguna utilidad (como `gdb`, `valgrind`, `clang-format` o `typst`), el comando indicará el paquete exacto a instalar según tu distribución GNU/Linux o entorno MSYS2.

---

(manual-corbel-comandos)=
## 3. Referencia Completa de Comandos CLI

A continuación se detallan los subcomandos principales disponibles en `corbel`:

| Sintaxis del Comando | Descripción y Efecto |
| :--- | :--- |
| `corbel build include/ -o docs/` | Genera el sitio web o manual Markdown a partir de los headers C. |
| `corbel test-snippets docs/` | Extrae y compila todos los bloques de código C de la documentación. |
| `corbel check-coverage include/` | Calcula el porcentaje de funciones y structs documentadas. |
| `corbel doctor` | Verifica la disponibilidad de compiladores y formateadores. |

````{tip}
Podés agregar el flag `--json` a la mayoría de los comandos para exportar resultados en formato estructurado o `--md` para generar reportes Markdown para el informe de entrega.
````

---

(manual-corbel-tutorial)=
## 4. Tutorial Paso a Paso con Ejemplos Reales

### Caso de Estudio

Considerá el siguiente fragmento de código representativo:

````{code-block} c
:linenos:
/**
 * @brief Inserta un elemento al inicio de la lista enlazada.
 * @param lista Puntero a la estructura TDA Lista.
 * @param dato Puntero genérico al dato a almacenar.
 * @return true si se insertó con éxito, false ante fallo de memoria.
 * @code
 * t_lista *l = lista_crear();
 * int x = 42;
 * assert(lista_insertar_inicio(l, &x) == true);
 * @endcode
 */
bool lista_insertar_inicio(t_lista *lista, void *dato);
````

### Ejecución de la Herramienta

Ejecutá el análisis desde tu terminal:

````{code-block} bash
corbel build include/ -o docs/
````

### Salida Obtenida en Consola

````{code-block} text
[✓] 14 funciones parseadas en include/lista.h (Cobertura: 100%)
[✓] 6 snippets de código extraídos de la documentación.
[✓] Compilación de snippets: 6/6 PASS (GCC -std=c11 -Werror)
[✓] Documentación generada exitosamente en docs/index.html
````

````{note}
Prestá atención a la explicación pedagógica generada: la herramienta no solo señala la línea del problema, sino que explica la causa raíz y el impacto en memoria o arquitectura.
````

---

(manual-corbel-ejercicios)=
## 5. Ejercicios Prácticos y Desafíos

Practicá el uso avanzado de **`corbel`** resolviendo los siguientes ejercicios:

````{exercise} Desafío 1: Generación de Manual de TDA
Generar la documentación Markdown de `include/tda_cola.h`.

**Instrucción de ejecución:**
```bash
corbel build include/tda_cola.h -o docs/cola/
```
````

````{solution} Desafío 1
```bash
corbel build include/tda_cola.h -o docs/cola/
# Verificá que la operación concluya exitosamente con código de salida 0.
```
````

````{exercise} Desafío 2: Verificación de Snippets de Código
Comprobar que los ejemplos en los comentarios compilan sin warnings.

**Instrucción de ejecución:**
```bash
corbel test-snippets docs/cola/
```
````

````{solution} Desafío 2
```bash
corbel test-snippets docs/cola/
# Revisá el archivo generado o el informe en terminal para confirmar la resolución del problema.
```
````

````{exercise} Desafío 3: Auditoría de Cobertura de Documentación
Verificar que ninguna función pública carezca de descripción de parámetros.

**Instrucción de ejecución:**
```bash
corbel check-coverage include/
```
````

````{solution} Desafío 3
```bash
corbel check-coverage include/
# Comprobá que la salida confirme la ausencia de advertencias o errores pendientes.
```
````

---

(manual-corbel-makefile)=
## 6. Integración en el Flujo de Trabajo y Makefile

Para incorporar `corbel` de forma automática a tu flujo de desarrollo, agregá la siguiente regla en el `Makefile` de tu proyecto:

````{code-block} makefile
check-corbel:
	@echo "=== Ejecutando verificación con corbel ==="
	corbel check src/ include/

.PHONY: check-corbel
````

Ejecutá `make check-corbel` antes de cada commit para asegurar que tu código conserve el estado de aprobación.
