/**
 * sgl-sim: Interactive Mission-Design & Wave Optics Simulator
 * Synchronizes 4 scientific panels with real-time API simulation.
 */

(function () {
  'use strict';

  // State object
  const state = {
    lens_type: 'star',
    mass_solar: 1.0,
    z_rec_au: 650.0,
    j2: 2.2e-7,
    wavelength_um: 1.0,
    aperture_m: 1.0,
    t_int_days: 1.0,
    distance_source_pc: 1.3,
    x0_m: 0.0,
    y0_m: 0.0,
    is_dragging_astroid: false,
    active_tab: 'tab-deconv',
    last_data: null,
    tradespace_data: null,
  };

  // Canvas elements
  const cvRays = document.getElementById('canvas-rays');
  const ctxRays = cvRays.getContext('2d');

  const cvAstroid = document.getElementById('canvas-astroid');
  const ctxAstroid = cvAstroid.getContext('2d');

  const cvDetector = document.getElementById('canvas-detector');
  const ctxDetector = cvDetector.getContext('2d');

  const cvPsf = document.getElementById('canvas-psf');
  const ctxPsf = cvPsf.getContext('2d');

  const cvGt = document.getElementById('canvas-gt');
  const ctxGt = cvGt.getContext('2d');

  const cvNoisy = document.getElementById('canvas-noisy');
  const ctxNoisy = cvNoisy.getContext('2d');

  const cvRecon = document.getElementById('canvas-reconstructed');
  const ctxRecon = cvRecon.getContext('2d');

  const cvTradespace = document.getElementById('canvas-tradespace');
  const ctxTradespace = cvTradespace.getContext('2d');

  // DOM elements for controls
  const inputLensType = document.getElementById('input-lens-type');
  const inputMass = document.getElementById('input-mass');
  const inputZRec = document.getElementById('input-z-rec');
  const inputJ2 = document.getElementById('input-j2');
  const inputWavelength = document.getElementById('input-wavelength');
  const inputAperture = document.getElementById('input-aperture');
  const inputTInt = document.getElementById('input-t-int');
  const inputDistPc = document.getElementById('input-dist-pc');

  const valMass = document.getElementById('val-mass');
  const valZRec = document.getElementById('val-z-rec');
  const valZMin = document.getElementById('val-z-min');
  const valJ2 = document.getElementById('val-j2');
  const valACaustic = document.getElementById('val-a-caustic');
  const valWavelength = document.getElementById('val-wavelength');
  const valMuMax = document.getElementById('val-mu-max');
  const valAperture = document.getElementById('val-aperture');
  const valTInt = document.getElementById('val-t-int');
  const valDistPc = document.getElementById('val-dist-pc');
  const valDImg = document.getElementById('val-d-img');

  // Telemetry DOM
  const telemVOrb = document.getElementById('telem-v-orb');
  const telemPeriod = document.getElementById('telem-period');
  const telemHoverDv = document.getElementById('telem-hover-dv');
  const telemScanDv = document.getElementById('telem-scan-dv');
  const telemTotalDv = document.getElementById('telem-total-dv');

  // Badge & Overlays
  const badgeRayStatus = document.getElementById('badge-ray-status');
  const badgeCausticRegime = document.getElementById('badge-caustic-regime');
  const overlayLensDesc = document.getElementById('overlay-lens-desc');
  const overlayRs = document.getElementById('overlay-rs');
  const overlayZmin = document.getElementById('overlay-zmin');
  const overlaySatZ = document.getElementById('overlay-sat-z');
  const overlayCausticA = document.getElementById('overlay-caustic-a');
  const overlayX0 = document.getElementById('overlay-x0');
  const overlayY0 = document.getElementById('overlay-y0');
  const overlayNumImages = document.getElementById('overlay-num-images');

  const valThetaE = document.getElementById('val-theta-e');
  const valBRing = document.getElementById('val-b-ring');
  const valCoronaRatio = document.getElementById('val-corona-ratio');

  const stageSnr = document.getElementById('stage-snr');
  const stageRmseNoisy = document.getElementById('stage-rmse-noisy');
  const stageSsim = document.getElementById('stage-ssim');
  const stageRmseRecon = document.getElementById('stage-rmse-recon');
  const metricRmseGain = document.getElementById('metric-rmse-gain');
  const metricFidelity = document.getElementById('metric-fidelity');

  // Presets Configuration
  const presets = {
    'solar-default': {
      lens_type: 'star',
      mass_solar: 1.0,
      z_rec_au: 650.0,
      j2: 2.2e-7,
      wavelength_um: 1.0,
      aperture_m: 1.0,
      t_int_days: 1.0,
      distance_source_pc: 1.3,
      x0_m: 0.0,
      y0_m: 0.0,
    },
    'solar-cusp': {
      lens_type: 'star',
      mass_solar: 1.0,
      z_rec_au: 650.0,
      j2: 2.2e-7,
      wavelength_um: 1.0,
      aperture_m: 1.0,
      t_int_days: 1.0,
      distance_source_pc: 1.3,
      x0_m: 15.2, // On astroid cusp boundary
      y0_m: 0.0,
    },
    'fast-rotator': {
      lens_type: 'star',
      mass_solar: 1.4,
      z_rec_au: 700.0,
      j2: 2.2e-6, // 10x solar
      wavelength_um: 0.8,
      aperture_m: 1.5,
      t_int_days: 2.0,
      distance_source_pc: 2.5,
      x0_m: 10.0,
      y0_m: 10.0,
    },
    'black-hole': {
      lens_type: 'black_hole',
      mass_solar: 5.0,
      z_rec_au: 550.0,
      j2: 0.0,
      wavelength_um: 1.5,
      aperture_m: 2.0,
      t_int_days: 1.0,
      distance_source_pc: 5.0,
      x0_m: 0.0,
      y0_m: 0.0,
    },
  };

  // Toast notifications
  function showToast(message) {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), 300);
    }, 2800);
  }

  // Update State & Labels from UI
  function updateStateFromInputs() {
    state.lens_type = inputLensType.value;
    state.mass_solar = parseFloat(inputMass.value);
    state.z_rec_au = parseFloat(inputZRec.value);
    state.j2 = parseFloat(inputJ2.value) * 1e-7;
    state.wavelength_um = parseFloat(inputWavelength.value);
    state.aperture_m = parseFloat(inputAperture.value);
    state.t_int_days = parseFloat(inputTInt.value);
    state.distance_source_pc = parseFloat(inputDistPc.value);

    // Update label text
    valMass.textContent = `${state.mass_solar.toFixed(2)} M☉`;
    valZRec.textContent = `${state.z_rec_au.toFixed(1)} AU`;
    valJ2.textContent = (state.j2 * 1e7).toFixed(2);
    valWavelength.textContent = `${state.wavelength_um.toFixed(2)} μm`;
    valAperture.textContent = `${state.aperture_m.toFixed(2)} m`;
    valTInt.textContent = `${state.t_int_days.toFixed(1)} days`;
    valDistPc.textContent = `${state.distance_source_pc.toFixed(2)} pc`;

    triggerSimulation();
  }

  // Debounce API calls
  let simTimeout = null;
  function triggerSimulation() {
    clearTimeout(simTimeout);
    simTimeout = setTimeout(fetchSimulationData, 60);
  }

  // Fetch full simulation from Flask API
  async function fetchSimulationData() {
    const payload = {
      lens_type: state.lens_type,
      mass_solar: state.mass_solar,
      z_rec_au: state.z_rec_au,
      j2: state.j2,
      wavelength_um: state.wavelength_um,
      aperture_m: state.aperture_m,
      t_int_days: state.t_int_days,
      distance_source_pc: state.distance_source_pc,
      x0_m: state.x0_m,
      y0_m: state.y0_m,
    };

    try {
      const resp = await fetch('/api/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) throw new Error(`HTTP error ${resp.status}`);
      const data = await resp.json();
      state.last_data = data;
      renderAll(data);
    } catch (err) {
      console.error('Simulation fetch error:', err);
    }
  }

  // Render everything based on data
  function renderAll(data) {
    // 1. Update text & telemetry
    valZMin.textContent = `${data.z_min_au.toFixed(1)} AU`;
    valACaustic.textContent = `~${data.a_caustic_m.toFixed(1)} m`;
    valMuMax.textContent = data.mu_max > 1e6 ? data.mu_max.toExponential(2) : data.mu_max.toFixed(0);
    valDImg.textContent = `~${data.image_cylinder_km.toFixed(1)} km`;

    telemVOrb.textContent = `${(data.orbital_velocity_m_s / 1000.0).toFixed(2)} km/s`;
    telemPeriod.textContent = `${data.orbital_period_years.toLocaleString(undefined, { maximumFractionDigits: 0 })} yrs`;
    telemHoverDv.textContent = `${data.delta_v_hover_m_s.toFixed(2)} m/s/yr`;
    telemScanDv.textContent = `${data.delta_v_scan_m_s.toFixed(4)} m/s`;
    telemTotalDv.textContent = `${data.delta_v_total_m_s.toFixed(2)} m/s/yr`;

    // Overlays
    overlayRs.textContent = `${(data.schwarzschild_radius_m / 1000.0).toFixed(2)} km`;
    overlayZmin.textContent = `${data.z_min_au.toFixed(1)} AU`;
    overlaySatZ.textContent = `${data.z_rec_au.toFixed(1)} AU`;
    overlayLensDesc.textContent = state.lens_type === 'black_hole'
      ? `Schwarzschild BH (${data.mass_solar.toFixed(1)} M☉)`
      : `Sun (${data.mass_solar.toFixed(1)} M☉, 1.0 R☉)`;

    badgeRayStatus.textContent = state.lens_type === 'black_hole'
      ? `Strong Field (bc = ${(data.critical_impact_param_m / 1000).toFixed(1)} km)`
      : `Weak Field (z_min ≈ 548 AU)`;

    overlayCausticA.textContent = `${data.a_caustic_m.toFixed(1)} m`;
    overlayX0.textContent = data.x0_m.toFixed(1);
    overlayY0.textContent = data.y0_m.toFixed(1);

    if (data.regime === 'inside') {
      badgeCausticRegime.textContent = 'Inside Astroid (Einstein Cross: 4 Images)';
      badgeCausticRegime.className = 'badge badge-success';
      overlayNumImages.textContent = '4 (Einstein Cross)';
    } else if (data.regime === 'cusp_boundary') {
      badgeCausticRegime.textContent = 'Astroid Cusp / Fold (Bright Arc)';
      badgeCausticRegime.className = 'badge badge-gold';
      overlayNumImages.textContent = '3+ (Merging Cusp Arc)';
    } else {
      badgeCausticRegime.textContent = 'Outside Astroid (2 Images)';
      badgeCausticRegime.className = 'badge badge-info';
      overlayNumImages.textContent = '2 (Double Image)';
    }

    valThetaE.textContent = `${data.theta_E_arcsec.toFixed(4)}" (${(data.theta_E_arcsec * 1000).toFixed(2)} mas)`;
    valBRing.textContent = `${data.b_ring_r_sun.toFixed(2)} R☉`;
    valCoronaRatio.textContent = (data.b_ring_r_sun ? (2.56e-6 / (data.b_ring_r_sun ** 6)).toExponential(2) : '1.8e-6');

    // Deconvolution metrics
    stageSnr.textContent = data.snr.toFixed(1);
    stageRmseNoisy.textContent = data.rmse_noisy.toFixed(3);
    stageSsim.textContent = data.ssim_deconvolved.toFixed(3);
    stageRmseRecon.textContent = data.rmse_deconvolved.toFixed(3);

    const rmseDrop = ((data.rmse_noisy - data.rmse_deconvolved) / data.rmse_noisy) * 100;
    metricRmseGain.textContent = `-${rmseDrop.toFixed(1)}%`;
    metricFidelity.textContent = data.ssim_deconvolved > 0.85 ? 'High (SSIM > 0.85)' : 'Moderate';

    // 2. Render Canvas Panels
    renderPanel1Rays(data);
    renderPanel2Astroid(data);
    renderPanel3Detector(data);
    renderPanel3Psf(data);
    renderPanel4Deconv(data);

    if (state.active_tab === 'tab-tradespace') {
      renderPanel4Tradespace();
    }
  }

  // ==========================================
  // PANEL 1: Ray-Tracing & Focal Line Geometry
  // ==========================================
  function renderPanel1Rays(data) {
    const w = cvRays.width;
    const h = cvRays.height;
    ctxRays.clearRect(0, 0, w, h);

    // Background deep space
    ctxRays.fillStyle = '#060a14';
    ctxRays.fillRect(0, 0, w, h);

    // Draw background stars
    ctxRays.fillStyle = 'rgba(255, 255, 255, 0.4)';
    const seed = 12;
    for (let i = 0; i < 35; i++) {
      const sx = ((i * 123 + 45) % w);
      const sy = ((i * 77 + 23) % h);
      const sr = (i % 3 === 0) ? 1.5 : 1.0;
      ctxRays.fillRect(sx, sy, sr, sr);
    }

    const midY = h / 2;
    const lensX = 90;

    // Optical Axis
    ctxRays.strokeStyle = 'rgba(255, 255, 255, 0.15)';
    ctxRays.setLineDash([4, 4]);
    ctxRays.beginPath();
    ctxRays.moveTo(0, midY);
    ctxRays.lineTo(w, midY);
    ctxRays.stroke();
    ctxRays.setLineDash([]);

    const isBh = state.lens_type === 'black_hole';

    if (!isBh) {
      // Stellar Lens
      const rSunPx = 28;

      // Solar Corona glow
      const gradCor = ctxRays.createRadialGradient(lensX, midY, rSunPx * 0.9, lensX, midY, rSunPx * 2.8);
      gradCor.addColorStop(0, 'rgba(245, 158, 11, 0.55)');
      gradCor.addColorStop(0.5, 'rgba(245, 158, 11, 0.15)');
      gradCor.addColorStop(1, 'rgba(245, 158, 11, 0.0)');
      ctxRays.fillStyle = gradCor;
      ctxRays.beginPath();
      ctxRays.arc(lensX, midY, rSunPx * 2.8, 0, Math.PI * 2);
      ctxRays.fill();

      // Stellar Disk
      const gradStar = ctxRays.createRadialGradient(lensX - 6, midY - 6, 2, lensX, midY, rSunPx);
      gradStar.addColorStop(0, '#fef08a');
      gradStar.addColorStop(0.7, '#f59e0b');
      gradStar.addColorStop(1, '#b45309');
      ctxRays.fillStyle = gradStar;
      ctxRays.beginPath();
      ctxRays.arc(lensX, midY, rSunPx, 0, Math.PI * 2);
      ctxRays.fill();

      // Rays
      const minFocalX = lensX + 220; // represents 548 AU
      const recX = lensX + 220 + ((state.z_rec_au - 547.8) / (950 - 547.8)) * 320;

      // Caustic focal line (semi-infinite)
      const gradLine = ctxRays.createLinearGradient(minFocalX, midY, w, midY);
      gradLine.addColorStop(0, 'rgba(250, 204, 21, 0.95)');
      gradLine.addColorStop(0.4, 'rgba(250, 204, 21, 0.7)');
      gradLine.addColorStop(1, 'rgba(250, 204, 21, 0.3)');
      ctxRays.strokeStyle = gradLine;
      ctxRays.lineWidth = 3;
      ctxRays.shadowColor = '#facc15';
      ctxRays.shadowBlur = 10;
      ctxRays.beginPath();
      ctxRays.moveTo(minFocalX, midY);
      ctxRays.lineTo(w, midY);
      ctxRays.stroke();
      ctxRays.shadowBlur = 0;

      // Draw Grazing & Blocked Rays
      const bOffsets = [10, 20, 28, 36, 46, 58];
      bOffsets.forEach((bOff) => {
        const isBlocked = bOff < rSunPx;
        [-1, 1].forEach((sign) => {
          const yStart = midY + sign * bOff;
          ctxRays.beginPath();
          ctxRays.moveTo(0, yStart);

          if (isBlocked) {
            // Stops at star surface
            const dx = Math.sqrt(Math.max(0, rSunPx**2 - bOff**2));
            const xHit = lensX - dx;
            ctxRays.lineTo(xHit, yStart);
            ctxRays.strokeStyle = 'rgba(239, 68, 68, 0.65)';
            ctxRays.setLineDash([3, 3]);
            ctxRays.lineWidth = 1.2;
            ctxRays.stroke();
            ctxRays.setLineDash([]);
          } else {
            // Bends toward focal line
            ctxRays.lineTo(lensX, yStart);
            // Focal crossing
            const zCrossX = minFocalX + (bOff - rSunPx) * 14;
            ctxRays.lineTo(zCrossX, midY);
            ctxRays.strokeStyle = (bOff === 28) ? 'rgba(56, 189, 248, 0.9)' : 'rgba(56, 189, 248, 0.4)';
            ctxRays.lineWidth = (bOff === 28) ? 2 : 1;
            ctxRays.stroke();
          }
        });
      });

      // Spacecraft Icon at recX
      drawSpacecraft(ctxRays, recX, midY, `${state.z_rec_au.toFixed(0)} AU`);

      // Label z_min
      ctxRays.fillStyle = '#facc15';
      ctxRays.font = '10px monospace';
      ctxRays.fillText('z_min (547.8 AU)', minFocalX - 25, midY - 14);
      ctxRays.beginPath();
      ctxRays.arc(minFocalX, midY, 3.5, 0, Math.PI * 2);
      ctxRays.fill();

    } else {
      // Black Hole Lens
      const rsPx = 16;
      const rPhPx = 1.5 * rsPx;
      const bcPx = 2.598 * rsPx;

      // Photon sphere
      ctxRays.strokeStyle = 'rgba(56, 189, 248, 0.5)';
      ctxRays.setLineDash([3, 3]);
      ctxRays.beginPath();
      ctxRays.arc(lensX, midY, rPhPx, 0, Math.PI * 2);
      ctxRays.stroke();
      ctxRays.setLineDash([]);

      // Critical impact parameter b_c
      ctxRays.strokeStyle = 'rgba(244, 63, 94, 0.35)';
      ctxRays.beginPath();
      ctxRays.arc(lensX, midY, bcPx, 0, Math.PI * 2);
      ctxRays.stroke();

      // Event Horizon
      ctxRays.fillStyle = '#000000';
      ctxRays.beginPath();
      ctxRays.arc(lensX, midY, rsPx, 0, Math.PI * 2);
      ctxRays.fill();
      ctxRays.strokeStyle = 'rgba(255, 255, 255, 0.6)';
      ctxRays.lineWidth = 1.5;
      ctxRays.stroke();

      // Strong field ray trajectories from data if available
      if (data.ray_bundle && data.ray_bundle.length > 0) {
        data.ray_bundle.forEach((rb) => {
          if (rb.x_rs && rb.y_rs) {
            ctxRays.beginPath();
            const scale = rsPx;
            for (let i = 0; i < rb.x_rs.length; i++) {
              const px = lensX + rb.x_rs[i] * scale;
              const py = midY - rb.y_rs[i] * scale;
              if (i === 0) ctxRays.moveTo(px, py);
              else ctxRays.lineTo(px, py);
            }
            if (rb.status === 'captured_by_bh') {
              ctxRays.strokeStyle = 'rgba(239, 68, 68, 0.7)';
              ctxRays.lineWidth = 1.2;
            } else {
              ctxRays.strokeStyle = 'rgba(56, 189, 248, 0.6)';
              ctxRays.lineWidth = 1.5;
            }
            ctxRays.stroke();
          }
        });
      }

      // Spacecraft on focal axis
      const recX = lensX + 380;
      drawSpacecraft(ctxRays, recX, midY, `BH Focal Line`);
    }
  }

  function drawSpacecraft(ctx, x, y, label) {
    ctx.save();
    ctx.translate(x, y);

    // Glowing dot
    ctx.fillStyle = '#38bdf8';
    ctx.shadowColor = '#38bdf8';
    ctx.shadowBlur = 12;
    ctx.beginPath();
    ctx.arc(0, 0, 5, 0, Math.PI * 2);
    ctx.fill();
    ctx.shadowBlur = 0;

    // Solar panels
    ctx.fillStyle = 'rgba(56, 189, 248, 0.7)';
    ctx.fillRect(-12, -2, 7, 4);
    ctx.fillRect(5, -2, 7, 4);

    // Label
    ctx.fillStyle = '#f1f5f9';
    ctx.font = '11px monospace';
    ctx.textAlign = 'center';
    ctx.fillText(label, 0, -12);

    ctx.restore();
  }

  // ==========================================
  // PANEL 2: Transverse Astroid Caustic Explorer
  // ==========================================
  function renderPanel2Astroid(data) {
    const w = cvAstroid.width;
    const h = cvAstroid.height;
    ctxAstroid.clearRect(0, 0, w, h);

    // Space background
    ctxAstroid.fillStyle = '#060a14';
    ctxAstroid.fillRect(0, 0, w, h);

    const cx = w / 2;
    const cy = h / 2;
    const aMeters = Math.max(data.a_caustic_m, 1.0);

    // Scaling: map 1.8 * aMeters to half-height (h/2 * 0.8)
    const scale = (h * 0.42) / (1.8 * aMeters);

    // Grid coordinates
    ctxAstroid.strokeStyle = 'rgba(255, 255, 255, 0.08)';
    ctxAstroid.lineWidth = 1;
    ctxAstroid.beginPath();
    ctxAstroid.moveTo(0, cy);
    ctxAstroid.lineTo(w, cy);
    ctxAstroid.moveTo(cx, 0);
    ctxAstroid.lineTo(cx, h);
    ctxAstroid.stroke();

    // Concentric scale rings
    [0.5, 1.0, 1.5].forEach((mult) => {
      ctxAstroid.beginPath();
      ctxAstroid.arc(cx, cy, mult * aMeters * scale, 0, Math.PI * 2);
      ctxAstroid.stroke();
    });

    // Astroid Boundary: X = a * cos^3(t), Y = a * sin^3(t)
    ctxAstroid.beginPath();
    const steps = 240;
    for (let i = 0; i <= steps; i++) {
      const theta = (i / steps) * 2 * Math.PI;
      const ax = aMeters * (Math.cos(theta) ** 3);
      const ay = aMeters * (Math.sin(theta) ** 3);
      const px = cx + ax * scale;
      const py = cy - ay * scale;
      if (i === 0) ctxAstroid.moveTo(px, py);
      else ctxAstroid.lineTo(px, py);
    }
    ctxAstroid.closePath();

    // Fill interior (4-image Einstein Cross zone)
    ctxAstroid.fillStyle = 'rgba(16, 185, 129, 0.12)';
    ctxAstroid.fill();

    // Stroke astroid caustic
    ctxAstroid.strokeStyle = '#38bdf8';
    ctxAstroid.lineWidth = 2.5;
    ctxAstroid.shadowColor = '#38bdf8';
    ctxAstroid.shadowBlur = 10;
    ctxAstroid.stroke();
    ctxAstroid.shadowBlur = 0;

    // Receiver Position (x0, y0)
    const satPx = cx + state.x0_m * scale;
    const satPy = cy - state.y0_m * scale;

    // Crosshairs for receiver
    ctxAstroid.strokeStyle = 'rgba(255, 255, 255, 0.35)';
    ctxAstroid.setLineDash([2, 3]);
    ctxAstroid.beginPath();
    ctxAstroid.moveTo(satPx, 0);
    ctxAstroid.lineTo(satPx, h);
    ctxAstroid.moveTo(0, satPy);
    ctxAstroid.lineTo(w, satPy);
    ctxAstroid.stroke();
    ctxAstroid.setLineDash([]);

    // Glowing Spacecraft Dot
    ctxAstroid.fillStyle = '#ffffff';
    ctxAstroid.shadowColor = '#ffffff';
    ctxAstroid.shadowBlur = 12;
    ctxAstroid.beginPath();
    ctxAstroid.arc(satPx, satPy, 6, 0, Math.PI * 2);
    ctxAstroid.fill();
    ctxAstroid.shadowBlur = 0;

    // Coordinate tag
    ctxAstroid.fillStyle = '#f1f5f9';
    ctxAstroid.font = '10px monospace';
    ctxAstroid.fillText(`(${state.x0_m.toFixed(1)}m, ${state.y0_m.toFixed(1)}m)`, satPx + 10, satPy - 10);
  }

  // Drag interaction on Astroid Canvas
  cvAstroid.addEventListener('mousedown', (e) => {
    state.is_dragging_astroid = true;
    updateAstroidFromMouse(e);
  });

  window.addEventListener('mousemove', (e) => {
    if (state.is_dragging_astroid) {
      updateAstroidFromMouse(e);
    }
  });

  window.addEventListener('mouseup', () => {
    if (state.is_dragging_astroid) {
      state.is_dragging_astroid = false;
    }
  });

  function updateAstroidFromMouse(e) {
    if (!state.last_data) return;
    const rect = cvAstroid.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    const w = cvAstroid.width;
    const h = cvAstroid.height;
    const cx = w / 2;
    const cy = h / 2;

    const aMeters = Math.max(state.last_data.a_caustic_m, 1.0);
    const scale = (h * 0.42) / (1.8 * aMeters);

    const clientScaleX = w / rect.width;
    const clientScaleY = h / rect.height;

    const canvasX = mx * clientScaleX;
    const canvasY = my * clientScaleY;

    state.x0_m = (canvasX - cx) / scale;
    state.y0_m = -(canvasY - cy) / scale;

    triggerSimulation();
  }

  // ==========================================
  // PANEL 3: Telescope Viewport & Bessel PSF
  // ==========================================
  function renderPanel3Detector(data) {
    const w = cvDetector.width;
    const h = cvDetector.height;
    ctxDetector.clearRect(0, 0, w, h);

    const cx = w / 2;
    const cy = h / 2;
    const coronagraphR = 48;
    const einsteinR = 86;

    // Space black background
    ctxDetector.fillStyle = '#02040a';
    ctxDetector.fillRect(0, 0, w, h);

    // Coronal Glow (Baumbach-Allen gradient)
    const corGrad = ctxDetector.createRadialGradient(cx, cy, coronagraphR, cx, cy, w * 0.65);
    corGrad.addColorStop(0, 'rgba(245, 158, 11, 0.4)');
    corGrad.addColorStop(0.3, 'rgba(245, 158, 11, 0.12)');
    corGrad.addColorStop(1, 'rgba(245, 158, 11, 0.0)');
    ctxDetector.fillStyle = corGrad;
    ctxDetector.beginPath();
    ctxDetector.arc(cx, cy, w * 0.65, 0, Math.PI * 2);
    ctxDetector.fill();

    // Central Occulting Coronagraph Mask (solid black)
    ctxDetector.fillStyle = '#000000';
    ctxDetector.beginPath();
    ctxDetector.arc(cx, cy, coronagraphR, 0, Math.PI * 2);
    ctxDetector.fill();
    ctxDetector.strokeStyle = 'rgba(245, 158, 11, 0.6)';
    ctxDetector.lineWidth = 1.5;
    ctxDetector.stroke();

    // Occulter label
    ctxDetector.fillStyle = 'rgba(255, 255, 255, 0.4)';
    ctxDetector.font = '9px monospace';
    ctxDetector.textAlign = 'center';
    ctxDetector.fillText('CORONAGRAPH', cx, cy + 3);

    // Base Einstein Ring (faint coherent ring)
    ctxDetector.strokeStyle = 'rgba(56, 189, 248, 0.25)';
    ctxDetector.lineWidth = 2.0;
    ctxDetector.beginPath();
    ctxDetector.arc(cx, cy, einsteinR, 0, Math.PI * 2);
    ctxDetector.stroke();

    // Render resolved bright spots or cusp arc based on quad solution
    if (data.image_angles_deg && data.image_angles_deg.length > 0) {
      const isCusp = data.regime === 'cusp_boundary';

      data.image_angles_deg.forEach((deg, idx) => {
        const rad = (deg * Math.PI) / 180.0;
        const spotX = cx + einsteinR * Math.cos(rad);
        const spotY = cy - einsteinR * Math.sin(rad);

        const intens = (data.image_intensities && data.image_intensities[idx]) || 5.0;
        const spotRadius = isCusp ? 7.5 : Math.min(6.5, 3.5 + intens * 0.2);

        // Glowing spot
        ctxDetector.shadowColor = isCusp ? '#facc15' : '#38bdf8';
        ctxDetector.shadowBlur = isCusp ? 16 : 12;
        ctxDetector.fillStyle = isCusp ? '#fef08a' : '#ffffff';
        ctxDetector.beginPath();
        ctxDetector.arc(spotX, spotY, spotRadius, 0, Math.PI * 2);
        ctxDetector.fill();
        ctxDetector.shadowBlur = 0;
      });

      // If cusp arc, draw connecting arc
      if (isCusp) {
        ctxDetector.strokeStyle = 'rgba(250, 204, 21, 0.85)';
        ctxDetector.lineWidth = 5.0;
        ctxDetector.shadowColor = '#facc15';
        ctxDetector.shadowBlur = 14;
        ctxDetector.beginPath();
        ctxDetector.arc(cx, cy, einsteinR, 0, Math.PI * 0.45);
        ctxDetector.stroke();
        ctxDetector.shadowBlur = 0;
      }
    }
  }

  function renderPanel3Psf(data) {
    const w = cvPsf.width;
    const h = cvPsf.height;
    ctxPsf.clearRect(0, 0, w, h);

    // Plot background
    ctxPsf.fillStyle = '#060a14';
    ctxPsf.fillRect(0, 0, w, h);

    const padLeft = 40;
    const padRight = 15;
    const padTop = 20;
    const padBottom = 30;

    const plotW = w - padLeft - padRight;
    const plotH = h - padTop - padBottom;

    // Grid lines
    ctxPsf.strokeStyle = 'rgba(255, 255, 255, 0.08)';
    ctxPsf.lineWidth = 1;

    // Y ticks
    [0.0, 0.25, 0.5, 0.75, 1.0].forEach((yNorm) => {
      const py = padTop + (1.0 - yNorm) * plotH;
      ctxPsf.beginPath();
      ctxPsf.moveTo(padLeft, py);
      ctxPsf.lineTo(w - padRight, py);
      ctxPsf.stroke();

      ctxPsf.fillStyle = 'rgba(255, 255, 255, 0.4)';
      ctxPsf.font = '8px monospace';
      ctxPsf.textAlign = 'right';
      ctxPsf.fillText(yNorm.toFixed(2), padLeft - 6, py + 3);
    });

    // Draw Bessel J0^2 Curve
    const rhoVals = data.psf_rho_m || [];
    const j0Sq = data.psf_j0_sq || [];

    if (j0Sq.length > 1) {
      ctxPsf.beginPath();
      for (let i = 0; i < j0Sq.length; i++) {
        const px = padLeft + (i / (j0Sq.length - 1)) * plotW;
        const py = padTop + (1.0 - j0Sq[i]) * plotH;
        if (i === 0) ctxPsf.moveTo(px, py);
        else ctxPsf.lineTo(px, py);
      }
      ctxPsf.strokeStyle = '#38bdf8';
      ctxPsf.lineWidth = 2.0;
      ctxPsf.shadowColor = '#38bdf8';
      ctxPsf.shadowBlur = 6;
      ctxPsf.stroke();
      ctxPsf.shadowBlur = 0;

      // Fill under curve
      ctxPsf.lineTo(padLeft + plotW, padTop + plotH);
      ctxPsf.lineTo(padLeft, padTop + plotH);
      ctxPsf.closePath();
      ctxPsf.fillStyle = 'rgba(56, 189, 248, 0.12)';
      ctxPsf.fill();
    }

    // Axes labels
    ctxPsf.fillStyle = 'rgba(255, 255, 255, 0.6)';
    ctxPsf.font = '9px sans-serif';
    ctxPsf.textAlign = 'center';
    ctxPsf.fillText('Transverse Offset ρ (m)', padLeft + plotW / 2, h - 8);

    ctxPsf.save();
    ctxPsf.translate(12, padTop + plotH / 2);
    ctxPsf.rotate(-Math.PI / 2);
    ctxPsf.fillText('Normalized I(ρ)', 0, 0);
    ctxPsf.restore();
  }

  // ==========================================
  // PANEL 4: Exoplanet Deconvolution
  // ==========================================
  function renderMatrixToCanvas(ctx, matrix) {
    if (!matrix || !matrix.length) return;
    const n = matrix.length;
    const cellW = ctx.canvas.width / n;
    const cellH = ctx.canvas.height / n;

    for (let r = 0; r < n; r++) {
      for (let c = 0; c < n; c++) {
        const val = Math.max(0, Math.min(1, matrix[r][c]));

        // Colormap for planet:
        // 0 = black space
        // 0.01 - 0.25 = deep blue ocean
        // 0.25 - 0.65 = green / earth land
        // > 0.65 = white polar ice
        let rCol, gCol, bCol;
        if (val <= 0.01) {
          rCol = 2; gCol = 4; bCol = 10;
        } else if (val < 0.25) {
          rCol = 12; gCol = 45; bCol = Math.floor(130 + (val / 0.25) * 80);
        } else if (val < 0.65) {
          const t = (val - 0.25) / 0.4;
          rCol = Math.floor(34 + t * 90);
          gCol = Math.floor(140 + t * 50);
          bCol = Math.floor(34 + t * 20);
        } else {
          const t = (val - 0.65) / 0.35;
          rCol = Math.floor(210 + t * 45);
          gCol = Math.floor(220 + t * 35);
          bCol = Math.floor(235 + t * 20);
        }

        ctx.fillStyle = `rgb(${rCol}, ${gCol}, ${bCol})`;
        ctx.fillRect(c * cellW, r * cellH, cellW, cellH);
      }
    }
  }

  function renderPanel4Deconv(data) {
    renderMatrixToCanvas(ctxGt, data.ground_truth);
    renderMatrixToCanvas(ctxNoisy, data.convolved_noisy);
    renderMatrixToCanvas(ctxRecon, data.deconvolved);
  }

  // Tradespace Heatmap
  async function renderPanel4Tradespace() {
    if (!state.tradespace_data) {
      try {
        const resp = await fetch('/api/research_analysis');
        if (resp.ok) {
          state.tradespace_data = await resp.json();
        }
      } catch (e) {
        console.error('Tradespace fetch error:', e);
        return;
      }
    }

    const ts = state.tradespace_data;
    if (!ts || !ts.snr_matrix) return;

    const w = cvTradespace.width;
    const h = cvTradespace.height;
    ctxTradespace.clearRect(0, 0, w, h);

    const padLeft = 45;
    const padBottom = 30;
    const padTop = 15;
    const padRight = 50;

    const plotW = w - padLeft - padRight;
    const plotH = h - padTop - padBottom;

    const snrMat = ts.snr_matrix;
    const nZ = snrMat.length;
    const nAp = snrMat[0].length;

    const cellW = plotW / nAp;
    const cellH = plotH / nZ;

    // Draw Heatmap Cells
    for (let i = 0; i < nZ; i++) {
      for (let j = 0; j < nAp; j++) {
        const snr = snrMat[i][j];
        // Colormap: purple (low SNR) -> cyan -> gold (high SNR > 20)
        const t = Math.min(1.0, snr / 30.0);
        const r = Math.floor(20 + t * 220);
        const g = Math.floor(20 + t * 180);
        const b = Math.floor(80 + (1 - t) * 120);

        ctxTradespace.fillStyle = `rgb(${r}, ${g}, ${b})`;
        ctxTradespace.fillRect(
          padLeft + j * cellW,
          padTop + (nZ - 1 - i) * cellH,
          cellW,
          cellH
        );
      }
    }

    // Axes and labels
    ctxTradespace.fillStyle = '#f1f5f9';
    ctxTradespace.font = '9px monospace';
    ctxTradespace.textAlign = 'center';
    ctxTradespace.fillText('Telescope Aperture (0.5m → 4.0m)', padLeft + plotW / 2, h - 8);

    ctxTradespace.save();
    ctxTradespace.translate(14, padTop + plotH / 2);
    ctxTradespace.rotate(-Math.PI / 2);
    ctxTradespace.fillText('Distance (550AU → 950AU)', 0, 0);
    ctxTradespace.restore();
  }

  // Tab switching
  document.querySelectorAll('.btn-tab').forEach((tabBtn) => {
    tabBtn.addEventListener('click', (e) => {
      document.querySelectorAll('.btn-tab').forEach((b) => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach((tc) => tc.classList.remove('active'));

      tabBtn.classList.add('active');
      const targetId = tabBtn.getAttribute('data-tab');
      document.getElementById(targetId).classList.add('active');
      state.active_tab = targetId;

      if (targetId === 'tab-tradespace') {
        renderPanel4Tradespace();
      }
    });
  });

  // Presets handling
  document.querySelectorAll('.btn-preset').forEach((pBtn) => {
    pBtn.addEventListener('click', () => {
      document.querySelectorAll('.btn-preset').forEach((b) => b.classList.remove('active'));
      pBtn.classList.add('active');

      const presetKey = pBtn.getAttribute('data-preset');
      const p = presets[presetKey];
      if (p) {
        inputLensType.value = p.lens_type;
        inputMass.value = p.mass_solar;
        inputZRec.value = p.z_rec_au;
        inputJ2.value = (p.j2 * 1e7).toFixed(1);
        inputWavelength.value = p.wavelength_um;
        inputAperture.value = p.aperture_m;
        inputTInt.value = p.t_int_days;
        inputDistPc.value = p.distance_source_pc;

        state.x0_m = p.x0_m;
        state.y0_m = p.y0_m;

        updateStateFromInputs();
        showToast(`Preset Loaded: ${pBtn.textContent}`);
      }
    });
  });

  // Slider inputs events
  [inputLensType, inputMass, inputZRec, inputJ2, inputWavelength, inputAperture, inputTInt, inputDistPc].forEach((el) => {
    el.addEventListener('input', updateStateFromInputs);
  });

  // Scientific Exports
  document.getElementById('btn-export-fits').addEventListener('click', () => {
    showToast('Generating NASA-standard FITS file...');
    const params = new URLSearchParams({
      lens_type: state.lens_type,
      mass_solar: state.mass_solar,
      z_rec_au: state.z_rec_au,
      j2: state.j2,
      wavelength_um: state.wavelength_um,
      aperture_m: state.aperture_m,
      t_int_days: state.t_int_days,
      distance_source_pc: state.distance_source_pc,
      x0_m: state.x0_m,
      y0_m: state.y0_m,
    });
    window.location.href = `/api/export_fits?${params.toString()}`;
  });

  document.getElementById('btn-export-csv').addEventListener('click', () => {
    showToast('Exporting radial PSF profile to CSV...');
    const params = new URLSearchParams({
      z_rec_au: state.z_rec_au,
      wavelength_um: state.wavelength_um,
    });
    window.location.href = `/api/export_csv?${params.toString()}`;
  });

  document.getElementById('btn-export-json').addEventListener('click', () => {
    showToast('Exporting simulation configuration to JSON...');
    const params = new URLSearchParams({
      lens_type: state.lens_type,
      mass_solar: state.mass_solar,
      z_rec_au: state.z_rec_au,
      j2: state.j2,
      x0_m: state.x0_m,
      y0_m: state.y0_m,
    });
    window.location.href = `/api/export_json?${params.toString()}`;
  });

  // Initial simulation run on page load
  updateStateFromInputs();

})();
