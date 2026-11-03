# Backend Flask: rutas de la API. Toda la lógica (validar, ordenar, Greedy, PD) vive en Python.
import json
import os
import shutil
import time

from flask import Flask, Response, jsonify, render_template, request, send_from_directory
from werkzeug.utils import safe_join, secure_filename

try:
    from mutagen import File as MutagenFile      # lee metadatos (título, artista, duración)
except ImportError:                              # la app funciona sin mutagen, pero sin leer metadatos
    MutagenFile = None

from algoritmos import (buscar_por_prefijo, generar_playlist_greedy, generar_playlist_pd,
                        ordenar_canciones, tabla_dp)
from experimentos import MAX_TAMANO, TAMANOS_DEFECTO, TIEMPO_MAX_DEFECTO, correr_experimentos
from validaciones import a_entero, validar_cancion, validar_tiempo_max

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "canciones.json")
PLAYLISTS_FILE = os.path.join(BASE_DIR, "data", "playlists.json")
AUDIO_DIR = os.path.join(BASE_DIR, "static", "audio")
EXTENSIONES = {".mp3", ".wav", ".ogg", ".flac"}
TIEMPO_MAX_LIMITE = 86400        # 24 h: la PD usa O(n*W) memoria, hay que acotar W
TABLA_MAX_CANCIONES, TABLA_MAX_COLUMNAS = 12, 40      # límites de la tabla didáctica de PD
PUNTUACION_DEFECTO = 10          # para canciones subidas/escaneadas sin puntuación

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024    # máx. 200 MB por subida
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)


# ---------- Utilidades ----------
def cargar_catalogo():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def guardar_catalogo(catalogo):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(catalogo, f, ensure_ascii=False, indent=2)


def cargar_playlists():
    if not os.path.exists(PLAYLISTS_FILE):
        return []
    with open(PLAYLISTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def guardar_playlists(playlists):
    with open(PLAYLISTS_FILE, "w", encoding="utf-8") as f:
        json.dump(playlists, f, ensure_ascii=False, indent=2)


def leer_caratula(ruta):
    """Imagen incrustada en el audio (MP3/FLAC) o None. Devuelve (bytes, mime)."""
    if MutagenFile is None:
        return None
    try:
        ext = os.path.splitext(ruta)[1].lower()
        if ext == ".mp3":
            from mutagen.id3 import ID3
            for marco in ID3(ruta).values():
                if marco.FrameID == "APIC":
                    return marco.data, marco.mime or "image/jpeg"
        elif ext == ".flac":
            from mutagen.flac import FLAC
            imagenes = FLAC(ruta).pictures
            if imagenes:
                return imagenes[0].data, imagenes[0].mime or "image/jpeg"
    except Exception:
        return None
    return None


def siguiente_id(catalogo):
    return max((c["id"] for c in catalogo), default=0) + 1


def error(mensaje, codigo=400, **extra):
    return jsonify({"ok": False, "error": mensaje, **extra}), codigo


def nombre_seguro(original):
    """Nombre de archivo limpio; si queda inservible (ej. solo símbolos), usa 'audio'."""
    ext = os.path.splitext(original)[1].lower()
    nombre = secure_filename(original)
    if nombre.lower().endswith(ext) and len(nombre) > len(ext):
        return nombre
    return "audio" + ext


def nombre_unico(nombre):
    """Si ya existe en static/audio, agrega _1, _2... para no sobrescribir."""
    base, ext = os.path.splitext(nombre)
    candidato, n = nombre, 1
    while os.path.exists(os.path.join(AUDIO_DIR, candidato)):
        candidato = f"{base}_{n}{ext}"
        n += 1
    return candidato


def leer_metadatos(ruta):
    """Lee título, artista, género y duración (seg) con mutagen. Campos ausentes = None."""
    meta = {"titulo": None, "artista": None, "genero": None, "duracion": None}
    if MutagenFile is None:
        return meta
    try:
        audio = MutagenFile(ruta, easy=True)
    except Exception:
        return meta
    if audio is None:
        return meta
    if audio.info is not None and getattr(audio.info, "length", None):
        meta["duracion"] = max(1, round(audio.info.length))
    for campo, clave in (("titulo", "title"), ("artista", "artist"), ("genero", "genre")):
        try:
            valor = audio.tags.get(clave) if audio.tags else None
        except Exception:
            valor = None
        if valor:
            meta[campo] = str(valor[0]).strip() or None
    return meta


def genero_por_carpeta(carpeta, raiz_escaneo):
    """Si el audio no trae género, usa la subcarpeta de primer nivel: Música/Rock/x.mp3 -> 'Rock'."""
    relativa = os.path.relpath(os.path.abspath(carpeta), raiz_escaneo)
    if relativa == "." or relativa.startswith(".."):
        return "Sin género"
    return relativa.split(os.sep)[0].strip() or "Sin género"


def ejecutar(algoritmo, canciones, tiempo_max):
    """Corre Greedy o PD y mide su tiempo de ejecución."""
    funcion = generar_playlist_greedy if algoritmo == "greedy" else generar_playlist_pd
    inicio = time.perf_counter()
    resultado = funcion(canciones, tiempo_max)
    resultado["tiempo_ejecucion_ms"] = round((time.perf_counter() - inicio) * 1000, 4)
    resultado["algoritmo"] = algoritmo
    return resultado


def catalogo_para_algoritmos(datos):
    """Catálogo que usarán Greedy/PD. Con incluir_ejemplos=false solo entran canciones con audio."""
    catalogo = cargar_catalogo()
    incluir = datos.get("incluir_ejemplos", True)
    if incluir in (False, 0, "false", "False", "0"):
        catalogo = [c for c in catalogo if c.get("archivo")]
    return catalogo


def leer_tiempo_max(datos):
    tiempo, err = validar_tiempo_max(datos.get("tiempo_max"))
    if err is None and tiempo > TIEMPO_MAX_LIMITE:
        err = f"El tiempo máximo no puede superar {TIEMPO_MAX_LIMITE} segundos (24 h)."
    return tiempo, err


# ---------- Rutas ----------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/canciones", methods=["GET"])
def api_listar():
    return jsonify({"ok": True, "canciones": cargar_catalogo()})


@app.route("/api/canciones", methods=["POST"])
def api_registrar():
    datos = request.get_json(silent=True) or {}
    catalogo = cargar_catalogo()
    if datos.get("id") in (None, ""):                    # ID vacío => automático
        datos["id"] = siguiente_id(catalogo)
    cancion, errores = validar_cancion(datos, {c["id"] for c in catalogo})
    if errores:
        return error(" ".join(errores), errores=errores)
    catalogo.append(cancion)
    guardar_catalogo(catalogo)
    return jsonify({"ok": True, "cancion": cancion}), 201


@app.route("/api/canciones/<int:cid>", methods=["PUT"])
def api_editar(cid):
    datos = request.get_json(silent=True) or {}
    catalogo = cargar_catalogo()
    actual = next((c for c in catalogo if c["id"] == cid), None)
    if actual is None:
        return error("La canción no existe.", 404)
    nuevos = {**actual, **{k: v for k, v in datos.items() if k in ("titulo", "artista", "genero", "duracion", "puntuacion")}}
    nuevos["id"] = cid                                   # el ID y el archivo no se modifican
    nuevos["archivo"] = actual.get("archivo")
    cancion, errores = validar_cancion(nuevos, {c["id"] for c in catalogo if c["id"] != cid})
    if errores:
        return error(" ".join(errores), errores=errores)
    catalogo[catalogo.index(actual)] = cancion
    guardar_catalogo(catalogo)
    return jsonify({"ok": True, "cancion": cancion})


@app.route("/api/canciones/<int:cid>", methods=["DELETE"])
def api_eliminar(cid):
    catalogo = cargar_catalogo()
    actual = next((c for c in catalogo if c["id"] == cid), None)
    if actual is None:
        return error("La canción no existe.", 404)
    catalogo.remove(actual)
    guardar_catalogo(catalogo)
    archivo = actual.get("archivo")                      # borra el audio si nadie más lo usa
    if archivo and not any(c.get("archivo") == archivo for c in catalogo):
        ruta = safe_join(AUDIO_DIR, archivo)
        if ruta and os.path.isfile(ruta):
            os.remove(ruta)
    playlists = cargar_playlists()                       # la quita de las playlists guardadas
    if any(cid in pl["ids"] for pl in playlists):
        for pl in playlists:
            pl["ids"] = [i for i in pl["ids"] if i != cid]
        guardar_playlists(playlists)
    return jsonify({"ok": True})


@app.route("/api/buscar", methods=["GET"])
def api_buscar():
    texto = request.args.get("q", "").strip()
    criterio = request.args.get("criterio", "titulo")
    if not texto:
        return error("Escribe un texto para buscar.")
    try:
        resultados, comparaciones = buscar_por_prefijo(cargar_catalogo(), texto, criterio)   # búsqueda binaria
    except ValueError as e:
        return error(str(e))
    return jsonify({"ok": True, "canciones": resultados, "comparaciones": comparaciones})


@app.route("/api/tabla-pd", methods=["POST"])
def api_tabla_pd():
    """Tabla dp paso a paso para un conjunto pequeño de canciones (didáctico / defensa)."""
    datos = request.get_json(silent=True) or {}
    tiempo, err = validar_tiempo_max(datos.get("tiempo_max"))
    if err:
        return error(err)
    crudas = datos.get("canciones")
    if not isinstance(crudas, list) or not 1 <= len(crudas) <= TABLA_MAX_CANCIONES:
        return error(f"Indica entre 1 y {TABLA_MAX_CANCIONES} canciones.")
    canciones = []
    for i, c in enumerate(crudas, 1):
        c = c if isinstance(c, dict) else {}
        cancion, errores = validar_cancion({**c, "id": i, "artista": c.get("artista") or "-"}, set())
        if errores:
            return error(f"Canción {i}: " + " ".join(errores))
        canciones.append(cancion)
    from math import gcd
    paso = tiempo
    for c in canciones:
        paso = gcd(paso, c["duracion"])
    if tiempo // paso > TABLA_MAX_COLUMNAS:
        return error(f"La tabla tendría {tiempo // paso + 1} columnas (máximo {TABLA_MAX_COLUMNAS + 1}). "
                     "Usa duraciones múltiplos entre sí o un tiempo menor.")
    tabla = tabla_dp(canciones, tiempo)
    tabla["canciones"] = [{"titulo": c["titulo"], "duracion": c["duracion"], "puntuacion": c["puntuacion"]}
                          for c in canciones]
    tabla["optimo_verificado"] = generar_playlist_pd(canciones, tiempo)["puntuacion_total"] == tabla["optimo"]
    return jsonify({"ok": True, **tabla})


@app.route("/api/playlists", methods=["GET"])
def api_playlists():
    por_id = {c["id"]: c for c in cargar_catalogo()}
    resultado = []
    for pl in cargar_playlists():
        canciones = [por_id[i] for i in pl["ids"] if i in por_id]
        resultado.append({**pl, "canciones": canciones, "cantidad": len(canciones),
                          "duracion_total": sum(c["duracion"] for c in canciones),
                          "puntuacion_total": sum(c["puntuacion"] for c in canciones)})
    return jsonify({"ok": True, "playlists": resultado})


@app.route("/api/playlists", methods=["POST"])
def api_guardar_playlist():
    datos = request.get_json(silent=True) or {}
    nombre = str(datos.get("nombre") or "").strip()
    if not 1 <= len(nombre) <= 80:
        return error("El nombre de la playlist debe tener entre 1 y 80 caracteres.")
    existentes = {c["id"] for c in cargar_catalogo()}
    ids = [a_entero(i) for i in (datos.get("ids") or [])] if isinstance(datos.get("ids"), list) else []
    ids = [i for i in ids if i in existentes]
    if not ids:
        return error("No hay canciones válidas para guardar.")
    playlists = cargar_playlists()
    nueva = {"id": max((p["id"] for p in playlists), default=0) + 1, "nombre": nombre, "ids": ids,
             "algoritmo": datos.get("algoritmo") if datos.get("algoritmo") in ("greedy", "pd") else None}
    playlists.append(nueva)
    guardar_playlists(playlists)
    return jsonify({"ok": True, "playlist": nueva}), 201


@app.route("/api/playlists/<int:pid>", methods=["DELETE"])
def api_borrar_playlist(pid):
    playlists = cargar_playlists()
    restantes = [p for p in playlists if p["id"] != pid]
    if len(restantes) == len(playlists):
        return error("La playlist no existe.", 404)
    guardar_playlists(restantes)
    return jsonify({"ok": True})


@app.route("/api/m3u", methods=["GET"])
def api_m3u():
    """Exporta una lista de canciones (?ids=1,2,3&nombre=Mi lista) como archivo .m3u (UTF-8)."""
    por_id = {c["id"]: c for c in cargar_catalogo()}
    ids = [a_entero(i) for i in request.args.get("ids", "").split(",") if i.strip()]
    canciones = [por_id[i] for i in ids if i in por_id]
    if not canciones:
        return error("No hay canciones para exportar.")
    lineas = ["#EXTM3U"]
    for c in canciones:
        lineas.append(f"#EXTINF:{c['duracion']},{c['artista']} - {c['titulo']}")
        lineas.append(c.get("archivo") or f"# (sin archivo de audio) {c['titulo']}")
    nombre = secure_filename(request.args.get("nombre", "")) or "playlist"
    return Response("\n".join(lineas) + "\n", mimetype="audio/x-mpegurl; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{nombre}.m3u"'})


@app.route("/api/ordenar", methods=["GET"])
def api_ordenar():
    criterio = request.args.get("criterio", "titulo")
    orden = request.args.get("orden", "asc")
    try:
        ordenadas = ordenar_canciones(cargar_catalogo(), criterio, orden)   # Merge Sort propio
    except ValueError as e:
        return error(str(e))
    return jsonify({"ok": True, "criterio": criterio, "orden": orden, "canciones": ordenadas})


@app.route("/api/playlist", methods=["POST"])
def api_playlist():
    datos = request.get_json(silent=True) or {}
    tiempo, err = leer_tiempo_max(datos)
    if err:
        return error(err)
    algoritmo = datos.get("algoritmo")
    if algoritmo not in ("greedy", "pd"):
        return error("El algoritmo debe ser 'greedy' o 'pd'.")
    resultado = ejecutar(algoritmo, catalogo_para_algoritmos(datos), tiempo)
    return jsonify({"ok": True, **resultado})


@app.route("/api/comparar", methods=["POST"])
def api_comparar():
    datos = request.get_json(silent=True) or {}
    tiempo, err = leer_tiempo_max(datos)
    if err:
        return error(err)
    catalogo = catalogo_para_algoritmos(datos)
    g = ejecutar("greedy", catalogo, tiempo)
    p = ejecutar("pd", catalogo, tiempo)

    ids_g = {c["id"] for c in g["canciones"]}
    ids_p = {c["id"] for c in p["canciones"]}
    tabla = [
        {"algoritmo": "Greedy", "cantidad": g["cantidad"], "duracion_total": g["duracion_total"],
         "puntuacion_total": g["puntuacion_total"], "tiempo_no_utilizado": g["tiempo_no_utilizado"],
         "tiempo_ms": g["tiempo_ejecucion_ms"]},
        {"algoritmo": "Prog. Dinámica", "cantidad": p["cantidad"], "duracion_total": p["duracion_total"],
         "puntuacion_total": p["puntuacion_total"], "tiempo_no_utilizado": p["tiempo_no_utilizado"],
         "tiempo_ms": p["tiempo_ejecucion_ms"]},
    ]
    return jsonify({
        "ok": True, "tiempo_max": tiempo, "tabla": tabla, "greedy": g, "pd": p,
        "difieren": ids_g != ids_p,
        "solo_greedy": [c["titulo"] for c in g["canciones"] if c["id"] not in ids_p],
        "solo_pd": [c["titulo"] for c in p["canciones"] if c["id"] not in ids_g],
        "diferencia_puntos": p["puntuacion_total"] - g["puntuacion_total"],
    })


@app.route("/api/experimentos", methods=["POST"])
def api_experimentos():
    datos = request.get_json(silent=True) or {}
    tamanos = datos.get("tamanos") or list(TAMANOS_DEFECTO)
    if not isinstance(tamanos, list) or not 1 <= len(tamanos) <= 6:
        return error("'tamanos' debe ser una lista de 1 a 6 enteros.")
    tamanos = [a_entero(t) for t in tamanos]
    if any(t is None or not 1 <= t <= MAX_TAMANO for t in tamanos):
        return error(f"Cada tamaño debe ser un entero entre 1 y {MAX_TAMANO}.")
    tiempo, err = (validar_tiempo_max(datos["tiempo_max"]) if "tiempo_max" in datos
                   else (TIEMPO_MAX_DEFECTO, None))[0:2]
    if err:
        return error(err)
    return jsonify({"ok": True, "filas": correr_experimentos(tamanos, tiempo)})


def procesar_audio(archivo, form, individual):
    """Guarda un audio y lo registra. Devuelve (cancion, None) o (None, {"error":..., "detectado":...})."""
    if os.path.splitext(archivo.filename)[1].lower() not in EXTENSIONES:
        return None, {"error": "Formato no permitido. Usa: " + ", ".join(sorted(EXTENSIONES))}
    nombre = nombre_unico(nombre_seguro(archivo.filename))
    ruta = os.path.join(AUDIO_DIR, nombre)
    archivo.save(ruta)

    meta = leer_metadatos(ruta)
    # Con un solo archivo, lo escrito por el usuario manda; con varios, se usan los metadatos
    manual = (lambda k: (form.get(k) or "").strip()) if individual else (lambda k: "")
    titulo = manual("titulo") or meta["titulo"] or (os.path.splitext(archivo.filename)[0] if not individual else None)
    artista = manual("artista") or meta["artista"] or (None if individual else "Desconocido")
    genero = manual("genero") or meta["genero"] or "Sin género"
    duracion = meta["duracion"] or (form.get("duracion") if individual else None)

    faltan = [n for n, v in (("título", titulo), ("artista", artista), ("duración", duracion)) if not v]
    if faltan:
        os.remove(ruta)
        return None, {"error": "Faltan datos: " + ", ".join(faltan) + ". Complétalos y vuelve a enviar.",
                      "detectado": meta}

    catalogo = cargar_catalogo()
    datos = {"id": (form.get("id") if individual else None) or siguiente_id(catalogo),
             "titulo": titulo, "artista": artista, "genero": genero, "duracion": duracion,
             "puntuacion": form.get("puntuacion") or PUNTUACION_DEFECTO, "archivo": nombre}
    cancion, errores = validar_cancion(datos, {c["id"] for c in catalogo})
    if errores:
        os.remove(ruta)
        return None, {"error": " ".join(errores)}
    catalogo.append(cancion)
    guardar_catalogo(catalogo)
    return cancion, None


@app.route("/api/subir-audio", methods=["POST"])
def api_subir_audio():
    archivos = [a for a in request.files.getlist("audio") if a and a.filename]
    if not archivos:
        return error("No se recibió ningún archivo.")
    individual = len(archivos) == 1
    agregadas, fallidos = [], []
    for a in archivos:
        cancion, problema = procesar_audio(a, request.form, individual)
        if cancion:
            agregadas.append(cancion)
        else:
            fallidos.append({"archivo": a.filename, **problema})
    if individual and fallidos:                          # un solo archivo: se devuelve el error tal cual
        return error(fallidos[0]["error"], 422, detectado=fallidos[0].get("detectado"))
    if not agregadas:
        return error("No se pudo agregar ningún archivo.", 400, fallidos=fallidos)
    return jsonify({"ok": True, "cancion": agregadas[0], "canciones": agregadas, "fallidos": fallidos}), 201


@app.route("/api/escanear-carpeta", methods=["POST"])
def api_escanear_carpeta():
    datos = request.get_json(silent=True) or {}
    ruta = str(datos.get("ruta", "")).strip().strip('"')
    if not ruta or not os.path.isdir(ruta):
        return error("La carpeta no existe o la ruta está vacía.")

    catalogo = cargar_catalogo()
    registrados = {c["archivo"] for c in catalogo if c.get("archivo")}
    analizados, agregadas, omitidos = 0, 0, []
    raiz_escaneo = os.path.abspath(ruta)

    for raiz, _, archivos in os.walk(ruta):             # os.walk recorre carpetas y subcarpetas
        for nombre in archivos:
            if os.path.splitext(nombre)[1].lower() not in EXTENSIONES:
                continue
            analizados += 1
            origen = os.path.join(raiz, nombre)
            meta = leer_metadatos(origen)
            if not meta["duracion"]:
                omitidos.append(f"{nombre}: no se pudo leer la duración")
                continue

            if os.path.abspath(raiz) == os.path.abspath(AUDIO_DIR):   # ya está en static/audio
                destino = nombre
                if destino in registrados:
                    omitidos.append(f"{nombre}: ya registrado")
                    continue
            else:                                                      # copiar para poder servirlo
                seguro = nombre_seguro(nombre)
                existente = os.path.join(AUDIO_DIR, seguro)
                if (seguro in registrados and os.path.exists(existente)
                        and os.path.getsize(existente) == os.path.getsize(origen)):
                    omitidos.append(f"{nombre}: ya registrado")
                    continue
                destino = nombre_unico(seguro)
                shutil.copy2(origen, os.path.join(AUDIO_DIR, destino))

            catalogo.append({
                "id": siguiente_id(catalogo),
                "titulo": meta["titulo"] or os.path.splitext(nombre)[0],
                "artista": meta["artista"] or "Desconocido",
                "genero": meta["genero"] or genero_por_carpeta(raiz, raiz_escaneo),
                "duracion": meta["duracion"],
                "puntuacion": PUNTUACION_DEFECTO,
                "archivo": destino,
            })
            registrados.add(destino)
            agregadas += 1

    if agregadas:
        guardar_catalogo(catalogo)
    return jsonify({"ok": True, "analizados": analizados, "agregadas": agregadas, "omitidos": omitidos})


@app.route("/caratula/<path:archivo>")
def servir_caratula(archivo):
    ruta = safe_join(AUDIO_DIR, archivo)
    imagen = leer_caratula(ruta) if ruta and os.path.isfile(ruta) else None
    if imagen is None:
        return error("Sin carátula.", 404)
    return Response(imagen[0], mimetype=imagen[1], headers={"Cache-Control": "max-age=3600"})


@app.route("/audio/<path:archivo>")
def servir_audio(archivo):
    # send_from_directory evita salirse de la carpeta y soporta "seek" (Range) en el reproductor
    return send_from_directory(AUDIO_DIR, archivo)


if __name__ == "__main__":
    app.run(debug=False)
