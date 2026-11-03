// Solo consume la API y pinta resultados.
// NO ordena ni calcula nada: Merge Sort, Greedy y PD se ejecutan en Python (Flask).

const $ = (id) => document.getElementById(id);

let catalogo = [];          // último catálogo recibido del servidor
let cola = [];              // canciones del reproductor
let indice = -1;            // posición actual en la cola
let vista = "audio";        // pestaña del catálogo: "audio" | "ejemplos"
let filtroIds = null;       // IDs devueltos por la búsqueda binaria (null = sin filtro)
let ultimaPlaylist = null;  // última playlist generada (para guardarla / exportarla)
let aleatorio = false;
let repetir = 0;            // 0 = no, 1 = toda la cola, 2 = una canción
let editandoId = null;      // ID de la canción que se está editando (null = registrando)

// ---------- Utilidades de presentación ----------
const esc = (t) => String(t).replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function mmss(seg) {                        // 354 -> "5:54" (solo formato de texto)
  seg = Math.floor(seg || 0);
  return `${Math.floor(seg / 60)}:${String(seg % 60).padStart(2, "0")}`;
}

function aviso(texto, tipo = "ok") {
  const el = $("aviso");
  el.textContent = texto;
  el.className = `aviso ${tipo} visible`;
  clearTimeout(aviso.temporizador);
  aviso.temporizador = setTimeout(() => el.classList.remove("visible"), 4500);
}

// ---------- Comunicación con la API ----------
async function api(url, opciones = {}) {
  const resp = await fetch(url, opciones);
  const datos = await resp.json();
  if (!resp.ok || datos.ok === false) {
    const err = new Error(datos.error || "Error en el servidor");
    err.datos = datos;
    throw err;
  }
  return datos;
}

const postJSON = (url, cuerpo) =>
  api(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cuerpo) });

// ---------- Catálogo ----------
async function cargarCatalogo() {
  try {
    const r = await api(`/api/ordenar?criterio=${$("selCriterio").value}&orden=${$("selOrden").value}`);
    catalogo = r.canciones;                 // ya viene ordenado desde Python
    pintarCatalogo();
  } catch (e) { aviso(e.message, "error"); }
}

function pintarCatalogo() {
  const visibles = filtroIds ? catalogo.filter((c) => filtroIds.has(c.id)) : catalogo;
  const conAudio = visibles.filter((c) => c.archivo);
  const ejemplos = visibles.filter((c) => !c.archivo);
  const lista = vista === "audio" ? conAudio : ejemplos;
  $("tabAudio").textContent = `🎵 Con audio (${conAudio.length})`;
  $("tabEjemplos").textContent = `📋 Ejemplos (${ejemplos.length})`;
  $("tabAudio").classList.toggle("activa", vista === "audio");
  $("tabEjemplos").classList.toggle("activa", vista === "ejemplos");
  $("notaVista").textContent = vista === "audio"
    ? "Canciones con archivo de audio: se pueden reproducir."
    : "Canciones de ejemplo sin audio: sirven para probar el ordenamiento, Greedy y PD.";

  $("tbodyCatalogo").innerHTML = lista.length ? lista.map((c) => `
    <tr>
      <td>${c.id}</td>
      <td>${esc(c.titulo)}</td>
      <td>${esc(c.artista)}</td>
      <td>${esc(c.genero)}</td>
      <td>${mmss(c.duracion)} <small class="muted">(${c.duracion}s)</small></td>
      <td><span class="badge">${c.puntuacion}</span></td>
      <td>${c.archivo ? `<button class="mini" data-play="${c.id}">▶</button>` : '<span class="muted">—</span>'}</td>
      <td><button class="editar" data-edit="${c.id}" title="Editar">✏️</button>
          <button class="editar" data-del="${c.id}" title="Eliminar">🗑️</button></td>
    </tr>`).join("") : '<tr><td colspan="8" class="muted">No hay canciones en esta sección.</td></tr>';
  $("contador").textContent = `${catalogo.length} canciones`;

  document.querySelectorAll("th[data-criterio]").forEach((th) => {
    th.classList.remove("asc", "desc");
    if (th.dataset.criterio === $("selCriterio").value) th.classList.add($("selOrden").value);
  });
}

document.querySelectorAll(".pestana").forEach((b) =>
  b.addEventListener("click", () => { vista = b.dataset.vista; pintarCatalogo(); }));

$("selCriterio").addEventListener("change", cargarCatalogo);
$("selOrden").addEventListener("change", cargarCatalogo);

document.querySelectorAll("th[data-criterio]").forEach((th) =>
  th.addEventListener("click", () => {
    const sel = $("selCriterio"), ord = $("selOrden");
    if (sel.value === th.dataset.criterio) ord.value = ord.value === "asc" ? "desc" : "asc";
    else { sel.value = th.dataset.criterio; ord.value = "asc"; }
    cargarCatalogo();
  }));

// ---------- Búsqueda binaria (se ejecuta en Python) ----------
async function buscar() {
  const q = $("textoBusqueda").value.trim();
  if (!q) { limpiarBusqueda(); return; }
  try {
    const r = await api(`/api/buscar?q=${encodeURIComponent(q)}&criterio=${$("buscarEn").value}`);
    filtroIds = new Set(r.canciones.map((c) => c.id));
    $("notaBusqueda").textContent = `${r.canciones.length} coincidencia(s) · búsqueda binaria: ${r.comparaciones} comparaciones sobre ${catalogo.length} canciones.`;
    $("btnLimpiarBusqueda").hidden = false;
    pintarCatalogo();
  } catch (e) { aviso(e.message, "error"); }
}
function limpiarBusqueda() {
  filtroIds = null;
  $("textoBusqueda").value = "";
  $("notaBusqueda").textContent = "";
  $("btnLimpiarBusqueda").hidden = true;
  pintarCatalogo();
}
$("btnBuscar").addEventListener("click", buscar);
$("btnLimpiarBusqueda").addEventListener("click", limpiarBusqueda);
$("textoBusqueda").addEventListener("keydown", (e) => { if (e.key === "Enter") buscar(); });

// 🗑 en una fila: elimina la canción (y su audio si nadie más lo usa)
$("tbodyCatalogo").addEventListener("click", async (e) => {
  const boton = e.target.closest("[data-del]");
  if (!boton) return;
  const c = catalogo.find((x) => x.id === Number(boton.dataset.del));
  if (!c || !confirm(`¿Eliminar «${c.titulo}»?${c.archivo ? " También se borrará su archivo de audio." : ""}`)) return;
  try {
    await api(`/api/canciones/${c.id}`, { method: "DELETE" });
    if (editandoId === c.id) salirDeEdicion();
    cola = cola.filter((x) => x.id !== c.id);
    aviso("Canción eliminada");
    await cargarCatalogo();
    cargarPlaylistsGuardadas();
  } catch (err) { aviso(err.message, "error"); }
});

// ✏ en una fila: carga la canción en el formulario para editarla
$("tbodyCatalogo").addEventListener("click", (e) => {
  const boton = e.target.closest("[data-edit]");
  if (!boton) return;
  const c = catalogo.find((x) => x.id === Number(boton.dataset.edit));
  if (!c) return;
  editandoId = c.id;
  const f = $("formCancion").elements;
  ["id", "titulo", "artista", "genero", "duracion", "puntuacion"].forEach((k) => { f[k].value = c[k]; });
  f.id.readOnly = true;
  $("tituloForm").textContent = `Editar canción #${c.id}`;
  $("btnGuardar").textContent = "Guardar cambios";
  $("btnCancelarEdicion").hidden = false;
  $("formCancion").scrollIntoView({ behavior: "smooth", block: "center" });
});

function salirDeEdicion() {
  editandoId = null;
  $("formCancion").reset();
  $("formCancion").elements.id.readOnly = false;
  $("tituloForm").textContent = "Registrar canción";
  $("btnGuardar").textContent = "Guardar";
  $("btnCancelarEdicion").hidden = true;
}
$("btnCancelarEdicion").addEventListener("click", salirDeEdicion);

// ▶ en una fila: la cola serán las canciones del catálogo que tengan audio
$("tbodyCatalogo").addEventListener("click", (e) => {
  const boton = e.target.closest("[data-play]");
  if (!boton) return;
  const conAudio = catalogo.filter((c) => c.archivo);
  cargarCola(conAudio, conAudio.findIndex((c) => c.id === Number(boton.dataset.play)));
});

// ---------- Registrar canción ----------
$("formCancion").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const datos = Object.fromEntries(new FormData(e.target));
    if (editandoId !== null) {
      await api(`/api/canciones/${editandoId}`, {
        method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(datos) });
      aviso("Canción actualizada");
      salirDeEdicion();
    } else {
      await postJSON("/api/canciones", datos);
      aviso("Canción registrada");
      e.target.reset();
    }
    cargarCatalogo();
  } catch (err) { aviso(err.message, "error"); }
});

// ---------- Subir audio ----------
$("formAudio").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const r = await api("/api/subir-audio", { method: "POST", body: new FormData(e.target) });
    const malos = r.fallidos || [];
    aviso(r.canciones.length === 1 && !malos.length ? `Subida: ${r.cancion.titulo}`
      : `${r.canciones.length} audio(s) agregados` + (malos.length ? ` · ${malos.length} con error: ${malos.map((m) => m.archivo).join(", ")}` : ""),
      malos.length ? "error" : "ok");
    e.target.reset();
    cargarCatalogo();
  } catch (err) {
    const d = err.datos && err.datos.detectado;       // metadatos parciales: autocompletar
    if (d) {
      ["titulo", "artista", "genero", "duracion"].forEach((campo) => {
        if (d[campo]) e.target.elements[campo].value = d[campo];
      });
    }
    aviso(err.message, "error");
  }
});

// ---------- Escanear carpeta ----------
$("formEscanear").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const r = await postJSON("/api/escanear-carpeta", { ruta: $("rutaCarpeta").value });
    $("resEscaneo").innerHTML =
      `<p>Analizados: <b>${r.analizados}</b> · Agregados: <b>${r.agregadas}</b> · Omitidos: <b>${r.omitidos.length}</b></p>` +
      (r.omitidos.length ? `<ul>${r.omitidos.map((o) => `<li>${esc(o)}</li>`).join("")}</ul>` : "");
    aviso(`${r.agregadas} canciones agregadas`);
    cargarCatalogo();
  } catch (err) { aviso(err.message, "error"); }
});

// ---------- Generar playlist ----------
$("tiempoMax").addEventListener("input", (e) => {
  $("tiempoHint").textContent = `= ${mmss(Number(e.target.value))}`;
});

function tablaCanciones(lista) {
  return `<div class="tabla-wrap"><table>
    <thead><tr><th>#</th><th>Título</th><th>Artista</th><th>Duración</th><th>Punt.</th></tr></thead>
    <tbody>${lista.map((c, i) => `
      <tr><td>${i + 1}</td><td>${esc(c.titulo)}</td><td>${esc(c.artista)}</td>
      <td>${mmss(c.duracion)} <small class="muted">(${c.duracion}s)</small></td>
      <td><span class="badge">${c.puntuacion}</span></td></tr>`).join("")}
    </tbody></table></div>`;
}

function pintarPlaylist(r) {
  if (r.cantidad === 0) {
    $("resPlaylist").innerHTML = `<p class="muted">Ninguna canción cabe en ${r.tiempo_no_utilizado} segundos.</p>`;
    return;
  }
  $("resPlaylist").innerHTML = `
    <div class="chips">
      <div class="chip"><b>${r.cantidad}</b><span>canciones</span></div>
      <div class="chip"><b>${mmss(r.duracion_total)}</b><span>${r.duracion_total}s usados</span></div>
      <div class="chip"><b>${r.puntuacion_total}</b><span>puntos</span></div>
      <div class="chip"><b>${r.tiempo_no_utilizado}s</b><span>sin usar</span></div>
      <div class="chip"><b>${r.tiempo_ejecucion_ms} ms</b><span>${r.algoritmo === "pd" ? "PD" : "GREEDY"}</span></div>
    </div>
    ${tablaCanciones(r.canciones)}
    <p class="fila-botones">
      <button class="btn" id="btnReproducirPl">▶ Reproducir playlist</button>
      <button class="btn sec" id="btnGuardarPl">💾 Guardar</button>
      <a class="btn sec" id="btnM3uPl" href="/api/m3u?ids=${r.canciones.map((c) => c.id).join(",")}&nombre=playlist-${r.algoritmo}" download>⬇ .m3u</a>
    </p>`;
  ultimaPlaylist = r;
  $("btnReproducirPl").onclick = () => cargarCola(r.canciones, 0);
  $("btnGuardarPl").onclick = async () => {
    const nombre = (prompt("Nombre de la playlist:", `Playlist ${r.algoritmo === "pd" ? "PD" : "Greedy"} ${mmss(r.tiempo_disponible)}`) || "").trim();
    if (!nombre) return;
    try {
      await postJSON("/api/playlists", { nombre, ids: r.canciones.map((c) => c.id), algoritmo: r.algoritmo });
      aviso("Playlist guardada");
      cargarPlaylistsGuardadas();
    } catch (err) { aviso(err.message, "error"); }
  };
}

$("formPlaylist").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const r = await postJSON("/api/playlist", { tiempo_max: $("tiempoMax").value, algoritmo: $("algoritmo").value, incluir_ejemplos: $("incluirEjemplos").checked });
    pintarPlaylist(r);
  } catch (err) { aviso(err.message, "error"); }
});

// ---------- Comparar Greedy vs PD ----------
$("btnComparar").addEventListener("click", async () => {
  try {
    const r = await postJSON("/api/comparar", { tiempo_max: $("tiempoMax").value, incluir_ejemplos: $("incluirEjemplos").checked });
    const filas = r.tabla.map((f) => `
      <tr><td>${f.algoritmo}</td><td>${f.cantidad}</td><td>${f.duracion_total}s</td>
      <td><b>${f.puntuacion_total}</b></td><td>${f.tiempo_no_utilizado}s</td><td>${f.tiempo_ms} ms</td></tr>`).join("");
    const nombres = (alg) => r[alg].canciones.map((c) => esc(c.titulo)).join(", ") || "—";

    $("resComparacion").innerHTML = `
      <table>
        <thead><tr><th>Algoritmo</th><th>Nº canciones</th><th>Duración usada</th><th>Puntuación</th><th>Sin usar</th><th>Tiempo</th></tr></thead>
        <tbody>${filas}</tbody>
      </table>
      <p><b>Greedy eligió:</b> ${nombres("greedy")}</p>
      <p><b>PD eligió:</b> ${nombres("pd")}</p>
      ${r.difieren
        ? `<p class="gana">Eligieron distinto. PD obtiene ${r.diferencia_puntos} punto(s) más.</p>
           <p class="muted"><span class="solo-g">Solo Greedy: ${esc(r.solo_greedy.join(", ") || "—")}</span> · <span class="solo-p">Solo PD: ${esc(r.solo_pd.join(", ") || "—")}</span></p>`
        : `<p class="muted">Ambos algoritmos eligieron las mismas canciones.</p>`}
      <p><button class="btn sec" id="btnPlG">▶ Cola Greedy</button> <button class="btn sec" id="btnPlP">▶ Cola PD</button></p>`;
    $("cardComparacion").hidden = false;
    $("btnPlG").onclick = () => cargarCola(r.greedy.canciones, 0);
    $("btnPlP").onclick = () => cargarCola(r.pd.canciones, 0);
  } catch (err) { aviso(err.message, "error"); }
});

// ---------- Playlists guardadas ----------
async function cargarPlaylistsGuardadas() {
  try {
    const r = await api("/api/playlists");
    if (!r.playlists.length) {
      $("resPlaylistsGuardadas").innerHTML = '<p class="muted">Aún no guardaste ninguna. Genera una playlist y pulsa 💾 Guardar.</p>';
      return;
    }
    $("resPlaylistsGuardadas").innerHTML = `<div class="lista-pl">${r.playlists.map((p) => `
      <div class="item-pl">
        <div><b>${esc(p.nombre)}</b><br><small class="muted">${p.cantidad} canciones · ${mmss(p.duracion_total)} · ${p.puntuacion_total} pts${p.algoritmo ? " · " + (p.algoritmo === "pd" ? "PD" : "Greedy") : ""}</small></div>
        <div class="acc">
          <button data-pl-play="${p.id}" title="Reproducir">▶</button>
          <a href="/api/m3u?ids=${p.canciones.map((c) => c.id).join(",")}&nombre=${encodeURIComponent(p.nombre)}" download title="Exportar .m3u">⬇</a>
          <button data-pl-del="${p.id}" title="Eliminar">🗑️</button>
        </div>
      </div>`).join("")}</div>`;
    $("resPlaylistsGuardadas").onclick = async (e) => {
      const play = e.target.closest("[data-pl-play]");
      const del = e.target.closest("[data-pl-del]");
      if (play) cargarCola(r.playlists.find((p) => p.id === Number(play.dataset.plPlay)).canciones, 0);
      if (del && confirm("¿Eliminar esta playlist?")) {
        try { await api(`/api/playlists/${del.dataset.plDel}`, { method: "DELETE" }); cargarPlaylistsGuardadas(); }
        catch (err) { aviso(err.message, "error"); }
      }
    };
  } catch (e) { aviso(e.message, "error"); }
}

// ---------- Tabla dp (didáctica) ----------
$("formTablaPD").addEventListener("submit", async (e) => {
  e.preventDefault();
  const canciones = $("tablaCanciones").value.split("\n").map((l) => l.trim()).filter(Boolean).map((linea) => {
    const partes = linea.split(",");
    const puntuacion = partes.pop();
    const duracion = partes.pop();
    return { titulo: partes.join(",").trim(), duracion, puntuacion };
  });
  try {
    const t = await postJSON("/api/tabla-pd", { canciones, tiempo_max: $("tablaTiempo").value });
    const camino = new Set(t.camino.map(([i, w]) => `${i}-${w}`));
    const elegidas = new Set(t.elegidas.map((i) => i + 1));
    const cabecera = t.columnas.map((w) => `<th>${w}</th>`).join("");
    const filas = t.filas.map((fila, i) => {
      const etiqueta = i === 0 ? "0 · sin canciones"
        : `${i} · ${esc(t.canciones[i - 1].titulo)} (${t.canciones[i - 1].duracion}s, ${t.canciones[i - 1].puntuacion} pts)`;
      return `<tr><th class="${elegidas.has(i) ? "elegida" : ""}" style="text-align:left">${etiqueta}${elegidas.has(i) ? " ✔" : ""}</th>
        ${fila.map((v, w) => `<td class="${camino.has(`${i}-${w}`) ? "camino" : ""}">${v}</td>`).join("")}</tr>`;
    }).join("");
    $("resTablaPD").innerHTML = `
      <div class="tabla-wrap"><table class="tabla-dp">
        <thead><tr><th>i · canción \\ w (segundos)</th>${cabecera}</tr></thead><tbody>${filas}</tbody></table></div>
      <p><b>Valor óptimo dp[n][C] = ${t.optimo}</b> · canciones elegidas: ${t.elegidas.map((i) => esc(t.canciones[i].titulo)).join(", ") || "ninguna"}
         ${t.optimo_verificado ? '· <span class="solo-p">✔ coincide con la PD de la playlist</span>' : ""}</p>
      <p class="nota">Las celdas rosadas son el camino de la reconstrucción: se parte de dp[n][C]; si dp[i][w] ≠ dp[i−1][w], la canción i se tomó y w baja en su duración. Columnas en pasos de ${t.paso}s (MCD).</p>`;
  } catch (err) { aviso(err.message, "error"); }
});

// ---------- Reproductor ----------
const audio = $("audio");

// Barras del visualizador (solo decoración con CSS)
for (let i = 0; i < 28; i++) {
  const barra = document.createElement("span");
  barra.style.setProperty("--d", `${(0.4 + Math.random() * 0.7).toFixed(2)}s`);
  barra.style.setProperty("--r", `${(Math.random() * -1).toFixed(2)}s`);
  $("ecualizador").appendChild(barra);
}

function cargarCola(canciones, inicio) {
  if (!canciones.length) { aviso("No hay canciones para reproducir", "error"); return; }
  cola = canciones;
  reproducirIndice(Math.max(inicio, 0));
}

function pintarCola() {
  $("cola").innerHTML = cola.length
    ? cola.map((c, i) => `<li data-i="${i}" class="${i === indice ? "actual" : ""}">${i + 1}. ${esc(c.titulo)} — ${esc(c.artista)}</li>`).join("")
    : '<li class="muted">Vacía</li>';
}

function aplicarTema(genero) {                       // el color de la página cambia con el género
  const raiz = document.documentElement.style;
  if (!genero || genero === "Sin género") { raiz.removeProperty("--a1"); raiz.removeProperty("--a2"); return; }
  let h = 0;
  for (const ch of genero.toLowerCase()) h = (h * 31 + ch.charCodeAt(0)) % 360;
  raiz.setProperty("--a1", `hsl(${h} 80% 62%)`);
  raiz.setProperty("--a2", `hsl(${(h + 55) % 360} 80% 60%)`);
}

function mostrarCaratula(c) {                        // imagen incrustada en el audio, si la tiene
  const etiqueta = $("pInicial");
  etiqueta.style.backgroundImage = "";
  etiqueta.textContent = c.titulo.charAt(0).toUpperCase();
  if (!c.archivo) return;
  const img = new Image();
  img.onload = () => {
    if (cola[indice] !== c) return;
    etiqueta.style.backgroundImage = `url("${img.src}")`;
    etiqueta.textContent = "";
  };
  img.src = `/caratula/${encodeURIComponent(c.archivo)}`;
}

function siguiente(automatico) {                     // respeta aleatorio y repetir
  if (!cola.length) return;
  if (automatico && repetir === 2) { audio.currentTime = 0; audio.play().catch(() => {}); return; }
  if (aleatorio && cola.length > 1) {
    let n; do { n = Math.floor(Math.random() * cola.length); } while (n === indice);
    reproducirIndice(n);
  } else if (indice + 1 < cola.length) reproducirIndice(indice + 1);
  else if (repetir === 1) reproducirIndice(0);
}

function reproducirIndice(i) {
  if (i < 0 || i >= cola.length) return;
  indice = i;
  const c = cola[i];
  aplicarTema(c.genero);
  mostrarCaratula(c);
  $("pTitulo").textContent = c.titulo;
  $("pArtista").textContent = c.artista;
  if (c.archivo) {
    $("pAviso").textContent = "";
    audio.src = `/audio/${encodeURIComponent(c.archivo)}`;
    audio.play().catch(() => {});
  } else {                                           // canción del catálogo sin audio real
    audio.pause();
    audio.removeAttribute("src");
    audio.load();
    $("pAviso").textContent = "Esta canción no tiene archivo de audio";
  }
  pintarCola();
}

$("btnPlay").addEventListener("click", () => {
  if (!audio.src) { if (cola.length) reproducirIndice(Math.max(indice, 0)); return; }
  audio.paused ? audio.play() : audio.pause();
});
$("btnNext").addEventListener("click", () => siguiente(false));
$("btnPrev").addEventListener("click", () => {
  if (audio.currentTime > 3) audio.currentTime = 0;   // si ya avanzó, reinicia la canción
  else reproducirIndice(indice - 1);
});
$("cola").addEventListener("click", (e) => {
  const li = e.target.closest("li[data-i]");
  if (li) reproducirIndice(Number(li.dataset.i));
});

function alternarAleatorio() {
  aleatorio = !aleatorio;
  $("btnShuffle").classList.toggle("activo", aleatorio);
  aviso(aleatorio ? "Aleatorio activado" : "Aleatorio desactivado");
}
function alternarRepetir() {
  repetir = (repetir + 1) % 3;
  $("btnRepeat").classList.toggle("activo", repetir > 0);
  $("btnRepeat").textContent = repetir === 2 ? "🔂" : "🔁";
  aviso(["Repetir: desactivado", "Repetir: toda la cola", "Repetir: una canción"][repetir]);
}
$("btnShuffle").addEventListener("click", alternarAleatorio);
$("btnRepeat").addEventListener("click", alternarRepetir);

document.addEventListener("keydown", (e) => {        // atajos (no actúan al escribir en un campo)
  if ((e.target.closest && e.target.closest("input, textarea, select")) || e.ctrlKey || e.altKey || e.metaKey) return;
  const cambiarVolumen = (d) => { audio.volume = Math.min(1, Math.max(0, audio.volume + d)); $("volumen").value = audio.volume; };
  if (e.code === "Space") { e.preventDefault(); $("btnPlay").click(); }
  else if (e.code === "ArrowRight") siguiente(false);
  else if (e.code === "ArrowLeft") $("btnPrev").click();
  else if (e.code === "ArrowUp") { e.preventDefault(); cambiarVolumen(0.05); }
  else if (e.code === "ArrowDown") { e.preventDefault(); cambiarVolumen(-0.05); }
  else if (e.key.toLowerCase() === "s") alternarAleatorio();
  else if (e.key.toLowerCase() === "r") alternarRepetir();
});

$("volumen").addEventListener("input", (e) => { audio.volume = e.target.value; });
audio.volume = 0.8;

$("progreso").addEventListener("input", (e) => {
  if (audio.duration) audio.currentTime = (e.target.value / 1000) * audio.duration;
});

audio.addEventListener("play", () => { $("reproductor").classList.add("playing"); $("btnPlay").textContent = "⏸"; });
audio.addEventListener("pause", () => { $("reproductor").classList.remove("playing"); $("btnPlay").textContent = "▶"; });
audio.addEventListener("loadedmetadata", () => { $("tTotal").textContent = mmss(audio.duration); });
audio.addEventListener("timeupdate", () => {
  $("tActual").textContent = mmss(audio.currentTime);
  if (audio.duration) $("progreso").value = (audio.currentTime / audio.duration) * 1000;
});
audio.addEventListener("ended", () => siguiente(true));   // pasa a la siguiente
audio.addEventListener("error", () => {
  if (audio.getAttribute("src")) $("pAviso").textContent = "El navegador no pudo reproducir este archivo";
});


// ---------- Experimentos de rendimiento ----------
function graficoTiempos(filas) {                     // gráfico SVG (escala logarítmica en el eje Y)
  const W = 560, H = 290, m = { i: 56, d: 16, s: 16, b: 52 };
  const series = [["Merge Sort", "orden_ms", "#22d3ee"], ["Greedy", "greedy_ms", "#fbbf24"], ["PD", "pd_ms", "#ec4899"]];
  const valores = filas.flatMap((f) => series.map(([, k]) => Math.max(f[k], 0.001)));
  const lmin = Math.floor(Math.log10(Math.min(...valores))), lmax = Math.ceil(Math.log10(Math.max(...valores)));
  const x = (i) => m.i + (filas.length === 1 ? 0.5 : i / (filas.length - 1)) * (W - m.i - m.d);
  const y = (v) => m.s + (1 - (Math.log10(Math.max(v, 0.001)) - lmin) / (lmax - lmin || 1)) * (H - m.s - m.b);
  let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Tiempos de ejecución">`;
  for (let e = lmin; e <= lmax; e++) {
    svg += `<line x1="${m.i}" x2="${W - m.d}" y1="${y(10 ** e)}" y2="${y(10 ** e)}" stroke="rgba(255,255,255,.10)"/>
            <text x="${m.i - 6}" y="${y(10 ** e) + 4}" text-anchor="end">${10 ** e} ms</text>`;
  }
  filas.forEach((f, i) => { svg += `<text x="${x(i)}" y="${H - m.b + 18}" text-anchor="middle">${f.n}</text>`; });
  svg += `<text x="${(W + m.i) / 2}" y="${H - 22}" text-anchor="middle">n (cantidad de canciones)</text>`;
  series.forEach(([nombre, k, color], j) => {
    svg += `<polyline fill="none" stroke="${color}" stroke-width="2.5" points="${filas.map((f, i) => `${x(i)},${y(f[k])}`).join(" ")}"/>`;
    filas.forEach((f, i) => { svg += `<circle cx="${x(i)}" cy="${y(f[k])}" r="3.5" fill="${color}"><title>${nombre}, n=${f.n}: ${f[k]} ms</title></circle>`; });
    svg += `<rect x="${m.i + j * 120}" y="${H - 12}" width="10" height="10" fill="${color}"/><text x="${m.i + j * 120 + 14}" y="${H - 3}">${nombre}</text>`;
  });
  return `<div class="grafico">${svg}</svg></div>`;
}

$("btnExperimentos").addEventListener("click", async (e) => {
  const boton = e.currentTarget;
  boton.disabled = true;
  $("graficoExperimentos").innerHTML = "";
  $("resExperimentos").innerHTML = '<p class="muted">Ejecutando… puede tardar unos segundos.</p>';
  try {
    const r = await postJSON("/api/experimentos", { tamanos: [50, 100, 250, 500, 1000, 2000] });
    $("graficoExperimentos").innerHTML = graficoTiempos(r.filas);
    $("resExperimentos").innerHTML = `<div class="tabla-wrap"><table>
      <thead><tr><th>n</th><th>Merge Sort</th><th>Greedy</th><th>PD</th><th>Pts Greedy</th><th>Pts PD</th></tr></thead>
      <tbody>${r.filas.map((f) => `<tr><td>${f.n}</td><td>${f.orden_ms} ms ${f.orden_correcto ? "✔" : "✘"}</td>
        <td>${f.greedy_ms} ms</td><td>${f.pd_ms} ms</td><td>${f.greedy_puntos}</td><td><b>${f.pd_puntos}</b></td></tr>`).join("")}
      </tbody></table></div>
      <p class="nota">Eje Y logarítmico. Capacidad fija de 30 min: PD crece ≈ linealmente con n; Merge Sort y Greedy, como n log n.</p>`;
  } catch (err) {
    $("resExperimentos").innerHTML = "";
    aviso(err.message, "error");
  } finally { boton.disabled = false; }
});

// ---------- Inicio ----------
cargarCatalogo();
cargarPlaylistsGuardadas();
$("tiempoHint").textContent = `= ${mmss(Number($("tiempoMax").value))}`;
