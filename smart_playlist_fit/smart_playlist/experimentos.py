"""
Experimentos de rendimiento (informe: "resultados experimentales").
Uso por consola:  python experimentos.py        (también se expone en POST /api/experimentos)
"""
import random
import time

from algoritmos import generar_playlist_greedy, generar_playlist_pd, ordenar_canciones
from algoritmos.ordenamiento import esta_ordenado

TAMANOS_DEFECTO = (50, 100, 250, 500, 1000, 2000)
TIEMPO_MAX_DEFECTO = 1800      # 30 minutos
MAX_TAMANO = 5000


def catalogo_sintetico(n, semilla=42):
    rng = random.Random(semilla)
    return [{"id": i, "titulo": f"Cancion {rng.randint(1, 10**6)}", "artista": f"Artista {rng.randint(1, 60)}",
             "genero": "Prueba", "duracion": rng.randint(120, 420), "puntuacion": rng.randint(1, 20),
             "archivo": None} for i in range(1, n + 1)]


def _medir(funcion, *args):
    inicio = time.perf_counter()
    resultado = funcion(*args)
    return resultado, round((time.perf_counter() - inicio) * 1000, 3)


def correr_experimentos(tamanos=TAMANOS_DEFECTO, tiempo_max=TIEMPO_MAX_DEFECTO, semilla=42):
    filas = []
    for n in tamanos:
        cat = catalogo_sintetico(n, semilla)
        ordenado, t_orden = _medir(ordenar_canciones, cat, "puntuacion", "desc")
        g, t_g = _medir(generar_playlist_greedy, cat, tiempo_max)
        p, t_p = _medir(generar_playlist_pd, cat, tiempo_max)
        filas.append({
            "n": n, "tiempo_max": tiempo_max,
            "orden_ms": t_orden, "orden_correcto": esta_ordenado(ordenado, lambda c: c["puntuacion"], True),
            "greedy_ms": t_g, "greedy_puntos": g["puntuacion_total"], "greedy_canciones": g["cantidad"],
            "pd_ms": t_p, "pd_puntos": p["puntuacion_total"], "pd_canciones": p["cantidad"],
            "diferencia_puntos": p["puntuacion_total"] - g["puntuacion_total"],
        })
    return filas


if __name__ == "__main__":
    print(f"{'n':>6} {'MergeSort ms':>13} {'Greedy ms':>10} {'PD ms':>10} {'Greedy pts':>11} {'PD pts':>7} {'dif':>4}")
    for f in correr_experimentos():
        print(f"{f['n']:>6} {f['orden_ms']:>13} {f['greedy_ms']:>10} {f['pd_ms']:>10} "
              f"{f['greedy_puntos']:>11} {f['pd_puntos']:>7} {f['diferencia_puntos']:>4}")
