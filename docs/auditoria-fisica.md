# Auditoría física de sgl-sim

**Fecha:** 3 de noviembre de 2026 · **Alcance:** paquete `sgl_sim` (v0.1.0), dashboard, sitio web y catálogo de candidatos · **Objetivo:** que el análisis resista una revisión de JOSS y tenga sentido para planificar misiones reales.

## Resumen

La **óptica básica de la lente es correcta**: deflexión, z_min, anillo de Einstein, ganancia máxima, PSF J₀², tamaño de la imagen, retraso de la señal y apuntado antipodal coinciden con la literatura.

Todo lo que depende de **fotones, ruido, tiempo y movimiento está mal o sin fundamentar**, y eso es justamente lo que decide si una misión es viable:

1. **El SNR está sobreestimado unas 10¹⁰ veces.** Según el paquete, una Tierra a 30 pc con un telescopio de 1 m alcanza SNR 7 por píxel en 0,002 s. La literatura da del orden de 10⁷ s.
2. **Las imágenes reconstruidas no representan a la lente solar.** La PSF se muestrea con píxeles de 1 m cuando cada píxel mide 0,1–1 km. Así la lente casi no desenfoca, y la penalización de deconvolución, que domina en la literatura, desaparece. Esto también afecta las imágenes de la Tierra y la Luna del sitio.
3. **"Basta con una nave" es un artefacto del modelo.** Para los planetas con rotación sincrónica el desenfoque se fija en 0,05, pero esos planetas giran una vez por órbita: entre 4 y 37 días en este catálogo. Además el barrido usa 10 s por píxel, cuando el tiempo real va de minutos a meses. Con tiempos realistas, todos los candidatos rotan muchas veces durante la observación.
4. **Falta el movimiento orbital de la imagen, que es el efecto dinámico dominante.** La imagen de Próxima b recorre unos 17.600 km cada 11 días, a ~114 m/s. Es el doble de la deriva por movimiento propio que modela el paquete, y la aceleración necesaria para seguirla es miles de veces mayor que el Δv de barrido que se reporta.
5. **La cáustica de astroide es unas 10⁵ veces demasiado grande** (39.000 km frente a ≤ 0,29 km) y crece con la distancia cuando debería decrecer.
6. **El puntaje de viabilidad es heurístico.** Ignora el tiempo de integración y el seguimiento de la imagen, y depende de datos del catálogo con errores.

Mi opinión: el ranking actual no sirve para decidir misiones, y el paper no debería enviarse con estos modelos. La buena noticia es que todo se puede corregir con modelos publicados, y la base del código (unidades, estructura, tests, visualizaciones) es reutilizable.

---

## Estado de las correcciones

| Hallazgo | Estado | Qué cambió |
|---|---|---|
| H4 · Movimiento propio | ✅ Corregido | Total = √(μ_α*² + μ_δ²). La deriva de Próxima pasa de 28,4 a 57,6 m/s, y los dos caminos de código coinciden. Hay test. |
| H3 · Catálogo | ✅ Corregido | Periodos de LHS 1140 b (593,8 h) y Kepler-186 f (3.117,6 h). Nuevos campos `radius_measured` y `confirmed`: Tau Ceti e figura como no confirmado y 6 radios como estimados. El sitio los muestra. |
| H1 · Cáustica | ✅ Corregido | a = 2 J₂ R² sin²β_s / b, que da 287,4 m · √(650 AU/z) para J₂ = 2,25 × 10⁻⁷ (como en Turyshev y Toth). Nuevo `solar_axis_sin2_beta()` con el polo solar de la IAU. Está corregido también en JavaScript y en ManimGL. |
| M1 · Corona | ✅ Corregido | Forma clásica de Baumbach: 10⁻⁶ [0,0532 r⁻²·⁵ + 1,425 r⁻⁷ + 2,565 r⁻¹⁷]. |
| C1 · Balance de fotones (SNR) | ✅ Corregido | Nuevo `sgl_sim.radiometry` con desenfoque de fuente extendida, señal del píxel y corona en el anillo. Reproduce el caso de referencia de Toth y Turyshev (30 pc, 1 m, N = 1000: 1,8 × 10⁷ s por píxel frente a 1,33 × 10⁷) y tiene tests. `calculate_snr` y el trade usan este modelo. Pendiente: verificar los demás casos publicados (p. ej. Próxima con 1000 × 1000) contra los papers. |
| C2 · Reconstrucción de la imagen | ⏳ Pendiente | La PSF todavía se muestrea con píxeles de 1 m. |
| C3 · Rotación y fases | ⏳ Pendiente | "Basta con una nave" sigue siendo un artefacto. |
| C4, M2, M3 · Movimiento de la imagen | ⏳ Pendiente | |
| M4 · Trayectoria | ⏳ Pendiente | |
| H2 · Puntaje y ranking | ⏳ Pendiente | Depende de C2–C4 y M4. |
| M5, B1 · Agujero negro, CI, afirmaciones | ⏳ Pendiente | |

El sitio y el dashboard muestran un aviso de "modelo en revisión" con enlace a este documento.

## 1. Qué está bien (verificado)

| Magnitud | Paquete | Literatura / comprobación |
|---|---|---|
| Deflexión en campo débil | α = 2R_s/b | ✔ |
| Distancia de cruce del eje | z(b) = b²/2R_s | ✔ |
| z_min (Sol) | 547,8 AU | ✔ (~548 AU) |
| Radio del anillo de Einstein a 650 AU | b = 1,09 R☉, θ_E = 1,61″ | ✔ |
| Ganancia máxima | μ₀ = 4π²R_s/λ = 1,17 × 10¹¹ a 1 µm | ✔ |
| PSF | J₀²(k θ_E ρ), núcleo de 4,9 cm | ✔ |
| Diámetro de la imagen | D = 2R·z/d (Tierra a 30 pc: 1,3 km) | ✔ (Toth y Turyshev dan 1,3 km) |
| Retraso de la señal a 650 AU | 3,75 días | ✔ |
| Apuntado del telescopio | antípoda del objetivo | ✔ |
| Agujero negro | b_c = 3√3/2 R_s, esfera de fotones de 1,5 R_s | ✔ |
| Distancias del catálogo | Wolf 1061, Ross 128, Próxima, TRAPPIST-1, etc. | ✔ en general |

---

## 2. Hallazgos

La severidad mide el impacto sobre las conclusiones de misión:
- **Crítico:** invalida resultados que se muestran o se publican.
- **Alto:** un error claro con impacto visible.
- **Medio:** un modelo incompleto o una suposición sin justificar.
- **Bajo:** presentación o rigor.

### C1 · Crítico: el modelo de SNR no es físico (`deconvolution.calculate_snr`)

- La señal se arma con constantes sin unidades ni fuente: `1.5e-3`, el flujo de corona `8.5e6`, y `mu_eff`, que se asigna dos veces y la primera se descarta.
- **La corona se reduce un millón de veces** con `coronagraph_suppression = 1e-6`. Pero la corona brilla justo en el anillo de Einstein, a 1,09 R☉: un coronógrafo tapa el disco solar, no puede quitar la luz que se superpone a la señal. En la literatura la corona es la fuente de ruido dominante.
- Falta la luz desenfocada del resto del planeta. En una fuente extendida, cada posición del telescopio recibe luz de todo el disco por las colas 1/ρ de la PSF, y eso domina sobre el píxel directo.
- **Evidencia:** para 30 pc y un telescopio de 1 m, el paquete da SNR 169 en 1 s. Para llegar a SNR 7 bastarían 0,0017 s. Toth y Turyshev (2021) estiman ~1,3 × 10⁷ s por píxel para ese caso. **La discrepancia es de unas 10¹⁰ veces.**
- **Qué afecta:** el KPI de SNR del dashboard (~10⁶), el trade de distancia × apertura (tiempos de ~10⁻¹⁰ h) y los ejemplos de deconvolución.
- **Corrección:** implementar el balance de señal y ruido publicado (Turyshev y Toth 2020; Toth y Turyshev 2021; MNRAS 2022), con la señal directa, la luz desenfocada del disco y la corona en el anillo. Agregar tests de regresión con sus números: D = 1,3 km a 30 pc; ~0,85 años para 128 × 128 píxeles a 30 pc; ~14 meses para 1000 × 1000 píxeles de Próxima con SNR > 10.

### C2 · Crítico: la deconvolución no representa a la lente solar (`optics.generate_2d_psf` y sus usos)

- `pixel_scale_m=1.0` está fijo en `triage.compute_motion_blur` y en `web/app.py`. Pero cada píxel de la imagen mide D/N: de 0,1 a 1 km para 32 píxeles. Con píxeles de 1 m, la PSF de 5 cm queda casi como un punto, y la "deconvolución" apenas tiene algo que deshacer.
- El ruido se fija como `std(imagen)/SNR`, sin relación con el balance de fotones. En `compute_motion_blur` el SNR vale siempre 25.
- Toda la dificultad real del problema, la penalización de deconvolución que crece con N (Toth y Turyshev 2021), no está.
- **Consecuencia:** las reconstrucciones con similitud de 0,85–0,99, incluidas la Tierra y la Luna del sitio, son optimistas y no se pueden citar.
- **Corrección:** usar la matriz de convolución de fuente extendida de la lente solar (píxeles de tamaño D/N, colas 1/ρ) con el ruido de C1. Para N grandes, aplicar la penalización analítica publicada en lugar de la convolución completa.

### C3 · Crítico: el modelo temporal hace que "basta con una nave" salga siempre (`triage.compute_motion_blur`)

- Si `tidally_locked=True`, el desenfoque se fija en `eta_blur = 0.05` y nunca hay desenfoque. Pero rotación sincrónica significa girar **una vez por órbita**. Visto desde lejos, el hemisferio visible cambia por completo en 4 días (TRAPPIST-1 d), 11 días (Próxima b) o 37 días (TOI-700 d). Además cambian la fase iluminada y las nubes.
- El tiempo de barrido usa 10 s por píxel (32² × 10 s = 2,84 h, igual para todos). Con tiempos realistas (C1), de minutos a meses por píxel, **cada planeta rota decenas o cientos de veces durante la observación**.
- El modelo dibuja un disco lleno, sin fases. Los planetas que transitan, como TRAPPIST-1 y LHS 1140 b, se ven casi de canto y pasan de "nuevo" a "lleno" en cada órbita.
- **Tu sospecha era correcta:** con física realista, ningún candidato se puede fotografiar "congelado", ni con una nave ni con 8. La literatura (Toth y Turyshev 2023, *Imaging rotating and orbiting exoplanets*) propone reconstruir con resolución temporal: aprovechar la rotación y muestrear cada fase muchas veces.
- **Corrección:** modelar el periodo de rotación real (para planetas sincrónicos, igual al orbital), la fase, y el tiempo total frente a la rotación. Cambiar la pregunta de "¿una nave o un enjambre?" por "cuántas naves y cuántos años para alcanzar la calidad X", según el enfoque de reconstrucción temporal.

### C4 · Crítico: falta el movimiento orbital de la imagen

La imagen del planeta en el plano focal se mueve con la órbita del planeta, escalada por z/d. Con los semiejes y periodos publicados:

| Planeta | Imagen (km) | Amplitud del movimiento (km) | Velocidad de la imagen (m/s) | Deriva por mov. propio (m/s) | Aceleración máx. (µm/s²) |
|---|---|---|---|---|---|
| Próxima b | 31,8 | 17.574 | 114 | 58 | 742 |
| Teegarden b | 11,0 | 3.102 | 46 | 94 | 680 |
| Ross 128 b | 13,2 | 6.938 | 51 | 20 | 377 |
| TRAPPIST-1 d | 2,5 | 846 | 15 | 15 | 273 |
| Luyten b | 12,5 | 11.289 | 44 | 56 | 172 |
| Wolf 1061 c | 15,5 | 9.735 | 40 | 17 | 161 |
| TRAPPIST-1 e | 3,0 | 1.111 | 13 | 15 | 158 |
| TRAPPIST-1 f | 3,4 | 1.460 | 12 | 15 | 91 |
| LHS 1140 b | 4,6 | 2.975 | 9 | 10 | 26 |
| Tau Ceti e | 19,8 | 69.487 | 31 | 29 | 14 |
| TOI-700 d | 1,5 | 2.468 | 5 | 2 | 9 |
| Kepler-186 f | 0,3 | 1.141 | 0,6 | 0,2 | 0,4 |

- **Comprobación de orden de magnitud:** para una Tierra análoga a 10 años luz, mi cálculo da ~3 µm/s². Turyshev y Toth (2022) reportan ~6,1 µm/s² para ese caso, el mismo orden. Los planetas de la zona habitable de enanas M tienen órbitas de días, así que sus aceleraciones son **100 a 250 veces mayores**.
- **Seguir la imagen de Próxima b** pide ~7 × 10⁻⁴ m/s² sostenidos, unos 20 km/s por año. El paquete reporta un Δv de barrido de ~1 km/s, pero calculado con 2,84 h de observación. La alternativa es no seguir la imagen y dejar que pase barriendo, con otra estrategia de muestreo; en cualquier caso es el factor que más decide la viabilidad, y el ranking lo ignora.
- **Corrección:** añadir el movimiento de la imagen (órbita del planeta, oscilación de la estrella, oscilación del Sol) y calcular el Δv de seguimiento o el ciclo de muestreo. Esto debería entrar en el puntaje.

### H1 · Alto: el tamaño de la cáustica está mal (`caustics.astroid_caustic_semi_width`)

- **Paquete:** a = 2R·J₂·z/b, que da 39.276 km a 650 AU y 46.216 km a 900 AU.
- **Literatura** (Turyshev y Toth 2021, *Optical properties of an extended gravitational lens*): ρ ≈ 287 m · √(650 AU/z) · sin²β_s · (J₂/2,25 × 10⁻⁷), es decir ≤ 287 m a 650 AU y ≤ 244 m a 900 AU. La razón es **1,4 × 10⁵**, y la dependencia con z tiene el signo opuesto.
- Falta sin²β_s, el ángulo entre el eje de rotación del Sol y la línea de visión. La cáustica depende de la dirección del objetivo, y para objetivos cerca del eje solar casi desaparece.
- **Qué afecta:** el valor en km que muestran el dashboard y el sitio, los FITS exportados y el paper. Los regímenes (4 o 2 imágenes) están bien, porque se calculan en unidades de a.
- **Corrección:** usar la fórmula publicada con el eje solar (α = 286,13°, δ = 63,87°) y la dirección de cada objetivo.

### H2 · Alto: el puntaje de viabilidad no tiene base física (`triage.score_exoplanet_candidate`)

- **SNR (30 %):** log(R²/d²). Ignora la luminosidad de la estrella, la insolación, el albedo, la corona y el tiempo de integración. `host_star_mag` se recibe y no se usa.
- **Logística (25 %):** una ventana arbitraria de 1,5–15 km para la imagen y un umbral de 35 m/s para la deriva. No considera el movimiento orbital (C4).
- **Eclíptica (25 %):** cos²β, sin un modelo de trayectoria (ver M4).
- **Desenfoque (20 %):** constantes elegidas a mano (0,98 para sincrónicos), heredando el error de C3.
- **Niveles:** umbrales arbitrarios y contradictorios. Tau Ceti e sale "Tier 1: Prioritario" y a la vez necesita enjambre; el nivel "Requiere enjambre" casi nunca se alcanza.
- **Corrección:** reemplazar el índice por magnitudes derivadas: tiempo total de integración para una calidad dada (C1–C3), Δv de seguimiento (C4), tiempo de vuelo y Δv de lanzamiento (M4). Se pueden presentar como frente de Pareto o con pesos justificados y un análisis de sensibilidad. Para la NASA, un frente de Pareto es más defendible que un número sobre 100.

### H3 · Alto: errores y supuestos ocultos en el catálogo (`triage.CATALOG_12_CANDIDATES`)

- **LHS 1140 b:** `rot_period_hrs = 314,4` (13,1 d) con rotación sincrónica, pero su periodo orbital es de 24,74 d (593,8 h).
- **Kepler-186 f:** 312 h, pero su periodo orbital es de 129,9 d (3.118 h). Es un error de un factor 10.
- **Tau Ceti e:** es un **candidato no confirmado** (detección por velocidad radial disputada). Su radio de 1,8 R⊕ no está medido y la rotación de 35 h es supuesta. Su conclusión de "necesita enjambre" sale de esos supuestos.
- **Radios estimados:** Próxima b, Ross 128 b, Wolf 1061 c, Luyten b y Teegarden b no transitan, así que solo se conoce su masa mínima (m sin i). Los radios del catálogo son estimaciones y hay que marcarlas como tales, porque el tamaño de la imagen y el SNR escalan con R².
- **Corrección:** citar la fuente de cada dato (NASA Exoplanet Archive, con fecha), separar los datos medidos de los supuestos y propagar la incertidumbre al ranking.

### H4 · Alto: el movimiento propio se cuenta mal (`targets.compute_sgl_deployment_vector`)

- `pmra` ya es μ_α* (incluye cos δ): así viene del NASA Exoplanet Archive, y así se le pasa a astropy como `pm_ra_cosdec`. Pero el total se calcula con `pmra * cos(dec)`, **multiplicando dos veces por cos δ**.
- **Próxima:** 1.899 mas/año en lugar de 3.859, así que la deriva da 28,4 m/s cuando debería ser 57,6. El triage, con otro camino de código, sí da 57,6, y por eso los dos números no coinciden en el sitio.
- **Corrección:** total = √(pmra² + pmdec²). Es un cambio de una línea, con un test.

### M1 · Medio: los coeficientes de la corona no son los estándar (`baumbach_allen_coronal_brightness`)

- **Paquete:** 10⁻⁶ [2,56 r⁻⁶ + 1,42 r⁻²·⁵ + 0,0226 r⁻¹·⁵].
- **Forma clásica de Baumbach** para la corona K: 10⁻⁶ [2,565 r⁻¹⁷ + 1,425 r⁻⁷ + 0,0532 r⁻²·⁵].
- Los coeficientes parecen los clásicos, pero asignados a otros exponentes. La diferencia es de 1,9× en el anillo (1,09 R☉), 7× a 1,5 R☉ y 24× a 3 R☉.
- **Corrección:** usar la forma de la referencia que siga el paper de Turyshev y Toth (incluye la corona F) y citarla.

### M2 · Medio: falta la oscilación del Sol

El Sol se mueve alrededor del baricentro (sobre todo por Júpiter): ~12 m/s, con desplazamientos de ~10⁶ km en 12 años. La línea focal pasa por el centro del Sol y se mueve con él. Su aceleración es pequeña (~0,2 µm/s², Turyshev y Toth 2022), pero la nave tiene que corregir ese desplazamiento. La literatura propone navegar con la luz amplificada de la estrella anfitriona como referencia.

### M3 · Medio: la nave no está quieta

- La nave sale del sistema solar a ~20–25 AU/año y no frena. z crece un 3–4 % por año, y con él cambian el tamaño de la imagen, la cáustica y la PSF.
- La "velocidad orbital" (1,17 km/s), el "periodo orbital" (16.572 años) y el "Δv para mantenerse en posición" del dashboard suponen una nave quieta en 650 AU. Eso no corresponde a ninguna arquitectura publicada.
- **Corrección:** quitar esas métricas, o redefinirlas, y modelar la observación como un tramo de z (por ejemplo, de 650 a 900 AU).

### M4 · Medio: trayectoria y eclíptica

- `cruise = z/v` con v constante es aceptable como primera aproximación (la literatura da 25–35 años), pero no incluye la fase de perihelio.
- **¿Importa dónde están los planetas?** En la arquitectura de referencia (velas solares con paso cercano al Sol a 0,1–0,2 AU, efecto Oberth), la dirección de salida se fija en el perihelio, así que la posición de los planetas importa poco. Solo importa si se usa una asistencia gravitatoria de Júpiter, que impone ventanas de lanzamiento de unos 12–13 años por dirección.
- **Puntos de Lagrange:** no ayudan a llegar ni a operar en la línea focal, que está a cientos de AU y en una dirección fija. A lo sumo servirían como zona de ensamblaje antes de partir (por ejemplo, Sol–Tierra L2), y no es necesario.
- **Salir de la eclíptica:** el costo real depende de la propulsión (una vela puede inclinar su plano en el perihelio). El cos²β actual no tiene derivación.
- **Corrección:** un modelo simple de trayectoria con perihelio y vela (o cohete más Oberth), con el Δv o el tiempo de vuelo en función de la latitud eclíptica, y citar a Friedman et al. y Helvajian et al.

### M5 · Medio: el modo agujero negro es ilustrativo

z_min = b_c²/2R_s aplica una fórmula de campo débil al borde del campo fuerte, y "verificar la ISCO en z_rec" no tiene sentido físico para un receptor lejano. Hay que marcarlo como ilustrativo o quitarlo del paper.

### B1 · Bajo: rigor y presentación

- **Insignia de CI estática:** "CI passing" es una imagen fija. El workflow vive en `ci/` y `.github/` está en `.gitignore`, así que **la CI nunca se ejecutó en GitHub**. Un revisor de JOSS lo nota enseguida.
- **Afirmaciones excesivas:** "peer-review-ready", "NASA-standard FITS" y "JOSS-compliant" en el README y el paper.
- **Mapa de eficiencia del cielo:** es cos²β multiplicado por un factor de "evitar el plano galáctico" sin justificar (¿confusión de fondo?).
- **El paper** cita las cifras de C1, C2 y H1; hay que rehacerlo después de las correcciones.

---

## 3. Respuestas a tus preguntas

- **¿Es real que basta con una nave?** No. Es un artefacto (C3): el modelo trata a los planetas sincrónicos como si no rotaran y usa barridos de 3 horas. Con tiempos realistas, todos rotan muchas veces y hace falta reconstrucción temporal, varias naves o ambas cosas.
- **¿La trayectoria depende de las órbitas de los planetas?** Poco, con vela solar y perihelio, que es la arquitectura de referencia. Sí depende si se usa Júpiter. Lo que sí cambia mucho entre objetivos es la latitud eclíptica, el tiempo de vuelo hasta la distancia necesaria y, sobre todo, cómo se mueve la imagen (C4).
- **¿Hay puntos de Lagrange útiles?** No para el viaje ni para la operación; a lo sumo para ensamblaje.
- **¿Qué quise decir con "barrido ilustrativo"?** La imagen del planeta mide kilómetros, y cada telescopio tiene que moverse dentro de ella para medir píxel por píxel. El paquete calcula cuánto tarda y cuánto Δv cuesta, pero no el recorrido. Para dibujarlo en 3D tendría que inventar un patrón (eso es "ilustrativo") o modelarlo de verdad. Con C3 y C4 queda claro que hay que modelarlo: la nave tiene que seguir una imagen que se mueve miles de km.

---

## 4. Plan de corrección propuesto (en orden)

1. **Bugs puntuales:**
   - movimiento propio (H4);
   - periodos de LHS 1140 b y Kepler-186 f (H3);
   - etiquetar los radios estimados y Tau Ceti e como no confirmado (H3);
   - fórmula de la cáustica con sin²β_s (H1);
   - coeficientes de la corona con su cita (M1).
2. **Modelo radiométrico publicado** (C1), con tests de regresión contra los números de los papers.
3. **Imagen de fuente extendida** con píxeles D/N y el ruido de (2) (C2).
4. **Modelo temporal** (C3): rotación, fases, tiempo total frente a número de naves.
5. **Dinámica de la imagen** (C4, M2, M3): órbita del planeta, oscilación del Sol, nave alejándose, Δv de seguimiento.
6. **Trayectoria** (M4): vela con perihelio, costo de salir de la eclíptica.
7. **Rehacer el ranking** (H2) con magnitudes de (2)–(6), como Pareto o con un análisis de sensibilidad.
8. **Rigor** (B1): CI real en `.github/workflows`, quitar la insignia estática, moderar las afirmaciones, actualizar el paper, el sitio y el dashboard.

Los pasos 1 y 8 son rápidos. Los pasos 2 a 5 son el corazón del trabajo, y conviene validarlos contra cada número publicado antes de tocar el ranking. Mientras tanto, convendría poner en el sitio y el dashboard una nota de que el modelo de imagen y el ranking están en revisión.

---

## Referencias

- Turyshev y Toth, *Optical properties of an extended gravitational lens* (2021), arXiv:2103.06955. Tamaño de la cáustica: <https://arxiv.org/pdf/2103.06955>
- Turyshev y Toth, *Wave-optical study of the Einstein cross formed by a quadrupole gravitational lens*, arXiv:2105.07295: <https://arxiv.org/html/2105.07295v2>
- Toth y Turyshev, *Image recovery with the solar gravitational lens*, Phys. Rev. D 103, 064073 (2021), arXiv:2012.05477. Tiempos por píxel: <https://arxiv.org/pdf/2012.05477>
- Turyshev y Toth, *Image formation for extended sources with the solar gravitational lens*, arXiv:2002.06492: <https://arxiv.org/pdf/2002.06492>
- Toth y Turyshev, *Resolved imaging of exoplanets with the solar gravitational lens*, MNRAS 515, 6122 (2022): <https://academic.oup.com/mnras/article/515/4/6122/6652111>
- Toth y Turyshev, *Imaging rotating and orbiting exoplanets with the solar gravitational lens*, arXiv:2306.07832: <https://arxiv.org/pdf/2306.07832>
- Turyshev y Toth, *Navigating stellar wobbles for imaging with the solar gravitational lens*, arXiv:2112.03019: <https://www.arxiv.org/abs/2112.03019>
- Turyshev et al., *Direct multipixel imaging and spectroscopy of an exoplanet with a solar gravity lens mission* (NIAC Phase II), arXiv:2002.11871: <https://arxiv.org/pdf/2002.11871>
- Friedman et al. / Helvajian et al., *Mission architecture to reach and operate at the focal region of the SGL*, J. Spacecraft and Rockets: <https://arc.aiaa.org/doi/10.2514/1.A35493>; *A mission to nature's telescope*, arXiv:2107.11473: <https://arxiv.org/pdf/2107.11473>

**Nota sobre las fuentes:** los valores de la literatura salen de búsquedas, no de leer los papers completos; desde esta sesión no tengo acceso a arxiv.org. Antes de cerrar cada corrección hay que verificarlos contra el texto original.
