"""Utilidades compartidas por Greedy y Programación Dinámica."""


def armar_resultado(seleccion, tiempo_max):
    """Construye el diccionario de salida (RF04) a partir de las canciones elegidas."""
    duracion_total = sum(c["duracion"] for c in seleccion)
    puntuacion_total = sum(c["puntuacion"] for c in seleccion)
    return {
        "canciones": seleccion,
        "cantidad": len(seleccion),
        "duracion_total": duracion_total,
        "puntuacion_total": puntuacion_total,
        "tiempo_disponible": tiempo_max,
        "tiempo_no_utilizado": tiempo_max - duracion_total,
    }
