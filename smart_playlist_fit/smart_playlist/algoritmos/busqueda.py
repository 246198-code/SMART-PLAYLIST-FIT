"""
BÚSQUEDA BINARIA sobre el catálogo ya ordenado (con nuestro Merge Sort).

Se busca por PREFIJO del título o del artista: la búsqueda binaria encuentra la primera posición
cuya clave es >= al texto buscado (cota inferior) en O(log n) y luego se recorren solo las
coincidencias consecutivas. Total: O(log n + k), con k = cantidad de resultados.
"""
from .ordenamiento import _clave_texto, ordenar_canciones


def buscar_por_prefijo(canciones, texto, criterio="titulo"):
    """Devuelve (coincidencias, comparaciones_realizadas). Ignora mayúsculas y tildes."""
    if criterio not in ("titulo", "artista"):
        raise ValueError("Solo se puede buscar por 'titulo' o 'artista'.")
    ordenadas = ordenar_canciones(canciones, criterio, "asc")
    objetivo = _clave_texto(texto.strip())
    bajo, alto, comparaciones = 0, len(ordenadas), 0
    while bajo < alto:                                   # cota inferior: primera clave >= objetivo
        medio = (bajo + alto) // 2
        comparaciones += 1
        if _clave_texto(ordenadas[medio][criterio]) < objetivo:
            bajo = medio + 1
        else:
            alto = medio
    resultados = []
    i = bajo
    while i < len(ordenadas) and _clave_texto(ordenadas[i][criterio]).startswith(objetivo):
        resultados.append(ordenadas[i])
        i += 1
    return resultados, comparaciones
