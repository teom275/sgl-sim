/*
 * English / Spanish for the web simulator.
 * Static text: elements with data-i18n="key" keep their English in the HTML;
 * the Spanish lives here. Dynamic text: window.I18N.t("key", {vars}).
 * Language order: ?lang=xx in the URL, then the saved choice, then the browser.
 */
(function () {
  "use strict";

  const ES = {
    // Navigation and page
    "doc.title": "sgl-sim: el Sol como telescopio",
    "nav.focal": "Línea focal",
    "nav.caustic": "Cruz de Einstein",
    "nav.psf": "Óptica ondulatoria",
    "nav.targets": "Planificador de misión",
    "nav.videos": "Videos",
    "nav.dashboard": "Panel de misión",
    "lang.switch": "English",
    "lang.label": "Switch to English",

    "hero.title": "El Sol curva la luz de las estrellas y forma un telescopio de 550 UA de largo.",
    "hero.text": "La luz de un planeta lejano que roza el Sol se desvía 1,75 segundos de arco y se cruza con el eje óptico mucho más allá de Plutón. Ahí, una nave ve el planeta amplificado unas cien mil millones de veces. Mueve los controles o arrastra la nave a lo largo del eje.",

    // Scene 1
    "focal.h": "De los rayos curvados a una línea focal",
    "focal.lede": "Un rayo que pasa a una distancia <i>b</i> del centro de la lente cruza el eje en <i>z</i> = <i>b</i>²/2<i>R</i><sub>s</sub>. Los rayos que rozan el borde enfocan primero, en <i>z</i><sub>min</sub>, y todo punto más lejano está en foco: esa es la línea focal. Los rayos más cercanos chocan con la estrella.",
    "focal.cap": "Fuera de escala: los ángulos están exagerados decenas de miles de veces.",
    "focal.hint": "Arrastra la nave a lo largo del eje para cambiar su distancia.",
    "focal.mass": "Masa de la lente",
    "focal.rad": "Radio de la lente",
    "focal.z": "Distancia de la nave",
    "focal.dt.zmin": "La línea focal empieza en",
    "focal.dt.b": "Rayo que llega a la nave",
    "focal.dt.theta": "Radio del anillo de Einstein",
    "focal.dt.mu": "Ganancia máxima a 1 µm",
    "focal.reset": "Volver al Sol",
    "focal.ok": "La nave está sobre la línea focal.",
    "focal.close": "Demasiado cerca: los rayos que enfocarían aquí chocan con la lente. Aléjate más allá de {z} UA.",
    "focal.blocked": "bloqueado",

    // Scene 2
    "caustic.h": "Un Sol achatado convierte el foco en un astroide",
    "caustic.lede": "El Sol está levemente achatado por su rotación (momento cuadrupolar <i>J</i><sub>2</sub>). En lugar de un único punto focal, el plano del receptor contiene una cáustica de cuatro puntas. Dentro de ella el telescopio ve cuatro imágenes del planeta sobre el anillo de Einstein; fuera, dos.",
    "caustic.cap1": "Plano del receptor",
    "caustic.cap2": "Vista del telescopio, con el Sol tapado",
    "caustic.j2": "Achatamiento J₂",
    "caustic.z": "Distancia de la nave",
    "caustic.dt.n": "Imágenes en el anillo",
    "caustic.dt.val": "Valor de prueba del astroide",
    "caustic.dt.a": "Semiancho del astroide (máx.)",
    "caustic.hint": "Arrastra o toca el plano del receptor. Un valor de prueba menor que 1 significa que estás dentro del astroide.",
    "caustic.inside": "Dentro del astroide: cuatro imágenes forman una cruz de Einstein.",
    "caustic.outside": "Fuera del astroide: quedan dos imágenes.",
    "caustic.edge": "Sobre la cáustica: dos imágenes se funden y desaparecen.",

    // Scene 3
    "psf.h": "Óptica ondulatoria: el foco mide centímetros",
    "psf.lede": "Como onda, la línea focal tiene un perfil de Bessel, <i>J</i>₀²(<i>k</i>θ<sub>E</sub>ρ). El núcleo brillante mide unos pocos centímetros, así que hasta un telescopio de 1 m recoge muchos anillos a la vez. El núcleo se ensancha con la longitud de onda y con la distancia.",
    "psf.cap1": "Intensidad según la distancia al eje",
    "psf.cap2": "Plano transversal, 60 cm de lado a lado",
    "psf.lam": "Longitud de onda",
    "psf.z": "Distancia de la nave",
    "psf.dt.core": "Radio del núcleo (primer anillo oscuro)",
    "psf.dt.mu": "Ganancia máxima",
    "psf.dt.span": "Una apertura de 1 m abarca",
    "psf.radii": "{n} radios del núcleo",

    "review.note": "<b>Modelo en revisión.</b> Una auditoría física encontró que el balance de fotones, la reconstrucción de la imagen, la rotación del planeta y el movimiento de la imagen detrás de este planificador eran demasiado optimistas. El ranking y la conclusión de «una nave o un enjambre» van a cambiar. Ya corregido: tamaño de la cáustica, corona, movimiento propio, datos del catálogo y balance de fotones. <a href=\"https://github.com/teom275/sgl-sim/blob/main/docs/auditoria-fisica.md\">Leer la auditoría</a>.",

    // Mission planner
    "targets.h": "¿Qué planetas debería observar primero un telescopio de lente solar?",
    "targets.lede": "Cada planeta cercano conocido recibe un puntaje de viabilidad sobre 100, calculado para una nave a 650 UA. El puntaje combina cuánta luz llega al detector (30 %), cuánto tarda el barrido de la imagen (25 %), qué tan cerca está el objetivo de la eclíptica, donde volar es más barato (25 %), y cuánto desenfoca el barrido la rotación del planeta (20 %). Elige un planeta para ver su misión completa.",
    "th.planet": "Planeta",
    "th.dist": "Distancia",
    "th.img": "Imagen del planeta",
    "th.points": "El telescopio apunta a",
    "th.score": "Puntaje",
    "targets.hint": "«Imagen del planeta» es el diámetro de la imagen del planeta en la línea focal: el área que la nave tiene que barrer. El telescopio apunta en dirección opuesta al planeta, hacia el otro lado del cielo. Los puntajes salen de <code>sgl_sim.get_ranked_catalog</code>.",
    "targets.loading": "Cargando el ranking…",
    "targets.error": "No se pudo cargar el ranking. Recarga la página para intentarlo otra vez.",
    "targets.select": "Ver la misión a {name}",

    "m.score": "Puntaje de viabilidad",
    "m.where": "Adónde enviar la nave",
    "m.where.lede": "La nave tiene que estar del lado opuesto del Sol respecto del planeta.",
    "m.point": "Apuntado del telescopio",
    "m.const": "Constelación",
    "m.xyz": "Posición heliocéntrica x, y, z",
    "m.incl": "Fuera de la eclíptica",
    "m.sky": "Facilidad de llegar a la línea focal en cada dirección del cielo (más claro es más fácil). Cada punto es un candidato: pasa el mouse para ver su nombre y haz clic para abrir su misión. El anillo marca el elegido.",
    "m.trip": "El viaje y la operación",
    "m.trip.lede": "Llegada en {year}, crucero a {v} UA por año.",
    "m.cruise": "Tiempo de crucero",
    "m.delay": "Retraso de la señal a la Tierra",
    "m.imgdiam": "Diámetro de la imagen a barrer",
    "m.drift": "Deriva por movimiento propio",
    "m.driftyr": "Deriva por año",
    "m.dv": "Δv de barrido, una nave",
    "m.dvswarm": "Δv de barrido por nave, enjambre de {n}",
    "m.imaging": "¿Una nave o un enjambre?",
    "m.imaging.lede": "El planeta gira durante el barrido y eso desenfoca la imagen. Varias naves barren en paralelo y terminan antes.",
    "m.one": "Una nave",
    "m.swarm": "Enjambre de {n}",
    "m.smear": "desenfoque {x}× · barrido {h} h",
    "m.verdict.swarm": "Hace falta un enjambre: con una sola nave, la rotación desenfoca la imagen.",
    "m.verdict.single": "Basta con una nave: el planeta gira tan lento (o tiene rotación sincrónica) que la imagen no se desenfoca.",
    "m.breakdown": "Por qué obtiene este puntaje",
    "m.surface": "Superficie",
    "m.surf.planet": "Planeta simulado",
    "m.surf.earth": "Tierra",
    "m.surf.moon": "Luna",
    "m.truth": "Superficie real",
    "m.truth.cap": "lo que la lente intenta captar",
    "m.surf.note.planet": "Un mundo oceánico sintético con continentes y casquetes polares: todavía no sabemos cómo es la superficie real de {name}. Elige Tierra o Luna para comparar con un cuerpo conocido.",
    "m.surf.note.earth": "¿Cómo se vería la Tierra sin nubes con esta misión? Misma distancia, rotación y ruido que {name}; solo cambia la superficie. Resolución: 32 × 32 píxeles.",
    "m.surf.note.moon": "¿Cómo se vería la cara visible de la Luna (mapa esquemático de sus mares) con esta misión? Misma distancia, rotación y ruido que {name}; solo cambia la superficie.",
    "m.err": "error {e} · similitud {s}",
    "m.sky.open": "Clic para ver la misión",
    "m.sky.cycle": "Clic para pasar de uno a otro",
    "m.f.snr": "Señal (SNR)",
    "m.f.log": "Logística del barrido",
    "m.f.ecl": "Acceso desde la eclíptica",
    "m.f.blur": "Resistencia al desenfoque",
    "m.shared": "Trayectoria compartida",
    "m.shared.yes": "La misma flota puede observar también {list} con una corrección menor de trayectoria (a menos de 3°).",
    "m.shared.no": "Ningún otro candidato está a menos de 3°, así que esta misión no se puede compartir.",
    "m.days": "{n} días",
    "m.years": "{n} años",
    "m.hours": "{n} h",
    "m.ly": "{n} años luz",

    // Videos and footer
    "videos.h": "Videos de demostración",
    "videos.lede": "Las mismas tres escenas renderizadas con <a href=\"https://github.com/3b1b/manim\">ManimGL</a>, el motor de animación que usa 3Blue1Brown. En el repositorio también son aplicaciones interactivas de escritorio.",
    "videos.c1": "Rayos, z<sub>min</sub> y la línea focal",
    "videos.c2": "Cáustica de astroide y cruz de Einstein",
    "videos.c3": "Función de dispersión de punto (óptica ondulatoria)",
    "foot.1": "Las fórmulas coinciden con el paquete de Python <a href=\"https://github.com/teom275/sgl-sim\">sgl-sim</a>: deflexión en campo débil, <i>z</i>(<i>b</i>) = <i>b</i>²/2<i>R</i><sub>s</sub>, μ<sub>max</sub> = 4π²<i>R</i><sub>s</sub>/λ, la ecuación de lente cuadrupolar con <i>J</i>₂ y la función de dispersión de punto <i>J</i>₀². El análisis de misión se precalcula con <code>scripts/export_site_targets.py</code>.",
    "foot.2": "Licencia MIT · Teo Maggio",

    "flag.unconfirmed": "planeta no confirmado",
    "flag.radius": "radio estimado",

    // Units shown in JS
    "unit.au": "UA",
    "tier.Prime Swarm/Single Target": "Prioritario: una nave o enjambre",
    "tier.High Launch Delta-V (Out of Ecliptic)": "Lanzamiento costoso (fuera de la eclíptica)",
    "tier.Swarm Required (Fast Rotator / Large Image)": "Requiere enjambre (rotación rápida o imagen grande)",

    // Planet notes
    "desc.Wolf 1061 c": "Supertierra cercana en la zona habitable, con inclinación eclíptica moderada.",
    "desc.Ross 128 b": "Mundo templado cercano que orbita una enana M tranquila; justo sobre el ecuador celeste y la eclíptica.",
    "desc.Luyten b": "Supertierra templada (1,35 masas terrestres) alrededor de GJ 273, cerca de la eclíptica.",
    "desc.Tau Ceti e": "Candidato no confirmado (velocidad radial) alrededor de una enana G parecida al Sol; su radio y su rotación son supuestos.",
    "desc.Teegarden's Star b": "Índice de similitud con la Tierra muy alto (ESI = 0,95); gran deriva lateral por movimiento propio.",
    "desc.LHS 1140 b": "Supertierra densa alrededor de una enana M inactiva; buena retención de atmósfera.",
    "desc.TRAPPIST-1 f": "Candidato rico en volátiles en el borde externo de la zona habitable, en el corredor de TRAPPIST-1.",
    "desc.TRAPPIST-1 e": "Planeta templado del tamaño de la Tierra en la zona habitable de TRAPPIST-1; cerca del plano de la eclíptica.",
    "desc.Proxima Centauri b": "El exoplaneta más cercano; máximo flujo de fotones, pero muy inclinado respecto de la eclíptica.",
    "desc.TRAPPIST-1 d": "Planeta en el borde interno de la zona habitable, en el corredor multiplanetario de TRAPPIST-1.",
    "desc.TOI-700 d": "Planeta de la zona habitable descubierto por TESS (NASA); trayectoria casi polar respecto de la eclíptica.",
    "desc.Kepler-186 f": "Histórico primer planeta del tamaño de la Tierra en una zona habitable; lejano y con poco flujo de fotones.",
  };

  const listeners = [];
  const originals = new Map();
  const params = new URLSearchParams(location.search);
  let saved = null;
  try { saved = localStorage.getItem("sgl-lang"); } catch (_) { /* storage blocked */ }
  let lang = params.get("lang") || saved || ((navigator.language || "en").toLowerCase().startsWith("es") ? "es" : "en");
  if (lang !== "es") lang = "en";

  function fill(str, vars) {
    return vars ? str.replace(/\{(\w+)\}/g, (_, k) => (k in vars ? vars[k] : `{${k}}`)) : str;
  }

  /** Translate a key; `fallback` is the English text (defaults to the key). */
  function t(key, vars, fallback) {
    const s = lang === "es" && key in ES ? ES[key] : (fallback !== undefined ? fallback : key);
    return fill(s, vars);
  }

  function apply() {
    document.documentElement.lang = lang;
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const key = el.dataset.i18n;
      if (!originals.has(el)) originals.set(el, el.innerHTML);
      el.innerHTML = lang === "es" && key in ES ? ES[key] : originals.get(el);
    });
    document.querySelectorAll("[data-i18n-attr]").forEach((el) => {
      // Format: "attr:key;attr:key"
      el.dataset.i18nAttr.split(";").forEach((pair) => {
        const [attr, key] = pair.split(":");
        const store = `orig-${attr}`;
        if (!(store in el.dataset)) el.dataset[store] = el.getAttribute(attr) || "";
        el.setAttribute(attr, lang === "es" && key in ES ? ES[key] : el.dataset[store]);
      });
    });
    if (!originals.has(document)) originals.set(document, document.title);
    document.title = lang === "es" ? ES["doc.title"] : originals.get(document);
    const btn = document.getElementById("lang-toggle");
    if (btn) {
      btn.textContent = lang === "es" ? ES["lang.switch"] : "Español";
      btn.setAttribute("aria-label", lang === "es" ? ES["lang.label"] : "Cambiar a español");
      btn.lang = lang === "es" ? "en" : "es";
    }
  }

  function set(next) {
    lang = next === "es" ? "es" : "en";
    try { localStorage.setItem("sgl-lang", lang); } catch (_) { /* storage blocked */ }
    const url = new URL(location.href);
    url.searchParams.set("lang", lang);
    history.replaceState(null, "", url);
    apply();
    listeners.forEach((cb) => cb(lang));
  }

  window.I18N = {
    get lang() { return lang; },
    t,
    set,
    apply,
    onChange(cb) { listeners.push(cb); },
    /** Locale-aware number formatting (comma decimals in Spanish). */
    num(x, d = 1) {
      return Number(x).toLocaleString(lang === "es" ? "es" : "en", { minimumFractionDigits: d, maximumFractionDigits: d });
    },
  };

  document.addEventListener("DOMContentLoaded", () => {
    apply();
    const btn = document.getElementById("lang-toggle");
    if (btn) btn.addEventListener("click", () => set(lang === "es" ? "en" : "es"));
  });
})();
