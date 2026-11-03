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
    return { el, update, set(v) { el.value = v; update(); } };
  }

  const fmtSci = (x, d = 2) => {
    const e = Math.floor(Math.log10(Math.abs(x)));
    const m = x / Math.pow(10, e);
    const sup = String(e).replace(/-/g, "⁻").replace(/\d/g, (c) => "⁰¹²³⁴⁵⁶⁷⁸⁹"[c]);
    return `${m.toFixed(d)} × 10${sup}`;
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
      ctx.fillText(`${z} AU`, Math.min(X(z), w - 28), h - 18);
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
      ctx.fillText(`z_min ${zmin.toFixed(0)} AU`, X(zmin) + (ctx.textAlign === "left" ? 6 : -6), yAxis - h * 0.36 + 12);
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
      st.textContent = "The spacecraft is on the focal line.";
    } else {
      st.dataset.tone = "flare";
      st.textContent = `Too close: rays that would focus here hit the lens. Move beyond ${zmin.toFixed(0)} AU.`;
    }
    $("r-zmin").textContent = `${zmin.toFixed(1)} AU`;
    $("r-b").textContent = ok ? `${ring.bRing_rsun.toFixed(2)} R☉` : "blocked";
    $("r-theta").textContent = ok ? `${ring.thetaE_arcsec.toFixed(2)}″` : "–";
    $("r-mu").textContent = fmtSci(S.peakGain(1e-6, focal.m));
    focalScene.render();
  }

  const fMass = bindRange("f-mass", "o-mass", (v) => `${v.toFixed(2)} M☉`, (v) => { focal.m = v; updateFocal(); });
  const fRad = bindRange("f-rad", "o-rad", (v) => `${v.toFixed(2)} R☉`, (v) => { focal.r = v; updateFocal(); });
  const fZ = bindRange("f-z", "o-z", (v) => `${v.toFixed(0)} AU`, (v) => { focal.z = v; updateFocal(); });
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
      inside: "Inside the astroid: four images form an Einstein cross.",
      outside: "Outside the astroid: two images remain.",
      edge: "On the caustic: two images merge and vanish.",
    }[st.regime];
    const box = $("c-status");
    box.dataset.tone = tone;
    box.textContent = text;
    $("r-nimg").textContent = st.roots.length;
    $("r-astroid").textContent = st.astroidValue.toFixed(2);
    const a = S.astroidSemiWidth(cau.z, cau.j2 * 1e-7);
    $("r-a").textContent = a >= 1e4 ? `${Math.round(a / 1e3).toLocaleString("en")} km` : `${a.toFixed(0)} m`;
    planeScene.render();
    ringScene.render();
  }

  bindRange("c-j2", "o-j2", (v) => `${v.toFixed(2)} × 10⁻⁷`, (v) => { cau.j2 = v; updateCaustic(); });
  bindRange("c-z", "o-cz", (v) => `${v.toFixed(0)} AU`, (v) => { cau.z = v; updateCaustic(); });

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
      ctx.fillText(yv.toFixed(1), L - 8, Y(yv) + 4);
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
      ctx.fillText(`${rho0.toFixed(1)} cm`, X(rho0) + 6, Y(0.8));
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
    $("r-rho0").textContent = `${(rho0 * 100).toFixed(2)} cm`;
    $("r-mu2").textContent = fmtSci(S.peakGain(lamM, 1));
    $("r-span").textContent = `${(0.5 / rho0).toFixed(0)} core radii`;
    psfScene.render();
    detScene.render();
  }

  bindRange("p-lam", "o-lam", (v) => `${v.toFixed(2)} µm`, (v) => { psfS.lam = v; updatePsf(); });
  bindRange("p-z", "o-pz", (v) => `${v.toFixed(0)} AU`, (v) => { psfS.z = v; updatePsf(); });

  updateFocal();
  updateCaustic();
  updatePsf();
})();
