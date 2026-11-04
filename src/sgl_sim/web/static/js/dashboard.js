/* sgl-sim mission dashboard. Talks to the Flask API; all physics runs server-side. */
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const css = getComputedStyle(document.documentElement);
  const C = Object.fromEntries(
    ["void", "surface", "raised", "rule", "ink", "dim", "faint", "sol", "ice", "flare"].map((k) => [k, css.getPropertyValue(`--${k}`).trim()])
  );
  const FONT = '12px "IBM Plex Sans", system-ui, sans-serif';

  // ------------------------------------------------------------------ utils
  const sup = (n) => String(n).replace(/-/g, "⁻").replace(/\d/g, (c) => "⁰¹²³⁴⁵⁶⁷⁸⁹"[c]);
  function sci(x, d = 2) {
    if (!isFinite(x) || x === 0) return String(x);
    const e = Math.floor(Math.log10(Math.abs(x)));
    if (e >= -2 && e < 5) return x.toLocaleString("en", { maximumFractionDigits: d });
    return `${(x / 10 ** e).toFixed(d)} × 10${sup(e)}`;
  }
  const num = (x, d = 1) => Number(x).toLocaleString("en", { minimumFractionDigits: d, maximumFractionDigits: d });
  function length(m) {
    const a = Math.abs(m);
    if (a >= 1e6) return `${num(m / 1e3, 0)} km`;
    if (a >= 1e3) return `${num(m / 1e3, 1)} km`;
    if (a >= 1) return `${num(m, 1)} m`;
    return `${num(m * 100, 2)} cm`;
  }

  let toastTimer = null;
  function toast(msg) {
    const t = $("toast");
    t.textContent = msg;
    t.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { t.hidden = true; }, 3500);
  }

  async function api(path, body) {
    const opts = body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
    const res = await fetch(path, opts);
    let data;
    try { data = await res.json(); } catch (_) { throw new Error(`${path} returned an unreadable response`); }
    if (!res.ok || data.status === "error") throw new Error(data.message || `${path} returned ${res.status}`);
    return data;
  }

  function debounce(fn, ms) {
    let t = null;
    return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
  }

  /** Canvas sized to its box at device pixel ratio; render() redraws on next frame. */
  function scene(canvas, draw) {
    const ctx = canvas.getContext("2d");
    const s = { w: 0, h: 0, ctx, draw, render };
    let queued = false;
    function render() {
      if (queued) return;
      queued = true;
      requestAnimationFrame(() => {
        queued = false;
        if (s.w > 0 && s.h > 0) { ctx.clearRect(0, 0, s.w, s.h); draw(ctx, s.w, s.h); }
      });
    }
    new ResizeObserver(() => {
      const r = canvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      s.w = r.width; s.h = r.height;
      canvas.width = Math.round(r.width * dpr);
      canvas.height = Math.round(r.height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      render();
    }).observe(canvas);
    return s;
  }

  function glow(ctx, x, y, r, rgba) {
    const g = ctx.createRadialGradient(x, y, 0, x, y, r);
    g.addColorStop(0, rgba);
    g.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.arc(x, y, r, 0, 2 * Math.PI); ctx.fill();
  }

  /** Piecewise-linear colour ramp; stops are [t, [r,g,b]]. */
  function ramp(stops) {
    return (t) => {
      t = Math.max(0, Math.min(1, t));
      for (let i = 1; i < stops.length; i++) {
        if (t <= stops[i][0]) {
          const [t0, a] = stops[i - 1];
          const [t1, b] = stops[i];
          const f = (t - t0) / (t1 - t0 || 1);
          return a.map((v, k) => Math.round(v + (b[k] - v) * f));
        }
      }
      return stops[stops.length - 1][1];
    };
  }
  // Albedo maps: dark → starlight blue → warm white.
  const albedo = ramp([[0, [23, 27, 36]], [0.35, [52, 84, 130]], [0.7, [169, 210, 255]], [1, [255, 240, 214]]]);
  // Heat maps (brighter = better): dark → deep amber → sol.
  const heat = ramp([[0, [23, 27, 36]], [0.5, [122, 82, 28]], [1, [255, 194, 75]]]);

  /** Draws a 2D array as square pixels filling a w×h box. */
  function drawMatrix(ctx, w, h, M, cmap, lo, hi, flipY = false, smooth = false) {
    const ny = M.length;
    const nx = M[0].length;
    const off = document.createElement("canvas");
    off.width = nx; off.height = ny;
    const octx = off.getContext("2d");
    const img = octx.createImageData(nx, ny);
    for (let j = 0; j < ny; j++) {
      const row = M[flipY ? ny - 1 - j : j];
      for (let i = 0; i < nx; i++) {
        const [r, g, b] = cmap((row[i] - lo) / (hi - lo || 1));
        const k = 4 * (j * nx + i);
        img.data[k] = r; img.data[k + 1] = g; img.data[k + 2] = b; img.data[k + 3] = 255;
      }
    }
    octx.putImageData(img, 0, 0);
    ctx.imageSmoothingEnabled = smooth;
    ctx.drawImage(off, 0, 0, w, h);
  }
  const flat = (M) => M.flat ? M.flat() : [].concat(...M);
  const minmax = (M) => { const f = flat(M); return [Math.min(...f), Math.max(...f)]; };

  // ------------------------------------------------------------------ state
  const P = {
    lens_type: "star", mass_solar: 1, z_rec_au: 650, j2: 2.2e-7, wavelength_um: 1,
    aperture_m: 1, t_int_days: 1, distance_source_pc: 1.3, x0_m: 0, y0_m: 0,
  };
  let sim = null;
  let ephem = null;
  let trade = null;
  let sky = null;
  let pendingCusp = false;

  const sliders = [
    ["p-mass", "o-mass", "mass_solar", (v) => `${num(v, 1)} M☉`, 1],
    ["p-z", "o-z", "z_rec_au", (v) => `${num(v, 0)} AU`, 1],
    ["p-j2", "o-j2", "j2", (v) => `${num(v, 1)} × 10⁻⁷`, 1e-7],
    ["p-lam", "o-lam", "wavelength_um", (v) => `${num(v, 2)} µm`, 1],
    ["p-ap", "o-ap", "aperture_m", (v) => `${num(v, 2)} m`, 1],
    ["p-tint", "o-tint", "t_int_days", (v) => `${num(v, 1)} d`, 1],
    ["p-dist", "o-dist", "distance_source_pc", (v) => `${num(v, 2)} pc`, 1],
  ];

  function syncInputs() {
    $("p-lens").value = P.lens_type;
    for (const [id, out, key, fmt, k] of sliders) {
      $(id).value = P[key] / k;
      $(out).textContent = fmt(P[key] / k);
    }
    $("p-j2").disabled = P.lens_type === "black_hole";
  }

  function readInputs() {
    P.lens_type = $("p-lens").value;
    for (const [id, out, key, fmt, k] of sliders) {
      const v = +$(id).value;
      P[key] = v * k;
      $(out).textContent = fmt(v);
    }
    $("p-j2").disabled = P.lens_type === "black_hole";
  }

  const query = () => new URLSearchParams(Object.entries(P).map(([k, v]) => [k, String(v)])).toString();

  // ------------------------------------------------------------------ simulate
  let simSeq = 0;
  const runSim = debounce(async () => {
    const seq = ++simSeq;
    $("busy").textContent = "Updating…";
    try {
      const data = await api("/api/simulate", P);
      if (seq !== simSeq) return;
      sim = data;
      if (pendingCusp) {
        pendingCusp = false;
        P.x0_m = 0.97 * sim.a_caustic_m;
        P.y0_m = 0;
        runSim();
        return;
      }
      renderAll();
      $("busy").textContent = "";
    } catch (e) {
      $("busy").textContent = "";
      toast(`Simulation failed: ${e.message}`);
    }
  }, 120);

  function renderAll() {
    renderRuler();
    renderKpis();
    rays.render(); psf.render(); detector.render();
    astroid.render(); ring.render(); renderCausticText();
    gt.render(); noisy.render(); recon.render(); renderImagingText();
    tradeScene.render();
    for (const fmt of ["fits", "csv", "json"]) $(`dl-${fmt}`).href = `/api/export_${fmt}?${query()}`;
  }

  // ------------------------------------------------------------------ ruler
  function renderRuler() {
    const svg = $("ruler");
    const w = svg.getBoundingClientRect().width;
    const h = 72;
    if (!w || !sim) return;
    svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
    const isBh = P.lens_type === "black_hole";
    const zmin = sim.z_min_au;
    const zmax = Math.max(1200, P.z_rec_au * 1.15);
    const x0 = 14;
    const x1 = w - 8;
    const X = (z) => x0 + (Math.max(0, Math.min(z, zmax)) / zmax) * (x1 - x0);
    const y = 40;
    const parts = [];
    parts.push(`<line x1="0" y1="${y}" x2="${w}" y2="${y}" stroke="${C.rule}" stroke-width="1"/>`);
    const step = zmax > 2000 ? 500 : 250;
    for (let z = step; z < zmax; z += step) {
      parts.push(`<line x1="${X(z)}" y1="${y + 6}" x2="${X(z)}" y2="${y + 11}" stroke="${C.faint}"/>`);
      parts.push(`<text x="${X(z)}" y="${y + 26}" fill="${C.faint}" font-size="12" text-anchor="middle">${z} AU</text>`);
    }
    parts.push(`<line x1="${X(zmin)}" y1="${y}" x2="${x1}" y2="${y}" stroke="${C.sol}" stroke-width="4" stroke-linecap="round"/>`);
    parts.push(`<circle cx="${x0}" cy="${y}" r="7" fill="${isBh ? C.void : C.sol}" stroke="${isBh ? C.ink : "none"}" stroke-width="1.5"/>`);
    parts.push(`<text x="${x0 - 6}" y="${y - 16}" fill="${C.dim}" font-size="12">${isBh ? "Black hole" : "Sun"}</text>`);
    if (!isBh && X(zmin) - x0 > 70 && Math.abs(X(P.z_rec_au) - X(zmin)) > 150) {
      parts.push(`<line x1="${X(zmin)}" y1="${y - 14}" x2="${X(zmin)}" y2="${y}" stroke="${C.sol}" stroke-dasharray="2 3"/>`);
      parts.push(`<text x="${X(zmin)}" y="${y - 18}" fill="${C.sol}" font-size="12" text-anchor="middle">focal line begins</text>`);
    }
    const xs = X(P.z_rec_au);
    const ok = P.z_rec_au >= zmin;
    const col = ok ? C.ink : C.flare;
    parts.push(`<path d="M ${xs + 9} ${y} L ${xs - 6} ${y - 7} L ${xs - 6} ${y + 7} Z" fill="${col}"/>`);
    const anchor = xs > w - 120 ? "end" : "middle";
    parts.push(`<text x="${xs}" y="${y - 16}" fill="${col}" font-size="12" font-weight="500" text-anchor="${anchor}">spacecraft ${num(P.z_rec_au, 0)} AU</text>`);
    svg.innerHTML = parts.join("");
  }
  new ResizeObserver(() => renderRuler()).observe($("ruler"));

  function renderKpis() {
    $("k-zmin").textContent = P.lens_type === "black_hole" ? `${sci(sim.z_min_au * 1.495978707e11 / 1e3, 1)} km` : `${num(sim.z_min_au, 1)} AU`;
    $("k-theta").textContent = `${num(sim.theta_E_arcsec, 2)}″`;
    $("k-mu").textContent = sci(sim.mu_max);
    $("k-snr").textContent = sci(sim.snr, 1);
    $("k-dimg").textContent = `${num(sim.image_cylinder_km, 1)} km`;
    $("t-vorb").textContent = `${num(sim.orbital_velocity_m_s / 1e3, 2)} km/s`;
    $("t-period").textContent = `${num(sim.orbital_period_years, 0)} yr`;
    $("t-hover").textContent = `${num(sim.delta_v_hover_m_s, 2)} m/s`;
    $("t-scan").textContent = `${sci(sim.delta_v_scan_m_s, 2)} m/s`;
    $("t-total").textContent = `${num(sim.delta_v_total_m_s, 2)} m/s`;
    $("o-theta").textContent = `${num(sim.theta_E_arcsec, 3)}″`;
    $("o-bring").textContent = `${num(sim.b_ring_r_sun, 2)} R☉`;
    $("o-core").textContent = length(sim.psf_core_m);
  }

  // ------------------------------------------------------------------ optics
  const rays = scene($("cv-rays"), (ctx, w, h) => {
    if (!sim) return;
    if (P.lens_type === "black_hole") return drawBhRays(ctx, w, h);
    const zmin = sim.z_min_au;
    const zmax = Math.max(1200, P.z_rec_au * 1.15);
    const xL = w * 0.1;
    const X = (z) => xL + (z / zmax) * (w - xL - 12);
    const yA = h / 2;
    const bMax = 2.6;
    const Y = (b) => yA - (b / bMax) * (h * 0.42);
    const rDisp = (h * 0.42) / bMax;
    $("rays-note").textContent = "Weak-field bending by the star; vertical scale exaggerated";

    ctx.strokeStyle = C.rule; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(0, yA); ctx.lineTo(w, yA); ctx.stroke();
    ctx.font = FONT; ctx.fillStyle = C.faint; ctx.textAlign = "center";
    for (let z = 250; z < zmax; z += 250) ctx.fillText(`${z} AU`, X(z), h - 10);

    for (const r of sim.ray_bundle) {
      for (const s of [1, -1]) {
        const b = s * r.b_r_sun;
        const y0 = Y(b);
        ctx.lineWidth = 1.2;
        if (r.status === "blocked_by_star") {
          const dy = Math.abs(b) * rDisp;
          const xh = xL - Math.sqrt(Math.max(rDisp * rDisp - dy * dy, 0));
          ctx.strokeStyle = C.flare; ctx.globalAlpha = 0.55;
          ctx.beginPath(); ctx.moveTo(0, y0); ctx.lineTo(xh, y0); ctx.stroke();
          ctx.globalAlpha = 1;
          continue;
        }
        const xf = X(r.z_focus_au);
        const slope = (yA - y0) / (xf - xL);
        ctx.strokeStyle = C.ice; ctx.globalAlpha = 0.5;
        ctx.beginPath(); ctx.moveTo(0, y0); ctx.lineTo(xL, y0); ctx.stroke();
        const g = ctx.createLinearGradient(xL, 0, xf, 0);
        g.addColorStop(0, C.ice); g.addColorStop(1, C.sol);
        ctx.strokeStyle = g; ctx.globalAlpha = 0.8;
        ctx.beginPath(); ctx.moveTo(xL, y0); ctx.lineTo(w, y0 + slope * (w - xL)); ctx.stroke();
        ctx.globalAlpha = 1;
      }
    }
    glow(ctx, xL, yA, rDisp * 2.4, "rgba(255,194,75,0.3)");
    ctx.fillStyle = C.sol;
    ctx.beginPath(); ctx.arc(xL, yA, rDisp, 0, 2 * Math.PI); ctx.fill();

    ctx.save(); ctx.shadowColor = C.sol; ctx.shadowBlur = 10; ctx.strokeStyle = C.sol; ctx.lineWidth = 4;
    ctx.beginPath(); ctx.moveTo(X(zmin), yA); ctx.lineTo(w, yA); ctx.stroke(); ctx.restore();

    const xs = X(P.z_rec_au);
    const ok = P.z_rec_au >= zmin;
    ctx.fillStyle = ok ? C.ink : C.flare;
    ctx.beginPath(); ctx.moveTo(xs + 9, yA); ctx.lineTo(xs - 6, yA - 7); ctx.lineTo(xs - 6, yA + 7); ctx.closePath(); ctx.fill();
  });

  function drawBhRays(ctx, w, h) {
    $("rays-note").textContent = "Strong-field null geodesics around a Schwarzschild black hole, in units of R_s";
    const xr = [-16, 40];
    const s = (w - 24) / (xr[1] - xr[0]);
    const X = (x) => 12 + (x - xr[0]) * s;
    const Y = (y) => h / 2 - y * s;
    ctx.strokeStyle = C.rule; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(0, h / 2); ctx.lineTo(w, h / 2); ctx.stroke();
    ctx.save();
    ctx.beginPath(); ctx.rect(0, 0, w, h); ctx.clip();
    for (const r of sim.ray_bundle) {
      const captured = r.status !== "escaped";
      for (const sg of [1, -1]) {
        ctx.beginPath();
        r.x_rs.forEach((x, i) => { const px = X(x), py = Y(sg * r.y_rs[i]); i ? ctx.lineTo(px, py) : ctx.moveTo(px, py); });
        ctx.strokeStyle = captured ? C.flare : C.ice;
        ctx.globalAlpha = 0.7; ctx.lineWidth = 1.2; ctx.stroke(); ctx.globalAlpha = 1;
      }
    }
    ctx.restore();
    ctx.setLineDash([3, 4]); ctx.strokeStyle = C.sol;
    ctx.beginPath(); ctx.arc(X(0), Y(0), 1.5 * s, 0, 2 * Math.PI); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle = "#000"; ctx.strokeStyle = C.dim;
    ctx.beginPath(); ctx.arc(X(0), Y(0), Math.max(1 * s, 3), 0, 2 * Math.PI); ctx.fill(); ctx.stroke();
    ctx.font = FONT; ctx.fillStyle = C.sol; ctx.textAlign = "left";
    ctx.fillText("photon sphere", X(0) + 1.5 * s + 6, Y(0) - 1.5 * s);
  }

  const psf = scene($("cv-psf"), (ctx, w, h) => {
    if (!sim) return;
    const L = 46, R = 36, T = 20, B = 34;
    const rho = sim.psf_rho_m;
    const I = sim.psf_j0_sq;
    const rmax = rho[rho.length - 1];
    const unit = rmax < 2 ? 100 : 1;
    const uLabel = unit === 100 ? "cm" : "m";
    const X = (r) => L + (r / rmax) * (w - L - R);
    const Y = (v) => h - B - v * (h - T - B);
    ctx.font = FONT; ctx.strokeStyle = C.rule; ctx.fillStyle = C.faint; ctx.lineWidth = 1;
    ctx.textAlign = "right";
    for (const v of [0, 0.5, 1]) {
      ctx.beginPath(); ctx.moveTo(L, Y(v)); ctx.lineTo(w - R, Y(v)); ctx.stroke();
      ctx.fillText(v.toFixed(1), L - 8, Y(v) + 4);
    }
    ctx.textAlign = "center";
    const span = rmax * unit;
    const raw = span / 5;
    const mag = 10 ** Math.floor(Math.log10(raw));
    const step = [1, 2, 5, 10].map((f) => f * mag).find((v) => v >= raw);
    for (let v = 0; v <= span + 1e-9; v += step) {
      const last = v + step > span + 1e-9;
      ctx.fillText(`${+v.toFixed(6)}${last ? ` ${uLabel}` : ""}`, X(v / unit), h - B + 18);
    }
    ctx.beginPath();
    rho.forEach((r, i) => (i ? ctx.lineTo(X(r), Y(I[i])) : ctx.moveTo(X(r), Y(I[i]))));
    ctx.strokeStyle = C.sol; ctx.lineWidth = 2; ctx.stroke();
    const c = sim.psf_core_m;
    ctx.setLineDash([3, 4]); ctx.strokeStyle = C.ice;
    ctx.beginPath(); ctx.moveTo(X(c), Y(0)); ctx.lineTo(X(c), Y(0.85)); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle = C.ice; ctx.textAlign = "left";
    ctx.fillText(`core ${length(c)}`, X(c) + 6, Y(0.8));
  });

  const detector = scene($("cv-detector"), (ctx, w, h) => {
    if (!sim) return;
    const cx = w / 2, cy = h / 2;
    const R = Math.min(w, h) * 0.3;
    const corona = ctx.createRadialGradient(cx, cy, R * 0.5, cx, cy, R * 1.6);
    corona.addColorStop(0, "rgba(255,194,75,0.22)");
    corona.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = corona; ctx.fillRect(0, 0, w, h);
    drawRingImages(ctx, cx, cy, R, 0);
    ctx.fillStyle = "#06080c"; ctx.strokeStyle = C.rule;
    ctx.beginPath(); ctx.arc(cx, cy, R * 0.62, 0, 2 * Math.PI); ctx.fill(); ctx.stroke();
    ctx.font = FONT; ctx.fillStyle = C.faint; ctx.textAlign = "center";
    ctx.fillText("coronagraph", cx, cy + 4);
  });

  /** Ring halo from ring_profile plus glowing image spots. */
  function drawRingImages(ctx, cx, cy, R, haloGain) {
    const prof = sim.ring_profile;
    const n = prof.length;
    ctx.lineWidth = 3;
    for (let i = 0; i < n; i++) {
      const a0 = (2 * Math.PI * i) / n;
      const a1 = (2 * Math.PI * (i + 1.2)) / n;
      ctx.strokeStyle = `rgba(255,194,75,${0.12 + 0.88 * prof[i]})`;
      ctx.beginPath(); ctx.arc(cx, cy, R, -a1, -a0); ctx.stroke();
    }
    if (haloGain) {
      ctx.beginPath();
      for (let i = 0; i <= n; i++) {
        const a = (2 * Math.PI * (i % n)) / n;
        const rr = R * (1 + haloGain * prof[i % n]);
        const x = cx + rr * Math.cos(a), y = cy - rr * Math.sin(a);
        i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
      }
      ctx.strokeStyle = C.sol; ctx.globalAlpha = 0.6; ctx.lineWidth = 1.5; ctx.stroke(); ctx.globalAlpha = 1;
    }
    const mx = Math.max(...sim.image_intensities, 1e-9);
    sim.image_angles_deg.forEach((deg, i) => {
      const a = (deg * Math.PI) / 180;
      const m = sim.image_intensities[i] / mx;
      const x = cx + R * Math.cos(a), y = cy - R * Math.sin(a);
      glow(ctx, x, y, 10 + 18 * m, "rgba(255,194,75,0.85)");
      ctx.fillStyle = C.ink; ctx.beginPath(); ctx.arc(x, y, 2 + 2 * m, 0, 2 * Math.PI); ctx.fill();
    });
  }

  // ------------------------------------------------------------------ caustic
  const HALF = 1.6; // plane half-width in units of a_caustic
  const astroid = scene($("cv-astroid"), (ctx, w, h) => {
    if (!sim) return;
    const a = sim.a_caustic_m || 1;
    const s = (Math.min(w, h) - 40) / (2 * HALF);
    const cx = w / 2, cy = h / 2;
    astroid.map = { cx, cy, s, a };
    ctx.strokeStyle = C.rule; ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(cx - HALF * s, cy); ctx.lineTo(cx + HALF * s, cy);
    ctx.moveTo(cx, cy - HALF * s); ctx.lineTo(cx, cy + HALF * s);
    ctx.stroke();
    if (sim.a_caustic_m > 0) {
      ctx.beginPath();
      for (let i = 0; i <= 240; i++) {
        const t = (2 * Math.PI * i) / 240;
        const x = cx + s * Math.cos(t) ** 3, y = cy - s * Math.sin(t) ** 3;
        i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
      }
      ctx.fillStyle = "rgba(255,194,75,0.08)"; ctx.fill();
      ctx.strokeStyle = C.sol; ctx.lineWidth = 2; ctx.stroke();
    }
    const rx = cx + (P.x0_m / a) * s, ry = cy - (P.y0_m / a) * s;
    const mx = Math.max(...sim.image_intensities, 1e-9);
    sim.image_angles_deg.forEach((deg, i) => {
      const ang = (deg * Math.PI) / 180;
      ctx.strokeStyle = C.sol; ctx.globalAlpha = 0.35 + 0.6 * sim.image_intensities[i] / mx; ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.moveTo(rx, ry); ctx.lineTo(rx + 28 * Math.cos(ang), ry - 28 * Math.sin(ang)); ctx.stroke();
    });
    ctx.globalAlpha = 1;
    glow(ctx, rx, ry, 18, "rgba(169,210,255,0.6)");
    ctx.fillStyle = C.ink; ctx.beginPath(); ctx.arc(rx, ry, 4.5, 0, 2 * Math.PI); ctx.fill();
    ctx.font = FONT; ctx.fillStyle = C.faint; ctx.textAlign = "left";
    ctx.fillText("±1.6 a", 10, h - 10);
  });

  const ring = scene($("cv-ring"), (ctx, w, h) => {
    if (!sim) return;
    const cx = w / 2, cy = h / 2;
    const R = Math.min(w, h) * 0.32;
    ctx.strokeStyle = C.rule; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.arc(cx, cy, R, 0, 2 * Math.PI); ctx.stroke();
    drawRingImages(ctx, cx, cy, R, 0.28);
    ctx.fillStyle = "#06080c"; ctx.strokeStyle = C.rule;
    ctx.beginPath(); ctx.arc(cx, cy, R * 0.55, 0, 2 * Math.PI); ctx.fill(); ctx.stroke();
  });

  function renderCausticText() {
    const a = sim.a_caustic_m;
    const st = $("c-status");
    const map = {
      inside: ["sol", "Inside the astroid: four images form an Einstein cross."],
      outside: ["ice", "Outside the astroid: two images remain."],
      cusp_boundary: ["flare", "On the caustic: images are merging."],
      unperturbed: ["ice", "No oblateness: the planet's light spreads into a full ring."],
    };
    const [tone, text] = map[sim.regime] || ["ice", sim.regime];
    st.dataset.tone = tone;
    st.textContent = text;
    $("c-n").textContent = sim.num_images;
    $("c-xy").textContent = a > 0 ? `(${num(P.x0_m / a, 2)}, ${num(P.y0_m / a, 2)}) a` : "–";
    $("c-a").textContent = length(a);
    $("c-ang").textContent = sim.image_angles_deg.map((d) => `${num(d, 0)}°`).join(", ") || "–";
  }

  (function bindAstroidDrag() {
    const cv = $("cv-astroid");
    let drag = false;
    const set = (u, v) => {
      const lim = HALF - 0.03;
      const a = astroid.map ? astroid.map.a : sim.a_caustic_m;
      P.x0_m = Math.max(-lim, Math.min(lim, u)) * a;
      P.y0_m = Math.max(-lim, Math.min(lim, v)) * a;
      astroid.render();
      runSim();
    };
    const fromEvent = (e) => {
      const r = cv.getBoundingClientRect();
      const m = astroid.map;
      if (!m) return;
      set((e.clientX - r.left - m.cx) / m.s, -(e.clientY - r.top - m.cy) / m.s);
    };
    cv.addEventListener("pointerdown", (e) => { drag = true; cv.setPointerCapture(e.pointerId); fromEvent(e); });
    cv.addEventListener("pointermove", (e) => { if (drag) fromEvent(e); });
    cv.addEventListener("pointerup", () => { drag = false; });
    cv.addEventListener("pointercancel", () => { drag = false; });
    cv.addEventListener("keydown", (e) => {
      const d = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, 1], ArrowDown: [0, -1] }[e.key];
      if (!d || !sim) return;
      e.preventDefault();
      const step = e.shiftKey ? 0.2 : 0.05;
      const a = sim.a_caustic_m;
      set(P.x0_m / a + d[0] * step, P.y0_m / a + d[1] * step);
    });
  })();

  // ------------------------------------------------------------------ imaging
  const imgScene = (id, key) => scene($(id), (ctx, w, h) => {
    if (!sim) return;
    const [lo, hi] = minmax(sim.ground_truth);
    const M = sim[key];
    const [mlo, mhi] = key === "ground_truth" ? [lo, hi] : minmax(M);
    drawMatrix(ctx, w, h, M, albedo, mlo, mhi);
  });
  const gt = imgScene("cv-gt", "ground_truth");
  const noisy = imgScene("cv-noisy", "convolved_noisy");
  const recon = imgScene("cv-recon", "deconvolved");

  function renderImagingText() {
    $("i-noisy").textContent = `SNR ${sci(sim.snr, 1)} · error ${num(sim.rmse_noisy, 3)}`;
    $("i-recon").textContent = `error ${num(sim.rmse_deconvolved, 3)} · similarity ${num(sim.ssim_deconvolved, 2)}`;
  }

  const tradeScene = scene($("cv-trade"), (ctx, w, h) => {
    if (!trade) return;
    const L = 56, R = 16, T = 12, B = 40;
    const M = trade.snr_matrix.map((row) => row.map((v) => Math.log10(Math.max(v, 1e-30))));
    // snr_matrix is indexed [z][aperture]; draw z on x, aperture on y.
    const nz = trade.z_au_grid.length, na = trade.aperture_m_grid.length;
    const T2 = [];
    for (let j = 0; j < na; j++) { T2.push([]); for (let i = 0; i < nz; i++) T2[j].push(M[i][j]); }
    const [lo, hi] = minmax(T2);
    ctx.save(); ctx.translate(L, T);
    drawMatrix(ctx, w - L - R, h - T - B, T2, heat, lo, hi, true);
    ctx.restore();
    ctx.font = FONT; ctx.fillStyle = C.faint; ctx.textAlign = "center";
    const zg = trade.z_au_grid, ag = trade.aperture_m_grid;
    const X = (z) => L + ((z - zg[0]) / (zg[nz - 1] - zg[0])) * (w - L - R);
    const Y = (a) => h - B - ((a - ag[0]) / (ag[na - 1] - ag[0])) * (h - T - B);
    [zg[0], (zg[0] + zg[nz - 1]) / 2, zg[nz - 1]].forEach((z, i) => {
      ctx.textAlign = ["left", "center", "right"][i];
      ctx.fillText(`${num(z, 0)} AU`, X(z), h - B + 18);
    });
    ctx.textAlign = "right";
    for (const a of [ag[0], (ag[0] + ag[na - 1]) / 2, ag[na - 1]]) ctx.fillText(`${num(a, 1)} m`, L - 8, Y(a) + 4);
    ctx.textAlign = "left";
    ctx.fillText("Spacecraft distance →", L, h - 6);
    if (P.z_rec_au >= zg[0] && P.z_rec_au <= zg[nz - 1] && P.aperture_m >= ag[0] && P.aperture_m <= ag[na - 1]) {
      ctx.strokeStyle = C.ink; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(X(P.z_rec_au), Y(P.aperture_m), 8, 0, 2 * Math.PI); ctx.stroke();
    }
  });

  async function loadTrade() {
    try {
      trade = await api(`/api/research_analysis?distance_source_pc=${P.distance_source_pc}`);
      tradeScene.render();
    } catch (e) { toast(`Trade study failed: ${e.message}`); }
  }
  const loadTradeSoon = debounce(loadTrade, 300);

  // ------------------------------------------------------------------ targets
  let targets = [];
  async function loadTargets() {
    try {
      targets = await api("/api/targets");
      const sel = $("p-target");
      sel.innerHTML = `<option value="">Custom distance</option>` +
        targets.map((t) => `<option value="${t.name}">${t.name} (${num(t.distance_pc, 2)} pc)</option>`).join("");
      $("target-list").innerHTML = targets.map((t) => `<option value="${t.name}">`).join("");
      sel.value = "Proxima Centauri b";
      $("t-query").value = "Proxima Centauri b";
      loadEphem();
    } catch (e) { toast(`Could not load targets: ${e.message}`); }
  }

  async function loadEphem() {
    const q = $("t-query").value.trim();
    if (!q) return;
    $("busy").textContent = "Locating target…";
    try {
      const res = await api("/api/target_ephemeris", { target: q, z_rec_au: P.z_rec_au, arrival_year: +$("t-year").value || null });
      ephem = res.data;
      renderEphem();
      runBlur();
    } catch (e) {
      toast(`Could not locate “${q}”. Try a catalogue name such as TRAPPIST-1 e.`);
    } finally { $("busy").textContent = ""; }
  }

  function renderEphem() {
    const e = ephem;
    $("t-desc").textContent = e.target_description || "";
    $("e-host").textContent = e.hostname;
    $("e-radec").textContent = `${num(e.target_ra_deg, 2)}°, ${num(e.target_dec_deg, 2)}°`;
    $("e-dist").textContent = `${num(e.target_distance_pc, 2)} pc (${num(e.target_distance_ly, 2)} ly)`;
    $("e-const").textContent = e.target_constellation;
    $("e-pm").textContent = `${num(e.target_pm_total_mas_yr, 0)} mas/yr`;
    $("e-rad").textContent = e.target_pl_rade ? `${num(e.target_pl_rade, 2)} Earth radii` : "unknown";
    $("e-tel").textContent = `${num(e.telescope_ra_deg, 2)}°, ${num(e.telescope_dec_deg, 2)}°`;
    $("e-telconst").textContent = e.telescope_constellation;
    $("e-xyz").textContent = `${num(e.x_au, 0)}, ${num(e.y_au, 0)}, ${num(e.z_au, 0)} AU`;
    $("e-norm").textContent = `${num(e.vector_norm_au, 0)} AU`;
    $("e-lon").textContent = `${num(e.ecliptic_lon_deg, 1)}°`;
    $("e-inc").textContent = `${num(e.ecliptic_inclination_deg, 1)}°`;
    $("e-delay").textContent = `${num(e.light_delay_days, 2)} days`;
    $("e-cruise").textContent = `${num(e.cruise_time_years, 1)} years`;
    $("e-dimg").textContent = `${num(e.image_diameter_km, 1)} km`;
    $("e-drift").textContent = `${num(e.proper_motion_drift_m_s, 1)} m/s`;
    $("e-sweep").textContent = `${num(e.annual_lateral_drift_km, 0)} km`;
    $("e-src").textContent = e.source;
  }

  $("target-form").addEventListener("submit", (ev) => { ev.preventDefault(); loadEphem(); });
  $("p-target").addEventListener("change", () => {
    const t = targets.find((x) => x.name === $("p-target").value);
    if (!t) return;
    P.distance_source_pc = Math.max(1, Math.min(35, t.distance_pc));
    syncInputs();
    $("t-query").value = t.name;
    runSim(); loadTradeSoon(); loadEphem();
  });

  // ------------------------------------------------------------------ triage
  const skyScene = scene($("cv-sky"), (ctx, w, h) => {
    if (!sky) return;
    drawMatrix(ctx, w, h, sky.efficiency_matrix, heat, 0, 1, true, true);
    const X = (ra) => (ra / 360) * w;
    const Y = (dec) => h / 2 - (dec / 90) * (h / 2);
    ctx.strokeStyle = "rgba(233,236,242,0.15)"; ctx.lineWidth = 1;
    for (const dec of [-60, -30, 0, 30, 60]) { ctx.beginPath(); ctx.moveTo(0, Y(dec)); ctx.lineTo(w, Y(dec)); ctx.stroke(); }
    ctx.font = FONT; ctx.textAlign = "left";
    for (const c of sky.candidates) {
      const x = X(c.tel_ra), y = Y(c.tel_dec);
      ctx.fillStyle = C.ink; ctx.beginPath(); ctx.arc(x, y, 3.5, 0, 2 * Math.PI); ctx.fill();
      ctx.strokeStyle = C.void; ctx.lineWidth = 1.5; ctx.stroke();
    }
    skyScene.X = X; skyScene.Y = Y;
  });

  async function loadSky() {
    try {
      sky = (await api("/api/sky_efficiency")).data;
      skyScene.render();
    } catch (e) { toast(`Sky map failed: ${e.message}`); }
  }

  $("cv-sky").addEventListener("pointermove", (e) => {
    if (!sky) return;
    const r = e.currentTarget.getBoundingClientRect();
    const ra = ((e.clientX - r.left) / r.width) * 360;
    const dec = 90 - ((e.clientY - r.top) / r.height) * 180;
    const i = Math.min(sky.n_ra - 1, Math.max(0, Math.floor((ra / 360) * sky.n_ra)));
    const j = Math.min(sky.n_dec - 1, Math.max(0, Math.floor(((dec + 90) / 180) * sky.n_dec)));
    let near = null;
    for (const c of sky.candidates) {
      const dx = (skyScene.X(c.tel_ra) - (e.clientX - r.left));
      const dy = (skyScene.Y(c.tel_dec) - (e.clientY - r.top));
      if (dx * dx + dy * dy < 100) near = c;
    }
    const eff = sky.efficiency_matrix[j][i];
    $("sky-hover").textContent = near
      ? `${near.name}: telescope points to RA ${num(near.tel_ra, 1)}°, Dec ${num(near.tel_dec, 1)}°, ${num(near.dist_pc, 2)} pc`
      : `RA ${num(ra, 0)}°, Dec ${num(dec, 0)}°: efficiency ${num(eff, 2)}`;
  });

  async function evaluate() {
    const body = {
      name: $("ev-name").value || "Custom planet",
      ra_deg: +$("ev-ra").value, dec_deg: +$("ev-dec").value, dist_pc: +$("ev-dist").value,
      radius_earth: +$("ev-rad").value, rot_period_hrs: +$("ev-rot").value,
      proper_motion_mas_yr: +$("ev-pm").value, tidally_locked: $("ev-lock").checked, z_rec_au: P.z_rec_au,
    };
    try {
      const res = await api("/api/evaluate_candidate", body);
      const c = res.candidate;
      $("ev-result").hidden = false;
      $("ev-score").innerHTML = `${num(c.sgl_score, 1)} <small>/ 100</small>`;
      $("ev-tier").textContent = c.tier;
      const bars = [["Signal", c.snr_score], ["Logistics", c.scan_logistics_score], ["Ecliptic access", c.ecliptic_access_score], ["Blur immunity", c.blur_immunity_score]];
      $("ev-bars").innerHTML = bars.map(([k, v]) => `<span>${k}</span><span class="bar"><i style="width:${Math.round(v * 100)}%"></i></span><span>${num(v, 2)}</span>`).join("");
      const al = $("ev-align");
      al.dataset.tone = res.coalignment.is_coaligned ? "sol" : "ice";
      al.textContent = res.coalignment.message;
    } catch (e) { toast(`Scoring failed: ${e.message}`); }
  }
  $("eval-form").addEventListener("submit", (e) => { e.preventDefault(); evaluate(); });

  const blur1 = scene($("cv-blur1"), (ctx, w, h) => { if (blurRes) drawBlur(ctx, w, h, blurRes.single); });
  const blurN = scene($("cv-blurN"), (ctx, w, h) => { if (blurRes) drawBlur(ctx, w, h, blurRes.swarm); });
  let blurRes = null;
  function drawBlur(ctx, w, h, r) {
    const [lo, hi] = minmax(r.ground_truth);
    drawMatrix(ctx, w, h, r.reconstructed_image, albedo, lo, hi);
  }
  const runBlur = debounce(async () => {
    const n = +$("bl-n").value;
    $("o-bl-n").textContent = n;
    try {
      blurRes = await api("/api/swarm_blur_sim", {
        num_satellites: n, planet_rot_period_hours: +$("bl-rot").value || 24,
        distance_source_pc: P.distance_source_pc, z_rec_au: P.z_rec_au, aperture_m: P.aperture_m,
        radius_earth: ephem && ephem.target_pl_rade ? ephem.target_pl_rade : 1.0,
      });
      const cap = (r, title) => `${title}<span>smear ${num(r.eta_blur, 1)}× · scan ${num(r.scan_time_hours, 1)} h · error ${num(r.rmse, 3)}</span>`;
      $("bl-1").innerHTML = cap(blurRes.single, "One spacecraft");
      $("bl-N").innerHTML = cap(blurRes.swarm, `Swarm of ${n}`);
      const s1 = blurRes.single;
      $("bl-need").textContent = s1.sharp_possible
        ? `${num(s1.per_pixel_s, 0)} s per pixel. A sharp 32 × 32 image needs ${num(s1.telescopes_needed, 0)} telescopes (rotation allows ${num(s1.t_max_blur_hours, 2)} h).`
        : `${num(s1.per_pixel_s, 0)} s per pixel is already longer than rotation allows (${num(s1.t_max_blur_hours, 2)} h): telescopes of at least ${num(s1.min_aperture_m, 1)} m are needed.`;
      blur1.render(); blurN.render();
    } catch (e) { toast(`Blur simulation failed: ${e.message}`); }
  }, 150);
  ["bl-n", "bl-rot"].forEach((id) => $(id).addEventListener("input", runBlur));

  async function loadRanking() {
    try {
      const rows = (await api(`/api/ranking?z_rec_au=${P.z_rec_au}`)).data;
      $("rank-body").innerHTML = rows.map((r, i) => {
        const tier = r.tier.startsWith("Tier 1") ? "t1" : r.tier.startsWith("Tier 2") ? "t2" : "t3";
        return `<tr tabindex="0" data-i="${i}"><td>${i + 1}</td><td>${r.name}</td><td class="num">${num(r.dist_pc, 2)} pc</td>
          <td class="num">${num(r.ecliptic_lat_deg, 1)}°</td><td class="num">${num(r.image_diameter_km, 1)} km</td>
          <td class="num"><span class="pill ${tier}">${num(r.sgl_score, 1)}</span></td><td class="tier">${r.tier.replace(/^Tier \d: /, "")}</td></tr>`;
      }).join("");
      const pick = (tr) => {
        const r = rows[+tr.dataset.i];
        $("ev-name").value = r.name; $("ev-ra").value = r.ra_deg; $("ev-dec").value = r.dec_deg;
        $("ev-dist").value = r.dist_pc; $("ev-rad").value = r.radius_earth; $("ev-rot").value = r.rot_period_hrs;
        $("ev-pm").value = r.proper_motion_mas_yr; $("ev-lock").checked = !!r.tidally_locked;
        evaluate();
        $("eval-form").scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "center" });
      };
      $("rank-body").querySelectorAll("tr").forEach((tr) => {
        tr.addEventListener("click", () => pick(tr));
        tr.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(tr); } });
      });
    } catch (e) { toast(`Ranking failed: ${e.message}`); }
  }

  // ------------------------------------------------------------------ tabs
  const tabs = [...document.querySelectorAll('[role="tab"]')];
  function selectTab(tab) {
    for (const t of tabs) {
      const on = t === tab;
      t.setAttribute("aria-selected", on);
      t.tabIndex = on ? 0 : -1;
      $(t.getAttribute("aria-controls")).hidden = !on;
    }
  }
  tabs.forEach((t, i) => {
    t.addEventListener("click", () => selectTab(t));
    t.addEventListener("keydown", (e) => {
      const d = { ArrowRight: 1, ArrowLeft: -1 }[e.key];
      if (!d) return;
      const n = tabs[(i + d + tabs.length) % tabs.length];
      selectTab(n); n.focus();
    });
  });

  // ------------------------------------------------------------------ presets
  const PRESETS = {
    sun: { lens_type: "star", mass_solar: 1, z_rec_au: 650, j2: 2.2e-7, wavelength_um: 1, aperture_m: 1, t_int_days: 1, x0_m: 0, y0_m: 0 },
    cusp: { lens_type: "star", mass_solar: 1, z_rec_au: 650, j2: 2.2e-7, wavelength_um: 1, aperture_m: 1, t_int_days: 1, cusp: true },
    rotator: { lens_type: "star", mass_solar: 1.4, z_rec_au: 700, j2: 2.2e-6, wavelength_um: 0.8, aperture_m: 1.5, t_int_days: 2, x0_m: 0, y0_m: 0 },
    bh: { lens_type: "black_hole", mass_solar: 5, z_rec_au: 650, j2: 0, wavelength_um: 1.5, aperture_m: 2, t_int_days: 1, x0_m: 0, y0_m: 0 },
  };
  document.querySelectorAll("[data-preset]").forEach((b) => b.addEventListener("click", () => {
    document.querySelectorAll("[data-preset]").forEach((x) => x.classList.toggle("active", x === b));
    const p = { ...PRESETS[b.dataset.preset] };
    pendingCusp = !!p.cusp;
    delete p.cusp;
    Object.assign(P, p);
    syncInputs();
    runSim(); loadTradeSoon();
  }));

  // ------------------------------------------------------------------ inputs
  ["p-lens", ...sliders.map((s) => s[0])].forEach((id) => $(id).addEventListener("input", () => {
    readInputs();
    document.querySelectorAll("[data-preset]").forEach((x) => x.classList.remove("active"));
    if (id === "p-dist") { $("p-target").value = ""; loadTradeSoon(); }
    if (id === "p-z") { loadRankingSoon(); }
    runSim();
  }));
  const loadRankingSoon = debounce(loadRanking, 400);

  // ------------------------------------------------------------------ boot
  syncInputs();
  runSim();
  loadTrade();
  loadTargets();
  loadSky();
  loadRanking();
  evaluate();
})();
