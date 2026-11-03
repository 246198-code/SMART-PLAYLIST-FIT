# 🎧 Smart Playlist — Programación III (Proyecto de la Unidad I)

Aplicación web (Flask + HTML/CSS/JS) que administra un catálogo de canciones, lo ordena con un
**Merge Sort propio** y genera playlists con **Greedy** y **Programación Dinámica (mochila 0/1)**.
Todos los algoritmos se ejecutan en Python (backend); el navegador solo muestra resultados.

## Instrucciones de ejecución
```bash
# 1) (opcional) entorno virtual
python -m venv venv
venv\Scripts\activate          # Windows   |   source venv/bin/activate  (Linux/Mac)

# 2) dependencias
pip install -r requirements.txt

# 3) iniciar la aplicación
python app.py                  # abrir http://127.0.0.1:5000
```
Requiere Python 3.9+. `mutagen` solo se usa para leer título/artista/duración de archivos de audio.

## Estructura
```
app.py                  Rutas Flask (API) y lógica de archivos de audio
validaciones.py         Validación de canciones y del tiempo máximo
experimentos.py         Mediciones de rendimiento (python experimentos.py)
algoritmos/
  ordenamiento.py       Merge Sort estable + ordenar_canciones()
  greedy.py             Heurística puntuación/duración
  dinamica.py           Mochila 0/1 (estados, casos base, transición, reconstrucción) + tabla didáctica
  busqueda.py           Búsqueda binaria por prefijo (título / artista)
data/canciones.json     Catálogo inicial (24 canciones)
templates/index.html    Interfaz     static/css, static/js    Estilos y cliente (solo consume la API)
static/audio/           4 tonos de prueba generados + audios que subas o escanees
tests/test_algoritmos.py  40 casos de prueba
```

## Casos de prueba
```bash
python -m unittest -v
```
Incluye: ejemplo del enunciado (Greedy = 16, PD = 22), comparación con `sorted()` (solo para verificar),
estabilidad, PD contra fuerza bruta en 150 casos aleatorios, PD ≥ Greedy, validaciones y endpoints.

## API
| Método | Ruta | Función |
|---|---|---|
| GET | `/` | Interfaz principal |
| GET / POST | `/api/canciones` | Obtener / registrar canciones |
| PUT / DELETE | `/api/canciones/<id>` | Editar / eliminar una canción |
| GET | `/api/buscar?q=&criterio=titulo\|artista` | Búsqueda binaria por prefijo |
| POST | `/api/tabla-pd` | Tabla dp paso a paso (máx. 12 canciones) |
| GET / POST / DELETE | `/api/playlists[/<id>]` | Playlists guardadas (data/playlists.json) |
| GET | `/api/m3u?ids=1,2,3&nombre=` | Exportar playlist como .m3u |
| GET | `/caratula/<archivo>` | Carátula incrustada en el audio (MP3/FLAC) |
| GET | `/api/ordenar?criterio=titulo\|artista\|duracion\|puntuacion&orden=asc\|desc` | Catálogo ordenado (Merge Sort) |
| POST | `/api/playlist` `{tiempo_max, algoritmo: "greedy"\|"pd"}` | Generar playlist |
| POST | `/api/comparar` `{tiempo_max}` | Comparar Greedy y PD |
| POST | `/api/experimentos` `{tamanos:[50,500,2000]}` | Mediciones con catálogos sintéticos |
| POST | `/api/subir-audio` | Subir uno o varios audios a la vez (lee metadatos con mutagen) |
| POST | `/api/escanear-carpeta` `{ruta}` | Analizar carpeta y subcarpetas buscando .mp3/.wav/.ogg/.flac |

## Catálogo: «Con audio» y «Ejemplos»
El catálogo se divide en dos pestañas: **Con audio** (reproducibles) y **Ejemplos** (datos de prueba sin archivo).
Al generar o comparar playlists, la casilla «Incluir ejemplos» decide si los ejemplos participan.
Con ✏️ se edita una canción (por ejemplo, su puntuación o género). Al escanear carpetas, si el audio no trae
género se usa el nombre de la subcarpeta de primer nivel (`Música/Rock/tema.mp3` → Rock).

## Funciones adicionales
- **Reproductor:** vinilo animado, ecualizador, cola, aleatorio (S), repetir (R: no/todas/una), atajos de teclado
  (Espacio, ←/→, ↑/↓), carátula del MP3/FLAC en el vinilo y colores de la página según el género.
- **Playlists:** guardar la generada (💾), reproducir, exportar `.m3u` y eliminar.
- **Búsqueda binaria** por prefijo de título o artista sobre el catálogo ordenado (muestra las comparaciones).
- **Tabla dp paso a paso:** muestra `dp[i][w]` y marca el camino de la reconstrucción (útil para la defensa).
- **Experimentos:** gráfico de tiempos (escala logarítmica) con n = 50 … 2000.

## Demostración sugerida
1. Ordenar el catálogo por puntuación (descendente) haciendo clic en el encabezado de la tabla.
2. Poner **900 s** y pulsar **Comparar ambos**: Greedy obtiene 85 puntos y PD 89 (elige otra canción).
3. Pulsar **▶ Reproducir playlist** con las canciones de prueba (las 4 de género "Prueba" tienen audio).
4. Escanear una carpeta propia de música y volver a generar la playlist.
5. Ejecutar **Experimentos de rendimiento**.

> Los audios `tono_*.wav` son tonos sintéticos creados para la demostración (sin derechos de autor).
