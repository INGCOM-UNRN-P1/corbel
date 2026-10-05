/** @file lista.h */
#ifndef LISTA_H
#define LISTA_H

/**
 * @brief Lista enlazada de enteros.
 */
typedef struct lista Lista;

/**
 * @brief Crea una lista vacía.
 * @return la lista, o NULL si no hay memoria
 */
Lista *lista_crear(void);

/**
 * @brief [Descripción breve de la función lista_agregar]
 * @param l [Descripción del parámetro l]
 */
void lista_agregar(Lista *l, int valor);

/**
 * @brief Cantidad de elementos.
 * @param lista la lista
 * @return la cantidad
 */
int lista_largo(const Lista *l);

void lista_destruir(Lista *l);
#endif
