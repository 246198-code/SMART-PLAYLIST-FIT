"""
PROGRAMACIÓN DINÁMICA: mochila 0/1 (solución ÓPTIMA).

Modelo:  max  sum(p_i * x_i)   sujeto a   sum(d_i * x_i) <= C,   x_i in {0,1}

a) ESTADOS:      dp[i][w] = máxima puntuación usando solo las primeras i canciones
                 con un tiempo disponible w (0 <= w <= C).
b) CASOS BASE:   dp[0][w] = 0 (sin canciones no hay puntos) y dp[i][0] = 0 (duraciones > 0).
c) TRANSICIÓN:   dp[i][w] = dp[i-1][w]                              si d_i > w
                 dp[i][w] = max(dp[i-1][w], dp[i-1][w-d_i] + p_i)   si d_i <= w
                 (no tomar la canción i  /  tomarla una sola vez)
d) VALOR ÓPTIMO: dp[n][C].
e) RECUPERACIÓN: se guarda, para cada (i, w), si tomar la canción i mejoró el valor.
                 Se recorre desde (n, C) hacia atrás: si tomar[i][w] -> la canción i está en la
                 solución y w -= d_i.
f) La interfaz muestra el resultado (ver /api/playlist y /api/comparar).

Optimizaciones (no cambian el resultado):
  * C se reduce a min(C, suma de duraciones): más tiempo del necesario no aporta nada.
  * Todas las duraciones y C se dividen por su MCD (si las canciones duran múltiplos de 5 s,
    la tabla es 5 veces más pequeña).
  * Se usa un único arreglo dp (se actualiza w de mayor a menor) + una matriz de bits "tomar".

Complejidad: tiempo O(n * C'), espacio O(C') para dp + O(n * C') bytes para reconstruir
(C' = capacidad reducida).
"""
from math import gcd

from ._comun import armar_resultado


def generar_playlist_pd(canciones, tiempo_max):
    candidatas = [c for c in canciones if c["duracion"] <= tiempo_max]   # las demás nunca caben
    if not candidatas:
        return armar_resultado([], tiempo_max)

    paso = 0
    for c in candidatas:
        paso = gcd(paso, c["duracion"])
    capacidad = min(tiempo_max, sum(c["duracion"] for c in candidatas)) // paso
    duraciones = [c["duracion"] // paso for c in candidatas]

    dp = [0] * (capacidad + 1)                                  # casos base: todo en 0
    tomar = []                                                  # tomar[i][w] = 1 si se toma la canción i
    for c, d in zip(candidatas, duraciones):
        p = c["puntuacion"]
        fila = bytearray(capacidad + 1)
        for w in range(capacidad, d - 1, -1):                   # de mayor a menor: cada canción se usa 1 vez
            valor = dp[w - d] + p
            if valor > dp[w]:
                dp[w] = valor
                fila[w] = 1
        tomar.append(fila)

    seleccion, w = [], capacidad                                # recuperar la solución
    for i in range(len(candidatas) - 1, -1, -1):
        if tomar[i][w]:
            seleccion.append(candidatas[i])
            w -= duraciones[i]
    seleccion.reverse()                                         # vuelve al orden del catálogo
    return armar_resultado([dict(c) for c in seleccion], tiempo_max)


def tabla_dp(canciones, tiempo_max):
    """
    Versión DIDÁCTICA: construye la tabla completa dp[i][w] para mostrarla en la interfaz
    (se usa con catálogos pequeños). Aplica exactamente las mismas transiciones que arriba.
    Las columnas son múltiplos de 'paso' = MCD(duraciones, tiempo_max), así la tabla es compacta.
    """
    n = len(canciones)
    paso = tiempo_max
    for c in canciones:
        paso = gcd(paso, c["duracion"])
    capacidad = tiempo_max // paso
    duraciones = [c["duracion"] // paso for c in canciones]

    dp = [[0] * (capacidad + 1) for _ in range(n + 1)]            # casos base: fila 0 y columna 0 en 0
    for i in range(1, n + 1):
        d, p = duraciones[i - 1], canciones[i - 1]["puntuacion"]
        for w in range(capacidad + 1):
            dp[i][w] = dp[i - 1][w]                                # no tomar la canción i
            if d <= w:
                dp[i][w] = max(dp[i][w], dp[i - 1][w - d] + p)     # tomarla (una sola vez)

    elegidas, camino, w = [], [(n, capacidad)], capacidad         # reconstrucción desde (n, C)
    for i in range(n, 0, -1):
        if dp[i][w] != dp[i - 1][w]:                               # cambió: la canción i está en la solución
            elegidas.append(i - 1)
            w -= duraciones[i - 1]
        camino.append((i - 1, w))
    elegidas.reverse()
    return {
        "paso": paso, "capacidad": capacidad, "columnas": [w * paso for w in range(capacidad + 1)],
        "filas": [dp[i] for i in range(n + 1)], "optimo": dp[n][capacidad],
        "elegidas": elegidas, "camino": [list(par) for par in camino],
    }
