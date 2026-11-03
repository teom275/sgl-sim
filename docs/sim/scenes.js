/* sgl-sim web simulator: three canvas scenes driven by physics.js (window.SGL). */
(function () {
  "use strict";
  const S = window.SGL;
  const css = getComputedStyle(document.documentElement);
  const C = {
    void: css.getPropertyValue("--void").trim(),
    surface: css.getPropertyValue("--surface").trim(),
    rule: css.getPropertyValue("--rule").trim(),
    ink: css.getPropertyValue("--ink").trim(),
    dim: css.getPropertyValue("--dim").trim(),
    faint: css.getPropertyValue("--faint").trim(),
    sol: css.getPropertyValue("--sol").trim(),
    ice: css.getPropertyValue("--ice").trim(),
    flare: css.getPropertyValue("--flare").trim(),
  };
  const FONT = '12px "IBM Plex Sans", system-ui, sans-serif';
  const $ = (id) => document.getElementById(id);
  const L10N = window.I18N || { t: (k, v, f) => f, num: (x, d) => Number(x).toFixed(d), lang: "en", onChange() {} };
  const T = (key, vars, fallback) => L10N.t(key, vars, fallback);
  const N = (x, d = 1) => L10N.num(x, d);
  const AU = () => T("unit.au", null, "AU");
  const binds = [];

  // Optional link to the hosted dashboard.
  const cfg = window.SGL_SITE || {};
  if (cfg.DASHBOARD_URL) {
    const a = $("nav-dashboard");
    a.href = cfg.DASHBOARD_URL;
    a.hidden = false;
  }

  /** Keeps a canvas sized to its box at device pixel ratio; calls draw(ctx, w, h). */
  function canvasScene(canvas, draw) {
    const ctx = canvas.getContext("2d");
    const state = { w: 0, h: 0 };
    function resize() {
      const r = canvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      state.w = r.width;
      state.h = r.height;
      canvas.width = Math.round(r.width * dpr);
      canvas.height = Math.round(r.height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      render();
    }
    let queued = false;
    function render() {
      if (queued) return;
      queued = true;
      requestAnimationFrame(() => {
        queued = false;
        if (state.w > 0) draw(ctx, state.w, state.h);
      });
    }
    new ResizeObserver(resize).observe(canvas);
    return { render, state };
  }

  /** Binds a range input to an output element, calling onChange with the value. */
  function bindRange(id, outId, fmt, onChange) {
    const el = $(id);
    const out = $(outId);
    const update = () => { out.textContent = fmt(+el.value); onChange(+el.value); };
    el.addEventListener("input", update);
    const b = { el, update, set(v) { el.value = v; update(); } };
    binds.push(b);
    return b;
  }

  const fmtSci = (x, d = 2) => {
    const e = Math.floor(Math.log10(Math.abs(x)));
    const m = x / Math.pow(10, e);
    const sup = String(e).replace(/-/g, "⁻").replace(/\d/g, (c) => "⁰¹²³⁴⁵⁶⁷⁸⁹"[c]);
    return `${N(m, d)} × 10${sup}`;
  };

  function glowDot(ctx, x, y, r, color, alpha = 1) {
    const g = ctx.createRadialGradient(x, y, 0, x, y, r);
    g.addColorStop(0, color);
    g.addColorStop(1, "rgba(0,0,0,0)");
    ctx.globalAlpha = alpha;
    ctx.fillStyle = g;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, 2 * Math.PI);
    ctx.fill();
    ctx.globalAlpha = 1;
  }

  // ===================================================================
  // Scene 1: focal line
  // ===================================================================
  const focal = { m: 1, r: 1, z: 650, dragging: false, geo: null };
  const Z_MAX = 2000;
  const B_MAX = 2.45;
  const IMPACTS = [];
  for (let i = 0; i < 10; i++) {
    const b = 0.3 + (i * (B_MAX - 0.3)) / 9;
    IMPACTS.push(b, -b);
  }

  const focalScene = canvasScene($("cv-focal"), (ctx, w, h) => {
    const yAxis = h * 0.52;
    const xLens = w * 0.15;
    const xRight = w - 18;
    const xPerAU = (xRight - xLens) / Z_MAX;
    const yPer = (h * 0.4) / B_MAX;
    const X = (z) => xLens + z * xPerAU;
    const Y = (b) => yAxis - b * yPer;
    focal.geo = { X, xPerAU, xLens, yAxis };

    ctx.clearRect(0, 0, w, h);
    ctx.font = FONT;

    // Axis and distance ticks.
    ctx.strokeStyle = C.rule;
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(0, yAxis); ctx.lineTo(w, yAxis); ctx.stroke();
    ctx.fillStyle = C.faint;
    ctx.textAlign = "center";
    for (let z = 500; z <= Z_MAX; z += 500) {
      ctx.beginPath(); ctx.moveTo(X(z), yAxis - 4); ctx.lineTo(X(z), yAxis + 4); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(X(z), h - 6); ctx.lineTo(X(z), h - 12); ctx.stroke();
      ctx.fillText(`${z} ${AU()}`, Math.min(X(z), w - 28), h - 18);
    }

    const zmin = S.zMinAU(focal.m, focal.r);
    const rDisp = focal.r * yPer;

    // Rays.
    for (const b of IMPACTS) {
      const y0 = Y(b);
      if (Math.abs(b) < focal.r) {
        const dy = Math.abs(b) * yPer;
        const xHit = xLens - Math.sqrt(Math.max(rDisp * rDisp - dy * dy, 0));
        ctx.strokeStyle = C.flare;
        ctx.globalAlpha = 0.55;
        ctx.lineWidth = 1.2;
        ctx.beginPath(); ctx.moveTo(0, y0); ctx.lineTo(xHit, y0); ctx.stroke();
        ctx.globalAlpha = 1;
        continue;
      }
      const zf = S.focalDistanceAU(Math.abs(b), focal.m);
      const xf = X(zf);
      const slope = (yAxis - y0) / (xf - xLens);
      let xe = w;
      let ye = y0 + slope * (xe - xLens);
      const lim = h * 0.47;
      if (Math.abs(ye - yAxis) > lim) {
        ye = yAxis + Math.sign(ye - yAxis) * lim;
        xe = xLens + (ye - y0) / slope;
      }
      ctx.lineWidth = 1.2;
      ctx.strokeStyle = C.ice;
      ctx.globalAlpha = 0.5;
      ctx.beginPath(); ctx.moveTo(0, y0); ctx.lineTo(xLens, y0); ctx.stroke();
      const grad = ctx.createLinearGradient(xLens, 0, Math.min(xf, w), 0);
      grad.addColorStop(0, C.ice);
      grad.addColorStop(1, C.sol);
      ctx.strokeStyle = grad;
      ctx.globalAlpha = 0.75;
      ctx.beginPath(); ctx.moveTo(xLens, y0); ctx.lineTo(xe, ye); ctx.stroke();
      ctx.globalAlpha = 1;
    }

    // Lens.
    glowDot(ctx, xLens, yAxis, rDisp * 2.6, "rgba(255,194,75,0.35)");
    ctx.fillStyle = C.sol;
    ctx.beginPath(); ctx.arc(xLens, yAxis, rDisp, 0, 2 * Math.PI); ctx.fill();

    // Focal line and z_min marker.
    if (zmin < Z_MAX) {
      ctx.save();
      ctx.shadowColor = C.sol;
      ctx.shadowBlur = 12;
      ctx.strokeStyle = C.sol;
      ctx.lineWidth = 4;
      ctx.beginPath(); ctx.moveTo(X(zmin), yAxis); ctx.lineTo(w, yAxis); ctx.stroke();
      ctx.restore();
      ctx.setLineDash([3, 4]);
      ctx.strokeStyle = C.sol;
      ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(X(zmin), yAxis - h * 0.36); ctx.lineTo(X(zmin), yAxis + 10); ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = C.sol;
      ctx.textAlign = X(zmin) > w - 120 ? "right" : "left";
      ctx.fillText(`z_min ${zmin.toFixed(0)} ${AU()}`, X(zmin) + (ctx.textAlign === "left" ? 6 : -6), yAxis - h * 0.36 + 12);
    }

    // Spacecraft and the ring rays that reach it.
    const xs = X(focal.z);
    const ok = focal.z >= zmin;
    if (ok) {
      const bR = S.einsteinRing(focal.z, focal.m).bRing_rsun;
      ctx.strokeStyle = C.ink;
      ctx.lineWidth = 2;
      for (const s of [1, -1]) {
        ctx.beginPath(); ctx.moveTo(0, Y(s * bR)); ctx.lineTo(xLens, Y(s * bR)); ctx.lineTo(xs, yAxis); ctx.stroke();
      }
    }
    glowDot(ctx, xs, yAxis, 22, ok ? "rgba(233,236,242,0.55)" : "rgba(255,111,89,0.6)");
    ctx.fillStyle = ok ? C.ink : C.flare;
    ctx.beginPath();
    ctx.moveTo(xs + 9, yAxis); ctx.lineTo(xs - 6, yAxis - 7); ctx.lineTo(xs - 6, yAxis + 7); ctx.closePath();
    ctx.fill();
  });

  function updateFocal() {
    const zmin = S.zMinAU(focal.m, focal.r);
    const ring = S.einsteinRing(focal.z, focal.m);
    const ok = focal.z >= zmin;
    const st = $("f-status");
    if (ok) {
      st.dataset.tone = "sol";
      st.textContent = T("focal.ok", null, "The spacecraft is on the focal line.");
    } else {
      st.dataset.tone = "flare";
      st.textContent = T("focal.close", { z: zmin.toFixed(0) }, `Too close: rays that would focus here hit the lens. Move beyond ${zmin.toFixed(0)} AU.`);
    }
    $("r-zmin").textContent = `${N(zmin, 1)} ${AU()}`;
    $("r-b").textContent = ok ? `${N(ring.bRing_rsun, 2)} R☉` : T("focal.blocked", null, "blocked");
    $("r-theta").textContent = ok ? `${N(ring.thetaE_arcsec, 2)}″` : "–";
    $("r-mu").textContent = fmtSci(S.peakGain(1e-6, focal.m));
    focalScene.render();
  }

  const fMass = bindRange("f-mass", "o-mass", (v) => `${N(v, 2)} M☉`, (v) => { focal.m = v; updateFocal(); });
  const fRad = bindRange("f-rad", "o-rad", (v) => `${N(v, 2)} R☉`, (v) => { focal.r = v; updateFocal(); });
  const fZ = bindRange("f-z", "o-z", (v) => `${v.toFixed(0)} ${AU()}`, (v) => { focal.z = v; updateFocal(); });
  $("f-reset").addEventListener("click", () => { fMass.set(1); fRad.set(1); fZ.set(650); });

  // Drag the spacecraft along the axis.
  (function () {
    const cv = $("cv-focal");
    const zFromEvent = (e) => {
      const r = cv.getBoundingClientRect();
      const g = focal.geo;
      const z = (e.clientX - r.left - g.xLens) / g.xPerAU;
      return Math.max(100, Math.min(1950, Math.round(z / 5) * 5));
    };
    cv.addEventListener("pointerdown", (e) => {
      const r = cv.getBoundingClientRect();
      const g = focal.geo;
      if (!g) return;
      const near = Math.abs(e.clientY - r.top - g.yAxis) < 40 && e.clientX - r.left > g.xLens + 10;
      if (!near) return;
      focal.dragging = true;
      cv.setPointerCapture(e.pointerId);
      fZ.set(zFromEvent(e));
    });
    cv.addEventListener("pointermove", (e) => {
      const r = cv.getBoundingClientRect();
      const g = focal.geo;
      if (focal.dragging) { fZ.set(zFromEvent(e)); return; }
      if (g) {
        const near = Math.abs(e.clientY - r.top - g.yAxis) < 40 && e.clientX - r.left > g.xLens + 10;
        cv.style.cursor = near ? "ew-resize" : "default";
      }
    });
    const stop = () => { focal.dragging = false; };
    cv.addEventListener("pointerup", stop);
    cv.addEventListener("pointercancel", stop);
  })();

  // ===================================================================
  // Scene 2: astroid caustic and Einstein cross
  // ===================================================================
  const cau = { j2: 2.2, z: 650, u: 0.3, v: 0.2, half: 2.0 };

  const causticState = () => {
    const k = S.causticScale(cau.j2 * 1e-7, cau.z);
    return { k, ...S.einsteinCross(cau.u / k, cau.v / k) };
  };

  const planeScene = canvasScene($("cv-plane"), (ctx, w, h) => {
    const st = causticState();
    const pad = 28;
    const s = (Math.min(w, h) - 2 * pad) / (2 * cau.half);
    const cx = w / 2;
    const cy = h / 2 + 8;
    const P = (u, v) => [cx + u * s, cy - v * s];
    planeScene.map = { cx, cy, s };

    ctx.clearRect(0, 0, w, h);
    ctx.strokeStyle = C.rule;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(cx - cau.half * s, cy); ctx.lineTo(cx + cau.half * s, cy);
    ctx.moveTo(cx, cy - cau.half * s); ctx.lineTo(cx, cy + cau.half * s);
    ctx.stroke();

    // Astroid.
    ctx.beginPath();
    for (let i = 0; i <= 240; i++) {
      const t = (2 * Math.PI * i) / 240;
      const [x, y] = P(st.k * Math.cos(t) ** 3, st.k * Math.sin(t) ** 3);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.fillStyle = "rgba(255,194,75,0.08)";
    ctx.fill();
    ctx.strokeStyle = C.sol;
    ctx.lineWidth = 2;
    ctx.stroke();

    // Spacecraft with spokes towards the images it sees.
    const [rx, ry] = P(cau.u, cau.v);
    ctx.lineWidth = 1.5;
    st.roots.forEach((phi, i) => {
      ctx.strokeStyle = C.sol;
      ctx.globalAlpha = 0.35 + 0.6 * st.mags[i];
      ctx.beginPath(); ctx.moveTo(rx, ry); ctx.lineTo(rx + 30 * Math.cos(phi), ry - 30 * Math.sin(phi)); ctx.stroke();
    });
    ctx.globalAlpha = 1;
    glowDot(ctx, rx, ry, 18, "rgba(169,210,255,0.6)");
    ctx.fillStyle = C.ink;
    ctx.beginPath(); ctx.arc(rx, ry, 4.5, 0, 2 * Math.PI); ctx.fill();
  });

  const ringScene = canvasScene($("cv-ring"), (ctx, w, h) => {
    const st = causticState();
    const cx = w / 2;
    const cy = h / 2 + 8;
    const R = Math.min(w, h) * 0.32;
    ctx.clearRect(0, 0, w, h);

    // Azimuthal brightness profile, drawn as a halo around the ring.
    const N = 360;
    const prof = new Float64Array(N).fill(0.05);
    for (let i = 0; i < N; i++) {
      const p = (2 * Math.PI * i) / N;
      st.roots.forEach((r, j) => {
        let d = Math.abs(p - r);
        d = Math.min(d, 2 * Math.PI - d);
        prof[i] += st.mags[j] * Math.exp(-(d * d) / (2 * 0.12 * 0.12));
      });
    }
    const pmax = Math.max(...prof);
    ctx.strokeStyle = C.rule;
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.arc(cx, cy, R, 0, 2 * Math.PI); ctx.stroke();
    ctx.beginPath();
    for (let i = 0; i <= N; i++) {
      const p = (2 * Math.PI * (i % N)) / N;
      const rr = R * (1 + 0.28 * (prof[i % N] / pmax));
      const x = cx + rr * Math.cos(p);
      const y = cy - rr * Math.sin(p);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.strokeStyle = C.sol;
    ctx.globalAlpha = 0.7;
    ctx.lineWidth = 1.5;
    ctx.stroke();
    ctx.globalAlpha = 1;

    // Occulted Sun.
    ctx.fillStyle = C.void;
    ctx.strokeStyle = C.rule;
    ctx.beginPath(); ctx.arc(cx, cy, R * 0.55, 0, 2 * Math.PI); ctx.fill(); ctx.stroke();

    // Images.
    st.roots.forEach((phi, i) => {
      const x = cx + R * Math.cos(phi);
      const y = cy - R * Math.sin(phi);
      glowDot(ctx, x, y, 12 + 22 * st.mags[i], "rgba(255,194,75,0.8)");
      ctx.fillStyle = C.ink;
      ctx.beginPath(); ctx.arc(x, y, 2.5 + 2 * st.mags[i], 0, 2 * Math.PI); ctx.fill();
    });
  });

  function updateCaustic() {
    const st = causticState();
    const tone = { inside: "sol", outside: "ice", edge: "flare" }[st.regime];
    const text = {
      inside: T("caustic.inside", null, "Inside the astroid: four images form an Einstein cross."),
      outside: T("caustic.outside", null, "Outside the astroid: two images remain."),
      edge: T("caustic.edge", null, "On the caustic: two images merge and vanish."),
    }[st.regime];
    const box = $("c-status");
    box.dataset.tone = tone;
    box.textContent = text;
    $("r-nimg").textContent = st.roots.length;
    $("r-astroid").textContent = N(st.astroidValue, 2);
    const a = S.astroidSemiWidth(cau.z, cau.j2 * 1e-7);
    $("r-a").textContent = a >= 1e4 ? `${N(a / 1e3, 0)} km` : `${N(a, 0)} m`;
    planeScene.render();
    ringScene.render();
  }

  bindRange("c-j2", "o-j2", (v) => `${N(v, 2)} × 10⁻⁷`, (v) => { cau.j2 = v; updateCaustic(); });
  bindRange("c-z", "o-cz", (v) => `${v.toFixed(0)} ${AU()}`, (v) => { cau.z = v; updateCaustic(); });

  (function () {
    const cv = $("cv-plane");
    let drag = false;
    const move = (e) => {
      const r = cv.getBoundingClientRect();
      const m = planeScene.map;
      if (!m) return;
      const lim = cau.half - 0.05;
      cau.u = Math.max(-lim, Math.min(lim, (e.clientX - r.left - m.cx) / m.s));
      cau.v = Math.max(-lim, Math.min(lim, -(e.clientY - r.top - m.cy) / m.s));
      updateCaustic();
    };
    cv.style.cursor = "crosshair";
    cv.addEventListener("pointerdown", (e) => { drag = true; cv.setPointerCapture(e.pointerId); move(e); });
    cv.addEventListener("pointermove", (e) => { if (drag) move(e); });
    cv.addEventListener("pointerup", () => { drag = false; });
    cv.addEventListener("pointercancel", () => { drag = false; });
    // Keyboard: arrow keys nudge the spacecraft.
    cv.tabIndex = 0;
    cv.addEventListener("keydown", (e) => {
      const step = e.shiftKey ? 0.2 : 0.05;
      const d = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, step], ArrowDown: [0, -step] }[e.key];
      if (!d) return;
      e.preventDefault();
      const lim = cau.half - 0.05;
      cau.u = Math.max(-lim, Math.min(lim, cau.u + d[0]));
      cau.v = Math.max(-lim, Math.min(lim, cau.v + d[1]));
      updateCaustic();
    });
  })();

  // ===================================================================
  // Scene 3: wave-optics PSF
  // ===================================================================
  const psfS = { lam: 1.0, z: 650 };
  const RHO_MAX_CM = 30;

  const psfScene = canvasScene($("cv-psf"), (ctx, w, h) => {
    const L = 44, R = 32, T = 40, B = 40;
    const X = (cm) => L + (cm / RHO_MAX_CM) * (w - L - R);
    const Y = (i) => h - B - i * (h - T - B);
    ctx.clearRect(0, 0, w, h);
    ctx.font = FONT;

    ctx.strokeStyle = C.rule;
    ctx.fillStyle = C.faint;
    ctx.lineWidth = 1;
    ctx.textAlign = "center";
    for (let cm = 0; cm <= RHO_MAX_CM; cm += 5) {
      ctx.beginPath(); ctx.moveTo(X(cm), h - B); ctx.lineTo(X(cm), h - B + 4); ctx.stroke();
      ctx.fillText(cm === RHO_MAX_CM ? `${cm} cm` : `${cm}`, X(cm), h - B + 18);
    }
    ctx.textAlign = "right";
    for (const yv of [0, 0.5, 1]) {
      ctx.beginPath(); ctx.moveTo(L, Y(yv)); ctx.lineTo(w - R, Y(yv)); ctx.stroke();
      ctx.fillText(N(yv, 1), L - 8, Y(yv) + 4);
    }

    const lamM = psfS.lam * 1e-6;
    ctx.beginPath();
    const n = 600;
    for (let i = 0; i <= n; i++) {
      const cm = (i / n) * RHO_MAX_CM;
      const I = S.psf(cm / 100, psfS.z, lamM, 1);
      if (i === 0) ctx.moveTo(X(cm), Y(I)); else ctx.lineTo(X(cm), Y(I));
    }
    ctx.strokeStyle = C.sol;
    ctx.lineWidth = 2;
    ctx.stroke();

    const rho0 = S.psfFirstZero(psfS.z, lamM, 1) * 100;
    if (rho0 < RHO_MAX_CM) {
      ctx.setLineDash([3, 4]);
      ctx.strokeStyle = C.ice;
      ctx.beginPath(); ctx.moveTo(X(rho0), Y(0)); ctx.lineTo(X(rho0), Y(0.85)); ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = C.ice;
      ctx.textAlign = "left";
      ctx.fillText(`${N(rho0, 1)} cm`, X(rho0) + 6, Y(0.8));
    }
  });

  const detScene = canvasScene($("cv-det"), (ctx, w, h) => {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const W = Math.round(w * dpr);
    const H = Math.round(h * dpr);
    const Rpx = Math.min(W, H) * 0.42;
    const cx = W / 2;
    const cy = H / 2 + 8 * dpr;
    const img = ctx.createImageData(W, H);
    const lamM = psfS.lam * 1e-6;
    // Precompute a radial lookup table, then paint.
    const LUT = 1024;
    const table = new Float32Array(LUT + 1);
    for (let i = 0; i <= LUT; i++) table[i] = Math.pow(S.psf((i / LUT) * (RHO_MAX_CM / 100), psfS.z, lamM, 1), 0.45);
    const bg = [0x17, 0x1b, 0x24];
    const fg = [0xff, 0xc2, 0x4b];
    for (let y = 0; y < H; y++) {
      for (let x = 0; x < W; x++) {
        const r = Math.hypot(x - cx, y - cy) / Rpx;
        const k = 4 * (y * W + x);
        let a = 0;
        if (r <= 1) a = table[Math.round(r * LUT)];
        img.data[k] = bg[0] + (fg[0] - bg[0]) * a;
        img.data[k + 1] = bg[1] + (fg[1] - bg[1]) * a;
        img.data[k + 2] = bg[2] + (fg[2] - bg[2]) * a;
        img.data[k + 3] = 255;
      }
    }
    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.putImageData(img, 0, 0);
    ctx.restore();
    // 1 m telescope would cover the whole picture several times over; mark the edge.
    ctx.strokeStyle = C.rule;
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.arc(cx / dpr, cy / dpr, Rpx / dpr, 0, 2 * Math.PI); ctx.stroke();
  });

  function updatePsf() {
    const lamM = psfS.lam * 1e-6;
    const rho0 = S.psfFirstZero(psfS.z, lamM, 1);
    $("r-rho0").textContent = `${N(rho0 * 100, 2)} cm`;
    $("r-mu2").textContent = fmtSci(S.peakGain(lamM, 1));
    $("r-span").textContent = T("psf.radii", { n: (0.5 / rho0).toFixed(0) }, `${(0.5 / rho0).toFixed(0)} core radii`);
    psfScene.render();
    detScene.render();
  }

  bindRange("p-lam", "o-lam", (v) => `${N(v, 2)} µm`, (v) => { psfS.lam = v; updatePsf(); });
  bindRange("p-z", "o-pz", (v) => `${v.toFixed(0)} ${AU()}`, (v) => { psfS.z = v; updatePsf(); });


  // ===================================================================
  // Mission planner (docs/sim/targets.json, precomputed with sgl_sim by
  // scripts/export_site_targets.py)
  // ===================================================================
  const esc = (t) => String(t).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const tierLabel = (tier) => {
    const en = tier.replace(/^Tier \d: /, "");
    return T(`tier.${en}`, null, en);
  };
  const descOf = (t) => T(`desc.${t.name}`, null, t.description);
  const albedo = (v) => {
    // dark → starlight blue → warm white, as in the dashboard
    const stops = [[0, [23, 27, 36]], [0.35, [52, 84, 130]], [0.7, [169, 210, 255]], [1, [255, 240, 214]]];
    v = Math.max(0, Math.min(1, v));
    for (let i = 1; i < stops.length; i++) {
      if (v <= stops[i][0]) {
        const [a0, c0] = stops[i - 1];
        const [a1, c1] = stops[i];
        const f = (v - a0) / (a1 - a0);
        return c0.map((c, k) => Math.round(c + (c1[k] - c) * f));
      }
    }
    return stops[stops.length - 1][1];
  };
  const heat = (v) => {
    v = Math.max(0, Math.min(1, v));
    const a = [23, 27, 36], m = [122, 82, 28], b = [255, 194, 75];
    return v < 0.5 ? a.map((c, k) => Math.round(c + (m[k] - c) * v * 2)) : m.map((c, k) => Math.round(c + (b[k] - c) * (v - 0.5) * 2));
  };

  /** Paint a 2D array into a w×h box via an offscreen bitmap. */
  function paintMatrix(ctx, w, h, M, cmap, { flipY = false, smooth = false } = {}) {
    const ny = M.length, nx = M[0].length;
    const off = document.createElement("canvas");
    off.width = nx; off.height = ny;
    const o = off.getContext("2d");
    const img = o.createImageData(nx, ny);
    let lo = Infinity, hi = -Infinity;
    for (const row of M) for (const v of row) { if (v < lo) lo = v; if (v > hi) hi = v; }
    for (let j = 0; j < ny; j++) {
      const row = M[flipY ? ny - 1 - j : j];
      for (let i = 0; i < nx; i++) {
        const [r, g, b] = cmap((row[i] - lo) / (hi - lo || 1));
        const k = 4 * (j * nx + i);
        img.data[k] = r; img.data[k + 1] = g; img.data[k + 2] = b; img.data[k + 3] = 255;
      }
    }
    o.putImageData(img, 0, 0);
    ctx.imageSmoothingEnabled = smooth;
    ctx.drawImage(off, 0, 0, w, h);
  }

  let planner = null;   // { data, index }

  const skyScene = canvasScene($("cv-sky"), (ctx, w, h) => {
    if (!planner) return;
    const { sky, targets } = planner.data;
    paintMatrix(ctx, w, h, sky.efficiency, heat, { flipY: true, smooth: true });
    const X = (ra) => (ra / 360) * w;
    const Y = (dec) => h / 2 - (dec / 90) * (h / 2);
    ctx.strokeStyle = "rgba(233,236,242,0.18)";
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(0, Y(0)); ctx.lineTo(w, Y(0)); ctx.stroke();
    targets.forEach((t, i) => {
      const x = X(t.telescope_ra_deg), y = Y(t.telescope_dec_deg);
      ctx.fillStyle = C.ink;
      ctx.beginPath(); ctx.arc(x, y, 3, 0, 2 * Math.PI); ctx.fill();
      if (i === planner.index) {
        ctx.strokeStyle = C.ink; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.arc(x, y, 9, 0, 2 * Math.PI); ctx.stroke();
      }
    });
  });

  const blurScene = (id, key) => canvasScene($(id), (ctx, w, h) => {
    if (!planner) return;
    const t = planner.data.targets[planner.index];
    paintMatrix(ctx, w, h, t.mission.blur[key].image, albedo);
  });
  const blur1 = blurScene("cv-b1", "single");
  const blurN = blurScene("cv-bn", "swarm");

  function renderTable() {
    const { targets } = planner.data;
    $("targets-body").innerHTML = targets.map((t, i) => {
      const low = t.sgl_score < 60;
      const sel = i === planner.index;
      return `<tr class="pick ${low ? "low" : ""}" data-i="${i}" aria-selected="${sel}">
        <td class="num">${i + 1}</td>
        <td class="planet"><button type="button" data-i="${i}" aria-label="${esc(T("targets.select", { name: t.name }, `See the mission to ${t.name}`))}">${esc(t.name)}</button><span>${esc(descOf(t))}</span></td>
        <td class="num">${N(t.dist_pc, 2)} pc<br><small>${esc(T("m.ly", { n: N(t.dist_pc * 3.2616, 1) }, `${N(t.dist_pc * 3.2616, 1)} ly`))}</small></td>
        <td class="num">${N(t.image_diameter_km, 1)} km</td>
        <td>${esc(t.telescope_constellation)}</td>
        <td class="score"><span class="score-bar"><i style="width:${t.sgl_score}%"></i></span>${N(t.sgl_score, 1)}<small>${esc(tierLabel(t.tier))}</small></td>
      </tr>`;
    }).join("");
  }

  function renderMission() {
    const d = planner.data;
    const t = d.targets[planner.index];
    const m = t.mission;
    const dep = m.deployment;
    const one = m.blur.single;
    const many = m.blur.swarm;
    $("mission").hidden = false;
    $("m-name").textContent = t.name;
    $("m-desc").textContent = descOf(t);
    $("m-score").innerHTML = `${N(t.sgl_score, 1)} <small>/ 100</small>`;
    $("m-tier").textContent = tierLabel(t.tier);

    $("m-point").textContent = `RA ${N(dep.telescope_ra_deg, 1)}°, Dec ${dep.telescope_dec_deg >= 0 ? "+" : ""}${N(dep.telescope_dec_deg, 1)}°`;
    $("m-const").textContent = dep.telescope_constellation;
    $("m-xyz").textContent = `${N(dep.x_au, 0)}, ${N(dep.y_au, 0)}, ${N(dep.z_au, 0)} ${AU()}`;
    $("m-incl").textContent = `${N(dep.ecliptic_inclination_deg, 1)}°`;

    $("m-trip-lede").textContent = T("m.trip.lede", { year: d.arrival_year, v: N(d.cruise_velocity_au_yr, 0) },
      `Arrival in ${d.arrival_year}, cruising at ${d.cruise_velocity_au_yr} AU per year.`);
    $("m-cruise").textContent = T("m.years", { n: N(dep.cruise_time_years, 1) }, `${N(dep.cruise_time_years, 1)} years`);
    $("m-delay").textContent = T("m.days", { n: N(dep.light_delay_days, 2) }, `${N(dep.light_delay_days, 2)} days`);
    $("m-img").textContent = `${N(t.image_diameter_km, 1)} km`;
    $("m-drift").textContent = `${N(dep.proper_motion_drift_m_s, 1)} m/s`;
    $("m-driftyr").textContent = `${N(dep.annual_lateral_drift_km, 0)} km`;
    $("m-dv1").textContent = `${N(one.total_delta_v_m_s, 0)} m/s`;
    $("m-dvn-label").textContent = T("m.dvswarm", { n: d.swarm_size }, `Scan Δv per craft, swarm of ${d.swarm_size}`);
    $("m-dvn").textContent = `${N(many.total_delta_v_m_s, 0)} m/s`;

    const factors = [
      ["m.f.snr", "Signal (SNR)", t.snr_score],
      ["m.f.log", "Scan logistics", t.scan_logistics_score],
      ["m.f.ecl", "Ecliptic access", t.ecliptic_access_score],
      ["m.f.blur", "Blur immunity", t.blur_immunity_score],
    ];
    $("m-bars").innerHTML = factors.map(([k, en, v]) =>
      `<span class="label">${esc(T(k, null, en))}</span><span class="bar"><i style="width:${Math.round(v * 100)}%"></i></span><span>${N(v, 2)}</span>`
    ).join("");

    const cap = (r, title) => `<b>${esc(title)}</b>${esc(T("m.smear",
      { x: N(r.eta_blur, 2), h: N(r.scan_time_hours, 2), e: N(r.rmse, 3) },
      `smear ${N(r.eta_blur, 2)}× · scan ${N(r.scan_time_hours, 2)} h · error ${N(r.rmse, 3)}`))}`;
    $("m-b1").innerHTML = cap(one, T("m.one", null, "One spacecraft"));
    $("m-bn").innerHTML = cap(many, T("m.swarm", { n: d.swarm_size }, `Swarm of ${d.swarm_size}`));
    const verdict = $("m-verdict");
    if (one.is_blurred) {
      verdict.dataset.tone = "flare";
      verdict.textContent = T("m.verdict.swarm", null, "A swarm is needed: with one spacecraft the planet's rotation smears the image.");
    } else {
      verdict.dataset.tone = "sol";
      verdict.textContent = T("m.verdict.single", null, "One spacecraft is enough: the planet turns so slowly (or is tidally locked) that the image stays sharp.");
    }

    const list = m.coaligned_with.map((c) => c.name);
    const joined = L10N.lang === "es"
      ? list.join(", ").replace(/, ([^,]*)$/, " y $1")
      : list.join(", ").replace(/, ([^,]*)$/, " and $1");
    $("m-shared").textContent = list.length
      ? T("m.shared.yes", { list: joined }, `The same fleet can also observe ${joined} with a minor trajectory correction (within 3°).`)
      : T("m.shared.no", null, "No other candidate lies within 3°, so this mission cannot be shared.");

    skyScene.render(); blur1.render(); blurN.render();
  }

  function select(i, focus) {
    planner.index = i;
    renderTable();
    renderMission();
    if (focus) {
      const btn = $("targets-body").querySelector(`button[data-i="${i}"]`);
      if (btn) btn.focus();
    }
  }

  $("targets-body").addEventListener("click", (e) => {
    const tr = e.target.closest("tr[data-i]");
    if (!tr || !planner) return;
    select(+tr.dataset.i, e.target.tagName === "BUTTON");
    if (e.target.tagName === "BUTTON") {
      $("mission").scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
    }
  });

  fetch("sim/targets.json")
    .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then((data) => { planner = { data, index: 0 }; select(0, false); })
    .catch(() => {
      $("targets-body").innerHTML = `<tr><td colspan="6" class="empty">${esc(T("targets.error", null, "The ranking could not be loaded. Reload the page to try again."))}</td></tr>`;
    });

  // Re-render every dynamic string when the language changes.
  L10N.onChange(() => {
    binds.forEach((b) => b.update());
    if (planner) { renderTable(); renderMission(); }
    focalScene.render(); psfScene.render();
  });

  updateFocal();
  updateCaustic();
  updatePsf();
})();
