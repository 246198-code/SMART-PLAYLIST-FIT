"""Validación de entradas (sección 6 del enunciado y RF03)."""
import os
import re

DURACION_MAX = 86400
_ENTERO = re.compile(r"^[+-]?\d+$")


def a_entero(valor):
    """Convierte 5, 5.0 o ' 5 ' a int; devuelve None si no es un entero válido."""
    if isinstance(valor, bool):
        return None
    if isinstance(valor, int):
        return valor
    if isinstance(valor, float) and valor.is_integer():
        return int(valor)
    if isinstance(valor, str) and _ENTERO.match(valor.strip()):
        return int(valor.strip())
    return None


def validar_cancion(datos, ids_existentes):
    """Devuelve (cancion, []) si es válida o (None, [errores])."""
    errores = []
    cid = a_entero(datos.get("id"))
    if cid is None or cid <= 0:
        errores.append("El ID debe ser un entero positivo.")
    elif cid in ids_existentes:
        errores.append(f"El ID {cid} ya existe.")

    titulo = str(datos.get("titulo") or "").strip()
    artista = str(datos.get("artista") or "").strip()
    if not titulo:
        errores.append("El título es obligatorio.")
    if not artista:
        errores.append("El artista es obligatorio.")
    if len(titulo) > 200 or len(artista) > 200:
        errores.append("Título y artista admiten máximo 200 caracteres.")

    duracion = a_entero(datos.get("duracion"))
    if duracion is None or duracion <= 0:
        errores.append("La duración debe ser un entero positivo (segundos).")
    elif duracion > DURACION_MAX:
        errores.append(f"La duración no puede superar {DURACION_MAX} segundos.")

    puntuacion = a_entero(datos.get("puntuacion"))
    if puntuacion is None or not 1 <= puntuacion <= 20:
        errores.append("La puntuación debe ser un entero entre 1 y 20.")

    archivo = datos.get("archivo")
    archivo = os.path.basename(str(archivo)).strip() if archivo else None

    if errores:
        return None, errores
    return {
        "id": cid, "titulo": titulo, "artista": artista,
        "genero": str(datos.get("genero") or "").strip() or "Sin género",
        "duracion": duracion, "puntuacion": puntuacion, "archivo": archivo or None,
    }, []


def validar_tiempo_max(valor):
    """RF03: el tiempo debe ser un entero positivo. Devuelve (tiempo, None) o (None, mensaje)."""
    tiempo = a_entero(valor)
    if tiempo is None:
        return None, "El tiempo máximo debe ser un número entero (segundos)."
    if tiempo <= 0:
        return None, "El tiempo máximo debe ser positivo."
    return tiempo, None
