"""
Ordenamiento del catálogo: MERGE SORT propio (sin sort() ni sorted()).

Justificación de la elección (frente a Insertion Sort):
  * Tiempo O(n log n) en el peor, mejor y caso promedio; Insertion Sort es O(n^2).
  * Es ESTABLE: canciones con la misma clave conservan su orden relativo
    (útil, p. ej., al ordenar por puntuación y tener muchos empates).
  * Espacio auxiliar O(n), aceptable para un catálogo en memoria.
"""
import unicodedata

CRITERIOS = ("titulo", "artista", "duracion", "puntuacion")


def _clave_texto(texto):
    """Clave para comparar texto sin distinguir mayúsculas ni tildes ('Árbol' < 'Brisa')."""
    sin_tildes = unicodedata.normalize("NFD", str(texto))
    sin_tildes = "".join(ch for ch in sin_tildes if not unicodedata.combining(ch))
    return sin_tildes.casefold()


def _mezclar(izq, der, descendente):
    """Mezcla dos listas ordenadas de pares (clave, elemento). En empate toma la izquierda (estable)."""
    resultado = []
    i = j = 0
    while i < len(izq) and j < len(der):
        k_izq, k_der = izq[i][0], der[j][0]
        tomar_izq = (k_izq >= k_der) if descendente else (k_izq <= k_der)
        if tomar_izq:
            resultado.append(izq[i])
            i += 1
        else:
            resultado.append(der[j])
            j += 1
    resultado.extend(izq[i:])
    resultado.extend(der[j:])
    return resultado


def _ordenar_pares(pares, descendente):
    if len(pares) <= 1:
        return pares
    medio = len(pares) // 2
    izq = _ordenar_pares(pares[:medio], descendente)
    der = _ordenar_pares(pares[medio:], descendente)
    return _mezclar(izq, der, descendente)


def merge_sort(elementos, clave=lambda x: x, descendente=False):
    """Devuelve una lista NUEVA ordenada por clave(elemento). No modifica la original."""
    pares = [(clave(e), e) for e in elementos]       # la clave se calcula una sola vez por elemento
    return [e for _, e in _ordenar_pares(pares, descendente)]


def ordenar_canciones(canciones, criterio="titulo", orden="asc"):
    """Ordena el catálogo por 'titulo', 'artista', 'duracion' o 'puntuacion' (asc/desc)."""
    if criterio not in CRITERIOS:
        raise ValueError("Criterio inválido. Usa: " + ", ".join(CRITERIOS) + ".")
    if orden not in ("asc", "desc"):
        raise ValueError("El orden debe ser 'asc' o 'desc'.")
    if criterio in ("titulo", "artista"):
        clave = lambda c: _clave_texto(c[criterio])
    else:
        clave = lambda c: c[criterio]
    return merge_sort(canciones, clave, descendente=(orden == "desc"))


def esta_ordenado(elementos, clave=lambda x: x, descendente=False):
    """Verificación auxiliar O(n): ¿la lista cumple el orden pedido?"""
    for a, b in zip(elementos, elementos[1:]):
        ka, kb = clave(a), clave(b)
        if (ka < kb) if descendente else (ka > kb):
            return False
    return True
