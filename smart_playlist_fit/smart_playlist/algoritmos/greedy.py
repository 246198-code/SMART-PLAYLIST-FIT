"""
Estrategia GREEDY (heurística) para armar la playlist.

Criterio voraz: prioridad_i = puntuacion_i / duracion_i (se usa Fraction: sin errores de redondeo).
Pasos:
  1. Ordenar las canciones de MAYOR a MENOR prioridad (con nuestro Merge Sort).
  2. Recorrerlas una sola vez: se incorpora la canción si su duración <= tiempo restante.
  3. Cada canción se usa como máximo una vez.

Complejidad: O(n log n) en tiempo (dominado por el ordenamiento), O(n) en espacio.
No garantiza el óptimo (ver Programación Dinámica).
"""
from fractions import Fraction

from ._comun import armar_resultado
from .ordenamiento import merge_sort


def generar_playlist_greedy(canciones, tiempo_max):
    por_prioridad = merge_sort(
        canciones, clave=lambda c: Fraction(c["puntuacion"], c["duracion"]), descendente=True)
    restante = tiempo_max
    seleccion = []
    for c in por_prioridad:
        if c["duracion"] <= restante:
            restante -= c["duracion"]
            seleccion.append({**c, "prioridad": round(c["puntuacion"] / c["duracion"], 4)})
    return armar_resultado(seleccion, tiempo_max)
