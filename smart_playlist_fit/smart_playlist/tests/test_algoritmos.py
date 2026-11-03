"""Casos de prueba. Ejecutar:  python -m unittest -v   (desde la carpeta del proyecto)
Aquí SÍ se permite sorted() y itertools: solo para VERIFICAR los algoritmos propios."""
import itertools
import json
import os
import random
import shutil
import tempfile
import unittest

import app as app_modulo
from algoritmos import (buscar_por_prefijo, generar_playlist_greedy, generar_playlist_pd, merge_sort,
                        ordenar_canciones, tabla_dp)
from validaciones import validar_cancion, validar_tiempo_max


def cancion(i, dur, punt, titulo=None, artista="X"):
    return {"id": i, "titulo": titulo or f"T{i}", "artista": artista, "genero": "G",
            "duracion": dur, "puntuacion": punt, "archivo": None}


# Ejemplo de la sección 7 del enunciado (A: 2 min/6, B: 4 min/10, C: 6 min/12; 10 minutos)
EJEMPLO = [cancion(1, 120, 6, "A"), cancion(2, 240, 10, "B"), cancion(3, 360, 12, "C")]


class TestOrdenamiento(unittest.TestCase):
    def test_lista_vacia_y_un_elemento(self):
        self.assertEqual(merge_sort([]), [])
        self.assertEqual(merge_sort([5]), [5])

    def test_coincide_con_sorted_en_listas_aleatorias(self):
        rng = random.Random(1)
        for _ in range(50):
            datos = [rng.randint(-50, 50) for _ in range(rng.randint(0, 60))]
            self.assertEqual(merge_sort(datos), sorted(datos))
            self.assertEqual(merge_sort(datos, descendente=True), sorted(datos, reverse=True))

    def test_no_modifica_la_lista_original(self):
        datos = [3, 1, 2]
        merge_sort(datos)
        self.assertEqual(datos, [3, 1, 2])

    def test_es_estable(self):
        datos = [(1, "a"), (0, "b"), (1, "c"), (0, "d"), (1, "e")]
        asc = merge_sort(datos, clave=lambda x: x[0])
        desc = merge_sort(datos, clave=lambda x: x[0], descendente=True)
        self.assertEqual([x[1] for x in asc], ["b", "d", "a", "c", "e"])
        self.assertEqual([x[1] for x in desc], ["a", "c", "e", "b", "d"])

    def test_todos_los_criterios_asc_y_desc(self):
        rng = random.Random(7)
        cat = [cancion(i, rng.randint(60, 400), rng.randint(1, 20), f"Tema {rng.randint(1, 30)}",
                       f"Art {rng.randint(1, 8)}") for i in range(1, 41)]
        for criterio in ("titulo", "artista", "duracion", "puntuacion"):
            for orden in ("asc", "desc"):
                res = ordenar_canciones(cat, criterio, orden)
                claves = [c[criterio] for c in res]
                self.assertEqual(claves, sorted(claves, reverse=(orden == "desc")))
                self.assertEqual(len(res), len(cat))

    def test_titulos_con_tildes_y_mayusculas(self):
        cat = [cancion(1, 100, 5, "brisa"), cancion(2, 100, 5, "Árbol"), cancion(3, 100, 5, "Zeta")]
        self.assertEqual([c["titulo"] for c in ordenar_canciones(cat, "titulo")], ["Árbol", "brisa", "Zeta"])

    def test_criterio_u_orden_invalido(self):
        with self.assertRaises(ValueError):
            ordenar_canciones(EJEMPLO, "genero")
        with self.assertRaises(ValueError):
            ordenar_canciones(EJEMPLO, "titulo", "arriba")


class TestGreedy(unittest.TestCase):
    def test_ejemplo_del_enunciado(self):
        r = generar_playlist_greedy(EJEMPLO, 600)
        self.assertEqual([c["titulo"] for c in r["canciones"]], ["A", "B"])
        self.assertEqual((r["duracion_total"], r["puntuacion_total"], r["tiempo_no_utilizado"]), (360, 16, 240))

    def test_nunca_excede_el_tiempo_ni_repite(self):
        rng = random.Random(3)
        cat = [cancion(i, rng.randint(30, 300), rng.randint(1, 20)) for i in range(1, 60)]
        for T in (1, 100, 500, 3000, 100000):
            r = generar_playlist_greedy(cat, T)
            ids = [c["id"] for c in r["canciones"]]
            self.assertLessEqual(r["duracion_total"], T)
            self.assertEqual(len(ids), len(set(ids)))

    def test_ninguna_cancion_cabe(self):
        r = generar_playlist_greedy(EJEMPLO, 60)
        self.assertEqual((r["cantidad"], r["puntuacion_total"], r["tiempo_no_utilizado"]), (0, 0, 60))

    def test_catalogo_vacio(self):
        self.assertEqual(generar_playlist_greedy([], 100)["cantidad"], 0)


class TestProgramacionDinamica(unittest.TestCase):
    def test_ejemplo_del_enunciado(self):
        r = generar_playlist_pd(EJEMPLO, 600)
        self.assertEqual(sorted(c["titulo"] for c in r["canciones"]), ["B", "C"])
        self.assertEqual((r["duracion_total"], r["puntuacion_total"], r["tiempo_no_utilizado"]), (600, 22, 0))

    def test_es_optimo_contra_fuerza_bruta(self):
        rng = random.Random(11)
        for _ in range(150):
            n = rng.randint(0, 10)
            cat = [cancion(i, rng.randint(1, 30), rng.randint(1, 20)) for i in range(1, n + 1)]
            T = rng.randint(1, 80)
            mejor = 0
            for k in range(n + 1):
                for comb in itertools.combinations(cat, k):
                    if sum(c["duracion"] for c in comb) <= T:
                        mejor = max(mejor, sum(c["puntuacion"] for c in comb))
            r = generar_playlist_pd(cat, T)
            self.assertEqual(r["puntuacion_total"], mejor)
            self.assertLessEqual(r["duracion_total"], T)
            ids = [c["id"] for c in r["canciones"]]
            self.assertEqual(len(ids), len(set(ids)))
            self.assertEqual(r["puntuacion_total"], sum(c["puntuacion"] for c in r["canciones"]))

    def test_pd_nunca_pierde_contra_greedy(self):
        rng = random.Random(5)
        for _ in range(100):
            cat = [cancion(i, rng.randint(20, 400), rng.randint(1, 20)) for i in range(1, rng.randint(1, 30))]
            T = rng.randint(1, 2000)
            self.assertGreaterEqual(generar_playlist_pd(cat, T)["puntuacion_total"],
                                    generar_playlist_greedy(cat, T)["puntuacion_total"])

    def test_tiempo_mayor_que_todo_el_catalogo(self):
        r = generar_playlist_pd(EJEMPLO, 10**6)
        self.assertEqual(r["cantidad"], 3)
        self.assertEqual(r["tiempo_no_utilizado"], 10**6 - 720)

    def test_sin_canciones_que_quepan(self):
        self.assertEqual(generar_playlist_pd(EJEMPLO, 10)["cantidad"], 0)
        self.assertEqual(generar_playlist_pd([], 10)["cantidad"], 0)


class TestBusquedaBinaria(unittest.TestCase):
    cat = [cancion(1, 100, 5, "Brisa"), cancion(2, 100, 5, "Árbol"), cancion(3, 100, 5, "brasas"),
           cancion(4, 100, 5, "Zeta"), cancion(5, 100, 5, "Bruma")]

    def test_prefijo_sin_importar_tildes_ni_mayusculas(self):
        res, _ = buscar_por_prefijo(self.cat, "br")
        self.assertEqual(sorted(c["titulo"] for c in res), ["Brisa", "Bruma", "brasas"])
        res, _ = buscar_por_prefijo(self.cat, "arb")
        self.assertEqual([c["titulo"] for c in res], ["Árbol"])

    def test_sin_resultados_y_criterio_invalido(self):
        self.assertEqual(buscar_por_prefijo(self.cat, "xyz")[0], [])
        with self.assertRaises(ValueError):
            buscar_por_prefijo(self.cat, "a", "duracion")

    def test_coincide_con_busqueda_lineal_y_hace_pocas_comparaciones(self):
        rng = random.Random(9)
        cat = [cancion(i, 100, 5, "".join(rng.choice("abcde") for _ in range(4))) for i in range(1, 1025)]
        for texto in ("a", "bc", "dd", "eeee", "zz"):
            res, comparaciones = buscar_por_prefijo(cat, texto)
            esperado = [c for c in cat if c["titulo"].startswith(texto)]
            self.assertEqual(sorted(c["id"] for c in res), sorted(c["id"] for c in esperado))
            self.assertLessEqual(comparaciones, 11)          # log2(1024) + 1


class TestTablaDP(unittest.TestCase):
    def test_ejemplo_del_enunciado(self):
        t = tabla_dp(EJEMPLO, 600)
        self.assertEqual((t["paso"], t["capacidad"], t["optimo"]), (120, 5, 22))
        self.assertEqual(t["columnas"], [0, 120, 240, 360, 480, 600])
        self.assertEqual(t["elegidas"], [1, 2])               # B y C (índices 1 y 2)
        self.assertEqual(t["filas"][0], [0] * 6)              # caso base
        self.assertEqual(t["camino"][0], [3, 5])              # arranca en dp[n][C]

    def test_optimo_igual_al_de_generar_playlist_pd(self):
        rng = random.Random(21)
        for _ in range(60):
            cat = [cancion(i, 10 * rng.randint(1, 8), rng.randint(1, 20)) for i in range(1, rng.randint(1, 8))]
            T = 10 * rng.randint(1, 30)
            self.assertEqual(tabla_dp(cat, T)["optimo"], generar_playlist_pd(cat, T)["puntuacion_total"])


class TestValidaciones(unittest.TestCase):
    base = {"id": 1, "titulo": "T", "artista": "A", "duracion": 100, "puntuacion": 10}

    def test_cancion_valida_acepta_texto_numerico(self):
        c, err = validar_cancion({**self.base, "duracion": "120", "puntuacion": "20"}, set())
        self.assertEqual(err, [])
        self.assertEqual((c["duracion"], c["puntuacion"], c["genero"]), (120, 20, "Sin género"))

    def test_rechaza_datos_invalidos(self):
        casos = [{"duracion": 0}, {"duracion": -5}, {"duracion": "abc"}, {"duracion": 12.5},
                 {"puntuacion": 0}, {"puntuacion": 21}, {"titulo": " "}, {"artista": ""}, {"id": 0}]
        for cambio in casos:
            c, err = validar_cancion({**self.base, **cambio}, set())
            self.assertIsNone(c, cambio)
            self.assertTrue(err, cambio)

    def test_id_duplicado(self):
        c, err = validar_cancion(self.base, {1})
        self.assertIsNone(c)
        self.assertIn("ya existe", err[0])

    def test_tiempo_max(self):
        self.assertEqual(validar_tiempo_max("600"), (600, None))
        for malo in (0, -1, "x", None, True, 3.5):
            self.assertIsNone(validar_tiempo_max(malo)[0], malo)


class TestAPI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.original = (app_modulo.DATA_FILE, app_modulo.AUDIO_DIR, app_modulo.PLAYLISTS_FILE)
        app_modulo.PLAYLISTS_FILE = os.path.join(self.tmp, "playlists.json")
        app_modulo.DATA_FILE = os.path.join(self.tmp, "canciones.json")
        app_modulo.AUDIO_DIR = os.path.join(self.tmp, "audio")
        os.makedirs(app_modulo.AUDIO_DIR)
        with open(app_modulo.DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(EJEMPLO, f)
        self.cliente = app_modulo.app.test_client()

    def tearDown(self):
        app_modulo.DATA_FILE, app_modulo.AUDIO_DIR, app_modulo.PLAYLISTS_FILE = self.original
        shutil.rmtree(self.tmp)

    def test_interfaz_y_catalogo(self):
        self.assertEqual(self.cliente.get("/").status_code, 200)
        self.assertEqual(len(self.cliente.get("/api/canciones").get_json()["canciones"]), 3)

    def test_ordenar(self):
        r = self.cliente.get("/api/ordenar?criterio=duracion&orden=desc").get_json()
        self.assertEqual([c["titulo"] for c in r["canciones"]], ["C", "B", "A"])
        self.assertEqual(self.cliente.get("/api/ordenar?criterio=xx").status_code, 400)

    def test_registrar_cancion(self):
        r = self.cliente.post("/api/canciones", json={"titulo": "N", "artista": "Z", "duracion": "90", "puntuacion": 7})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.get_json()["cancion"]["id"], 4)
        malo = self.cliente.post("/api/canciones", json={"titulo": "N", "artista": "Z", "duracion": 0, "puntuacion": 7})
        self.assertEqual(malo.status_code, 400)

    def test_playlist_y_validacion_de_tiempo(self):
        g = self.cliente.post("/api/playlist", json={"tiempo_max": 600, "algoritmo": "greedy"}).get_json()
        p = self.cliente.post("/api/playlist", json={"tiempo_max": "600", "algoritmo": "pd"}).get_json()
        self.assertEqual((g["puntuacion_total"], p["puntuacion_total"]), (16, 22))
        for tiempo in (0, -10, "abc", None, 10**7):
            r = self.cliente.post("/api/playlist", json={"tiempo_max": tiempo, "algoritmo": "pd"})
            self.assertEqual(r.status_code, 400, tiempo)
        self.assertEqual(self.cliente.post("/api/playlist", json={"tiempo_max": 60, "algoritmo": "x"}).status_code, 400)

    def test_comparar(self):
        r = self.cliente.post("/api/comparar", json={"tiempo_max": 600}).get_json()
        self.assertTrue(r["difieren"])
        self.assertEqual((r["solo_greedy"], r["solo_pd"], r["diferencia_puntos"]), (["A"], ["C"], 6))
        self.assertEqual(len(r["tabla"]), 2)

    def test_editar_cancion(self):
        r = self.cliente.put("/api/canciones/2", json={"titulo": "B2", "genero": "Rock", "puntuacion": "15"})
        self.assertEqual(r.status_code, 200)
        c = r.get_json()["cancion"]
        self.assertEqual((c["id"], c["titulo"], c["genero"], c["puntuacion"], c["duracion"]), (2, "B2", "Rock", 15, 240))
        self.assertEqual(self.cliente.put("/api/canciones/2", json={"puntuacion": 99}).status_code, 400)
        self.assertEqual(self.cliente.put("/api/canciones/77", json={"titulo": "x"}).status_code, 404)
        guardado = self.cliente.get("/api/canciones").get_json()["canciones"]
        self.assertEqual([x["titulo"] for x in guardado if x["id"] == 2], ["B2"])

    def test_incluir_ejemplos_en_playlist(self):
        # el catálogo de prueba no tiene audio: sin ejemplos no hay nada que elegir
        r = self.cliente.post("/api/playlist", json={"tiempo_max": 600, "algoritmo": "pd", "incluir_ejemplos": False}).get_json()
        self.assertEqual(r["cantidad"], 0)
        r = self.cliente.post("/api/comparar", json={"tiempo_max": 600, "incluir_ejemplos": True}).get_json()
        self.assertEqual(r["pd"]["puntuacion_total"], 22)

    def test_escaneo_usa_la_subcarpeta_como_genero(self):
        origen = os.path.join(os.path.dirname(app_modulo.__file__), "static", "audio", "tono_1.wav")
        raiz = os.path.join(self.tmp, "Musica")
        os.makedirs(os.path.join(raiz, "Rock", "Sub"))
        shutil.copy(origen, os.path.join(raiz, "Rock", "Sub", "a.wav"))
        shutil.copy(origen, os.path.join(raiz, "suelto.wav"))
        r = self.cliente.post("/api/escanear-carpeta", json={"ruta": raiz}).get_json()
        self.assertEqual(r["agregadas"], 2)
        generos = {c["archivo"]: c["genero"] for c in self.cliente.get("/api/canciones").get_json()["canciones"] if c["archivo"]}
        self.assertEqual(generos["a.wav"], "Rock")
        self.assertEqual(generos["suelto.wav"], "Sin género")

    def test_eliminar_cancion_y_su_audio(self):
        with open(os.path.join(app_modulo.AUDIO_DIR, "x.wav"), "wb") as f:
            f.write(b"RIFF")
        with open(app_modulo.DATA_FILE, encoding="utf-8") as f:
            cat = json.load(f)
        cat[0]["archivo"] = "x.wav"
        with open(app_modulo.DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(cat, f)
        self.assertEqual(self.cliente.delete("/api/canciones/1").status_code, 200)
        self.assertFalse(os.path.exists(os.path.join(app_modulo.AUDIO_DIR, "x.wav")))
        self.assertEqual(len(self.cliente.get("/api/canciones").get_json()["canciones"]), 2)
        self.assertEqual(self.cliente.delete("/api/canciones/1").status_code, 404)

    def test_buscar(self):
        r = self.cliente.get("/api/buscar?q=b&criterio=titulo").get_json()
        self.assertEqual([c["titulo"] for c in r["canciones"]], ["B"])
        self.assertGreaterEqual(r["comparaciones"], 1)
        self.assertEqual(self.cliente.get("/api/buscar?q=").status_code, 400)
        self.assertEqual(self.cliente.get("/api/buscar?q=a&criterio=duracion").status_code, 400)

    def test_tabla_pd_api(self):
        cuerpo = {"tiempo_max": 600, "canciones": [{"titulo": "A", "duracion": "120", "puntuacion": "6"},
                  {"titulo": "B", "duracion": 240, "puntuacion": 10}, {"titulo": "C", "duracion": 360, "puntuacion": 12}]}
        r = self.cliente.post("/api/tabla-pd", json=cuerpo).get_json()
        self.assertEqual((r["optimo"], r["elegidas"], r["optimo_verificado"]), (22, [1, 2], True))
        self.assertEqual(self.cliente.post("/api/tabla-pd", json={**cuerpo, "tiempo_max": 0}).status_code, 400)
        grande = {"tiempo_max": 100000, "canciones": [{"titulo": "A", "duracion": 7, "puntuacion": 5}]}
        self.assertEqual(self.cliente.post("/api/tabla-pd", json=grande).status_code, 400)
        self.assertEqual(self.cliente.post("/api/tabla-pd", json={"tiempo_max": 60, "canciones": []}).status_code, 400)

    def test_playlists_guardadas_y_m3u(self):
        if True:
            r = self.cliente.post("/api/playlists", json={"nombre": "Mi lista", "ids": [2, 3, 99], "algoritmo": "pd"})
            self.assertEqual(r.status_code, 201)
            self.assertEqual(r.get_json()["playlist"]["ids"], [2, 3])
            self.assertEqual(self.cliente.post("/api/playlists", json={"nombre": "", "ids": [1]}).status_code, 400)
            self.assertEqual(self.cliente.post("/api/playlists", json={"nombre": "x", "ids": [99]}).status_code, 400)
            lista = self.cliente.get("/api/playlists").get_json()["playlists"]
            self.assertEqual((lista[0]["cantidad"], lista[0]["puntuacion_total"]), (2, 22))
            m3u = self.cliente.get("/api/m3u?ids=1,2&nombre=Mi lista")
            texto = m3u.get_data(as_text=True)
            self.assertTrue(texto.startswith("#EXTM3U\n#EXTINF:120,X - A"))
            self.assertIn("attachment", m3u.headers["Content-Disposition"])
            self.assertEqual(self.cliente.get("/api/m3u?ids=99").status_code, 400)
            self.cliente.delete("/api/canciones/2")                      # se quita de la playlist guardada
            self.assertEqual(self.cliente.get("/api/playlists").get_json()["playlists"][0]["cantidad"], 1)
            self.assertEqual(self.cliente.delete(f"/api/playlists/{lista[0]['id']}").status_code, 200)
            self.assertEqual(self.cliente.delete("/api/playlists/77").status_code, 404)

    def test_subida_multiple_de_audios(self):
        import io
        origen = os.path.join(os.path.dirname(app_modulo.__file__), "static", "audio")
        with open(os.path.join(origen, "tono_1.wav"), "rb") as a, open(os.path.join(origen, "tono_2.wav"), "rb") as b:
            datos = {"audio": [(io.BytesIO(a.read()), "uno.wav"), (io.BytesIO(b.read()), "dos.wav"),
                               (io.BytesIO(b"no es audio"), "malo.txt")]}
        r = self.cliente.post("/api/subir-audio", data=datos, content_type="multipart/form-data")
        j = r.get_json()
        self.assertEqual((r.status_code, len(j["canciones"]), len(j["fallidos"])), (201, 2, 1))
        self.assertEqual(sorted(c["titulo"] for c in j["canciones"]), ["dos", "uno"])
        self.assertTrue(all(c["duracion"] > 0 and c["archivo"] for c in j["canciones"]))

    def test_caratula_incrustada(self):
        from mutagen.id3 import APIC, ID3
        ruta = os.path.join(app_modulo.AUDIO_DIR, "c.mp3")
        open(ruta, "wb").close()
        etiquetas = ID3()
        etiquetas.add(APIC(encoding=3, mime="image/png", type=3, desc="", data=b"\x89PNGfake"))
        etiquetas.save(ruta)
        r = self.cliente.get("/caratula/c.mp3")
        self.assertEqual((r.status_code, r.mimetype, r.data), (200, "image/png", b"\x89PNGfake"))
        self.assertEqual(self.cliente.get("/caratula/no-existe.mp3").status_code, 404)
        self.assertEqual(self.cliente.get("/caratula/../app.py").status_code, 404)

    def test_experimentos(self):
        r = self.cliente.post("/api/experimentos", json={"tamanos": [10, 30]}).get_json()
        self.assertEqual(len(r["filas"]), 2)
        self.assertTrue(all(f["orden_correcto"] and f["pd_puntos"] >= f["greedy_puntos"] for f in r["filas"]))
        self.assertEqual(self.cliente.post("/api/experimentos", json={"tamanos": [0]}).status_code, 400)


if __name__ == "__main__":
    unittest.main()
