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

  // Target Resolver DOM Elements
  const selectTarget = document.getElementById('select-target');
  const sidebarTargetSelect = document.getElementById('sidebar-target-select');
  const inputTargetCustom = document.getElementById('input-target-custom');
  const inputArrivalYear = document.getElementById('input-arrival-year');
  const btnFetchTarget = document.getElementById('btn-fetch-target');
  const valTargetName = document.getElementById('val-target-name');

  const targetDisplayName = document.getElementById('target-display-name');
  const telemTargetHost = document.getElementById('telem-target-host');
  const telemTargetCoords = document.getElementById('telem-target-coords');
  const telemTargetDist = document.getElementById('telem-target-dist');
  const telemTargetConstellation = document.getElementById('telem-target-constellation');
  const telemTargetPm = document.getElementById('telem-target-pm');
  const telemTargetRadius = document.getElementById('telem-target-radius');

  const telemTelRadec = document.getElementById('telem-tel-radec');
  const telemTelConstellation = document.getElementById('telem-tel-constellation');
  const telemTelXyz = document.getElementById('telem-tel-xyz');
  const telemTelNorm = document.getElementById('telem-tel-norm');
  const telemEclLon = document.getElementById('telem-ecl-lon');
  const telemEclInc = document.getElementById('telem-ecl-inc');

  const telemLightDelay = document.getElementById('telem-light-delay');
  const telemCruiseTime = document.getElementById('telem-cruise-time');
  const telemImgDiameter = document.getElementById('telem-img-diameter');
  const telemPmDrift = document.getElementById('telem-pm-drift');
  const telemAnnualSweep = document.getElementById('telem-annual-sweep');
  const telemDataSource = document.getElementById('telem-data-source');

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

  // ==========================================
  // PANEL 5: Target Exoplanet Resolver & Ephemeris
  // ==========================================
  async function loadCuratedTargets() {
    try {
      const resp = await fetch('/api/targets');
      if (!resp.ok) return;
      const targets = await resp.json();

      if (selectTarget) {
        selectTarget.innerHTML = '';
        targets.forEach((tgt) => {
          const opt = document.createElement('option');
          opt.value = tgt.name;
          opt.textContent = `${tgt.name} (${tgt.distance_pc.toFixed(2)} pc / ${tgt.constellation})`;
          if (tgt.name === 'Proxima Centauri b') opt.selected = true;
          selectTarget.appendChild(opt);
        });
        const customOpt = document.createElement('option');
        customOpt.value = 'custom';
        customOpt.textContent = 'Custom Name or RA/Dec...';
        selectTarget.appendChild(customOpt);
      }
    } catch (e) {
      console.error('Error loading curated targets:', e);
    }
  }

  async function fetchTargetTelemetry(targetQuery, arrivalYear, autoUpdateSim = true) {
    if (!targetQuery) targetQuery = 'Proxima Centauri b';
    const year = arrivalYear !== undefined && arrivalYear !== null
      ? arrivalYear
      : (inputArrivalYear ? parseInt(inputArrivalYear.value, 10) : 2048);

    try {
      const resp = await fetch('/api/target_ephemeris', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target: targetQuery,
          z_rec_au: state.z_rec_au,
          arrival_year: year,
          cruise_velocity_au_yr: 20.0,
        }),
      });

      const res = await resp.json();
      if (res.status !== 'success' || !res.data) {
        showToast(res.message || 'Error resolving target');
        return;
      }

      const d = res.data;
      state.target_telemetry = d;

      // Update UI elements
      if (targetDisplayName) targetDisplayName.textContent = d.target_name;
      if (valTargetName) valTargetName.textContent = d.target_name.replace('Centauri', 'Cen');
      if (telemTargetHost) telemTargetHost.textContent = d.hostname;
      if (telemTargetCoords) {
        const raStr = `${d.target_ra_deg.toFixed(2)}°`;
        const decStr = `${d.target_dec_deg > 0 ? '+' : ''}${d.target_dec_deg.toFixed(2)}°`;
        telemTargetCoords.textContent = `${raStr} / ${decStr} (Epoch ${d.arrival_year || 2000})`;
      }
      if (telemTargetDist) {
        telemTargetDist.textContent = `${d.target_distance_pc.toFixed(2)} pc (${d.target_distance_ly.toFixed(2)} ly)`;
      }
      if (telemTargetConstellation) telemTargetConstellation.textContent = d.target_constellation;
      if (telemTargetPm) {
        telemTargetPm.textContent = `${d.target_pmra_mas_yr.toFixed(1)}, ${d.target_pmdec_mas_yr.toFixed(1)} mas/yr (Total: ${d.target_pm_total_mas_yr.toFixed(1)})`;
      }
      if (telemTargetRadius) telemTargetRadius.textContent = `${d.target_pl_rade.toFixed(2)} R⊕`;

      // Telescope Antipode & Heliocentric Coords
      if (telemTelRadec) {
        const tRa = `${d.telescope_ra_deg.toFixed(2)}°`;
        const tDec = `${d.telescope_dec_deg > 0 ? '+' : ''}${d.telescope_dec_deg.toFixed(2)}°`;
        telemTelRadec.textContent = `${tRa} / ${tDec}`;
      }
      if (telemTelConstellation) telemTelConstellation.textContent = d.telescope_constellation;
      if (telemTelXyz) {
        const xStr = (d.x_au >= 0 ? '+' : '') + d.x_au.toFixed(1);
        const yStr = (d.y_au >= 0 ? '+' : '') + d.y_au.toFixed(1);
        const zStr = (d.z_au >= 0 ? '+' : '') + d.z_au.toFixed(1);
        telemTelXyz.textContent = `(${xStr}, ${yStr}, ${zStr}) AU`;
      }
      if (telemTelNorm) telemTelNorm.textContent = `${d.vector_norm_au.toFixed(1)} AU`;
      if (telemEclLon) telemEclLon.textContent = `${d.ecliptic_lon_deg.toFixed(2)}°`;
      if (telemEclInc) telemEclInc.textContent = `${d.ecliptic_inclination_deg.toFixed(2)}° out of ecliptic`;

      // Feasibility & Logistics
      if (telemLightDelay) {
        telemLightDelay.textContent = `${d.light_delay_days.toFixed(2)} light-days (${d.light_delay_hours.toFixed(1)} hrs)`;
      }
      if (telemCruiseTime) {
        telemCruiseTime.textContent = `${d.cruise_time_years.toFixed(1)} yrs (Solar Oberth @ ${d.cruise_velocity_au_yr} AU/yr)`;
      }
      if (telemImgDiameter) {
        telemImgDiameter.textContent = `D_img ≈ ${d.image_diameter_km.toFixed(1)} km (${Math.round(d.image_diameter_m).toLocaleString()} m)`;
      }
      if (telemPmDrift) {
        const kmh = (d.proper_motion_drift_km_s * 3600.0).toFixed(1);
        telemPmDrift.textContent = `${d.proper_motion_drift_m_s.toFixed(1)} m/s (${kmh} km/hr)`;
      }
      if (telemAnnualSweep) {
        telemAnnualSweep.textContent = `${Math.round(d.annual_lateral_drift_km).toLocaleString()} km / year`;
      }
      if (telemDataSource) telemDataSource.textContent = d.source;

      // Automatically sync target distance and trigger simulation update
      if (autoUpdateSim && d.target_distance_pc > 0) {
        inputDistPc.value = d.target_distance_pc;
        valDistPc.textContent = `${d.target_distance_pc.toFixed(2)} pc`;
        state.distance_source_pc = d.target_distance_pc;
        triggerSimulation();
      }
    } catch (err) {
      console.error('Target ephemeris error:', err);
    }
  }

  // Target event listeners
  if (selectTarget) {
    selectTarget.addEventListener('change', () => {
      const val = selectTarget.value;
      if (val === 'custom') {
        if (inputTargetCustom) inputTargetCustom.focus();
      } else {
        if (inputTargetCustom) inputTargetCustom.value = '';
        if (sidebarTargetSelect) sidebarTargetSelect.value = val;
        fetchTargetTelemetry(val);
        showToast(`Target Set: ${val}`);
      }
    });
  }

  if (sidebarTargetSelect) {
    sidebarTargetSelect.addEventListener('change', () => {
      const val = sidebarTargetSelect.value;
      if (val !== 'custom') {
        if (selectTarget) selectTarget.value = val;
        fetchTargetTelemetry(val);
        showToast(`Target Set: ${val}`);
      }
    });
  }

  if (btnFetchTarget) {
    btnFetchTarget.addEventListener('click', () => {
      const customVal = inputTargetCustom && inputTargetCustom.value.trim();
      const targetQuery = customVal || (selectTarget ? selectTarget.value : 'Proxima Centauri b');
      const year = inputArrivalYear ? parseInt(inputArrivalYear.value, 10) : 2048;
      fetchTargetTelemetry(targetQuery, year);
      showToast(`Resolving Target Ephemeris for ${targetQuery}...`);
    });
  }

  // Update target telemetry distance if z_rec changes
  inputZRec.addEventListener('input', () => {
    if (state.target_telemetry) {
      fetchTargetTelemetry(state.target_telemetry.target_name, state.target_telemetry.arrival_year, false);
    }
  });

  // ==========================================
  // PANEL 6: Target Triage, Sky Efficiency & Swarm Blur
  // ==========================================
  const cvSkyMap = document.getElementById('canvas-sky-map');
  const ctxSkyMap = cvSkyMap ? cvSkyMap.getContext('2d') : null;
  const skyMapHoverInfo = document.getElementById('sky-map-hover-info');
  let cachedSkyMapData = null;

  async function loadSkyEfficiencyMap() {
    if (!ctxSkyMap) return;
    try {
      const res = await fetch('/api/sky_efficiency?n_ra=72&n_dec=36');
      const json = await res.json();
      if (json.status !== 'success') return;
      cachedSkyMapData = json.data;
      renderSkyEfficiencyMap(cachedSkyMapData);
    } catch (err) {
      console.error('Sky efficiency map error:', err);
    }
  }

  function renderSkyEfficiencyMap(data) {
    if (!ctxSkyMap || !data) return;
    const w = cvSkyMap.width;
    const h = cvSkyMap.height;
    ctxSkyMap.clearRect(0, 0, w, h);

    const nDec = data.n_dec;
    const nRa = data.n_ra;
    const eff = data.efficiency_matrix;

    const cellW = w / nRa;
    const cellH = h / nDec;

    for (let r = 0; r < nDec; r++) {
      const canvasRow = (nDec - 1) - r;
      for (let c = 0; c < nRa; c++) {
        const val = eff[r][c];
        let red, green, blue;
        if (val < 0.35) {
          const t = val / 0.35;
          red = Math.floor(6 + t * 15);
          green = Math.floor(12 + t * 40);
          blue = Math.floor(35 + t * 120);
        } else if (val < 0.7) {
          const t = (val - 0.35) / 0.35;
          red = Math.floor(21 + t * 15);
          green = Math.floor(52 + t * 120);
          blue = Math.floor(155 + t * 40);
        } else {
          const t = (val - 0.7) / 0.3;
          red = Math.floor(36 + t * 60);
          green = Math.floor(172 + t * 50);
          blue = Math.floor(195 - t * 80);
        }

        ctxSkyMap.fillStyle = `rgb(${red}, ${green}, ${blue})`;
        ctxSkyMap.fillRect(c * cellW, canvasRow * cellH, cellW + 0.5, cellH + 0.5);
      }
    }

    // Celestial Equator (Dec = 0)
    ctxSkyMap.strokeStyle = 'rgba(255, 255, 255, 0.12)';
    ctxSkyMap.lineWidth = 1;
    const cy = h / 2;
    ctxSkyMap.beginPath();
    ctxSkyMap.moveTo(0, cy);
    ctxSkyMap.lineTo(w, cy);
    ctxSkyMap.stroke();

    // Ecliptic Equator indication
    ctxSkyMap.setLineDash([4, 4]);
    ctxSkyMap.strokeStyle = 'rgba(250, 204, 21, 0.45)';
    ctxSkyMap.beginPath();
    for (let c = 0; c <= w; c += 4) {
      const raRad = ((c / w) * 360.0) * (Math.PI / 180.0);
      const decEclDeg = 23.44 * Math.sin(raRad);
      const py = (1.0 - (decEclDeg + 90.0) / 180.0) * h;
      if (c === 0) ctxSkyMap.moveTo(c, py);
      else ctxSkyMap.lineTo(c, py);
    }
    ctxSkyMap.stroke();
    ctxSkyMap.setLineDash([]);

    // Candidate markers (✦)
    const candidates = data.candidates || [];
    candidates.forEach((cand) => {
      const px = (cand.tel_ra / 360.0) * w;
      const py = (1.0 - (cand.tel_dec + 90.0) / 180.0) * h;

      ctxSkyMap.fillStyle = '#facc15';
      ctxSkyMap.font = '12px sans-serif';
      ctxSkyMap.textAlign = 'center';
      ctxSkyMap.textBaseline = 'middle';
      ctxSkyMap.fillText('✦', px, py);

      ctxSkyMap.fillStyle = 'rgba(241, 245, 249, 0.85)';
      ctxSkyMap.font = '9px monospace';
      ctxSkyMap.fillText(cand.name, px, py - 9);
    });
  }

  if (cvSkyMap) {
    cvSkyMap.addEventListener('mousemove', (e) => {
      if (!cachedSkyMapData) return;
      const rect = cvSkyMap.getBoundingClientRect();
      const scaleX = cvSkyMap.width / rect.width;
      const scaleY = cvSkyMap.height / rect.height;
      const mx = (e.clientX - rect.left) * scaleX;
      const my = (e.clientY - rect.top) * scaleY;

      const ra = (mx / cvSkyMap.width) * 360.0;
      const dec = 90.0 - (my / cvSkyMap.height) * 180.0;

      let hoveredCand = null;
      for (const cand of (cachedSkyMapData.candidates || [])) {
        const cx = (cand.tel_ra / 360.0) * cvSkyMap.width;
        const cy = (1.0 - (cand.tel_dec + 90.0) / 180.0) * cvSkyMap.height;
        const dist = Math.hypot(mx - cx, my - cy);
        if (dist <= 12) {
          hoveredCand = cand;
          break;
        }
      }

      if (hoveredCand && skyMapHoverInfo) {
        skyMapHoverInfo.innerHTML = `<strong>${hoveredCand.name}</strong> | Target: (${hoveredCand.target_ra.toFixed(1)}°, ${hoveredCand.target_dec.toFixed(1)}°) | Antipode: (${hoveredCand.tel_ra.toFixed(1)}°, ${hoveredCand.tel_dec.toFixed(1)}°) | Dist: ${hoveredCand.dist_pc.toFixed(2)} pc`;
      } else if (skyMapHoverInfo) {
        const nRa = cachedSkyMapData.n_ra;
        const nDec = cachedSkyMapData.n_dec;
        const c = Math.min(nRa - 1, Math.max(0, Math.floor((ra / 360.0) * nRa)));
        const r = Math.min(nDec - 1, Math.max(0, Math.floor(((dec + 90.0) / 180.0) * nDec)));
        const effVal = cachedSkyMapData.efficiency_matrix[r][c];
        skyMapHoverInfo.textContent = `Antipode RA: ${ra.toFixed(1)}°, Dec: ${dec.toFixed(1)}° | SGL Efficiency: ${(effVal * 100).toFixed(1)}%`;
      }
    });

    cvSkyMap.addEventListener('mouseleave', () => {
      if (skyMapHoverInfo) {
        skyMapHoverInfo.textContent = 'Hover over sky or target markers to inspect efficiency';
      }
    });
  }

  // Candidate Evaluation Form
  const evalName = document.getElementById('eval-name');
  const evalDist = document.getElementById('eval-dist');
  const evalRa = document.getElementById('eval-ra');
  const evalDec = document.getElementById('eval-dec');
  const evalRadius = document.getElementById('eval-radius');
  const evalRot = document.getElementById('eval-rot');
  const evalPm = document.getElementById('eval-pm');
  const evalLocked = document.getElementById('eval-locked');
  const btnEvalCandidate = document.getElementById('btn-eval-candidate');

  const evalScoreVal = document.getElementById('eval-score-val');
  const evalTierVal = document.getElementById('eval-tier-val');
  const coalignmentAlert = document.getElementById('coalignment-alert');
  const barSnr = document.getElementById('bar-snr');
  const valSubSnr = document.getElementById('val-sub-snr');
  const barLogistics = document.getElementById('bar-logistics');
  const valSubLogistics = document.getElementById('val-sub-logistics');
  const barEcliptic = document.getElementById('bar-ecliptic');
  const valSubEcliptic = document.getElementById('val-sub-ecliptic');
  const barBlur = document.getElementById('bar-blur');
  const valSubBlur = document.getElementById('val-sub-blur');

  async function evaluateCandidate() {
    if (!evalName) return;
    const payload = {
      name: evalName.value.trim() || 'Custom Discovery',
      dist_pc: parseFloat(evalDist.value) || 10.0,
      ra_deg: parseFloat(evalRa.value) || 0.0,
      dec_deg: parseFloat(evalDec.value) || 0.0,
      radius_earth: parseFloat(evalRadius.value) || 1.0,
      rot_period_hrs: parseFloat(evalRot.value) || 24.0,
      proper_motion_mas_yr: parseFloat(evalPm.value) || 100.0,
      tidally_locked: evalLocked ? evalLocked.checked : false,
      z_rec_au: state.z_rec_au || 650.0,
    };

    try {
      const res = await fetch('/api/evaluate_candidate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const json = await res.json();
      if (json.status !== 'success') {
        showToast('Evaluation failed: ' + (json.message || 'unknown error'), true);
        return;
      }

      const c = json.candidate;
      const co = json.coalignment;

      if (evalScoreVal) evalScoreVal.textContent = c.sgl_score.toFixed(1);
      if (evalTierVal) {
        evalTierVal.textContent = c.tier;
        evalTierVal.className = 'tier-pill ' + (c.sgl_score >= 72 ? 'tier-1' : c.sgl_score >= 50 ? 'tier-2' : 'tier-3');
      }

      if (barSnr) barSnr.style.width = `${Math.round(c.snr_score * 100)}%`;
      if (valSubSnr) valSubSnr.textContent = c.snr_score.toFixed(2);
      if (barLogistics) barLogistics.style.width = `${Math.round(c.scan_logistics_score * 100)}%`;
      if (valSubLogistics) valSubLogistics.textContent = c.scan_logistics_score.toFixed(2);
      if (barEcliptic) barEcliptic.style.width = `${Math.round(c.ecliptic_access_score * 100)}%`;
      if (valSubEcliptic) valSubEcliptic.textContent = c.ecliptic_access_score.toFixed(2);
      if (barBlur) barBlur.style.width = `${Math.round(c.blur_immunity_score * 100)}%`;
      if (valSubBlur) valSubBlur.textContent = c.blur_immunity_score.toFixed(2);

      if (coalignmentAlert) {
        coalignmentAlert.textContent = co.message;
        coalignmentAlert.className = 'coalignment-alert ' + (co.is_coaligned ? 'coaligned' : 'independent');
      }

      showToast(`Evaluated ${c.name}: SGL Score ${c.sgl_score}`);
    } catch (err) {
      console.error('Candidate evaluation error:', err);
    }
  }

  if (btnEvalCandidate) {
    btnEvalCandidate.addEventListener('click', evaluateCandidate);
  }

  // Motion Blur & Swarm Simulator
  const cvBlurSingle = document.getElementById('canvas-blur-single');
  const ctxBlurSingle = cvBlurSingle ? cvBlurSingle.getContext('2d') : null;
  const cvBlurSwarm = document.getElementById('canvas-blur-swarm');
  const ctxBlurSwarm = cvBlurSwarm ? cvBlurSwarm.getContext('2d') : null;

  const blurFleetSize = document.getElementById('blur-fleet-size');
  const valFleetSize = document.getElementById('val-fleet-size');
  const blurRotPeriod = document.getElementById('blur-rot-period');
  const blurLocked = document.getElementById('blur-locked');
  const btnRunBlur = document.getElementById('btn-run-blur');
  const titleSwarmNsat = document.getElementById('title-swarm-nsat');

  const metricSingleEta = document.getElementById('metric-single-eta');
  const metricSingleTime = document.getElementById('metric-single-time');
  const metricSingleRmse = document.getElementById('metric-single-rmse');
  const badgeSingleStatus = document.getElementById('badge-single-status');

  const metricSwarmEta = document.getElementById('metric-swarm-eta');
  const metricSwarmTime = document.getElementById('metric-swarm-time');
  const metricSwarmRmse = document.getElementById('metric-swarm-rmse');
  const badgeSwarmStatus = document.getElementById('badge-swarm-status');

  if (blurFleetSize) {
    blurFleetSize.addEventListener('input', () => {
      const val = blurFleetSize.value;
      if (valFleetSize) valFleetSize.textContent = `${val} Craft`;
      if (titleSwarmNsat) titleSwarmNsat.textContent = `N = ${val}`;
    });
  }

  async function runSwarmBlurSimulation() {
    if (!ctxBlurSingle || !ctxBlurSwarm) return;
    const nSat = blurFleetSize ? parseInt(blurFleetSize.value, 10) : 8;
    const rotH = blurRotPeriod ? parseFloat(blurRotPeriod.value) : 24.0;
    const isLocked = blurLocked ? blurLocked.checked : false;

    const dImgKm = (state.target_telemetry && state.target_telemetry.image_diameter_km) || 4.2;

    const payload = {
      image_diameter_km: dImgKm,
      grid_pixels: 32,
      planet_rot_period_hours: rotH,
      tidally_locked: isLocked,
      num_satellites: nSat,
      integration_time_per_pixel_s: (state.t_int_days || 1.0) * 86400.0,
      max_lateral_accel_m_s2: 1e-4,
      v_drift_m_s: (state.target_telemetry && state.target_telemetry.proper_motion_drift_m_s) || 15.0,
      snr: 25.0,
    };

    try {
      const res = await fetch('/api/swarm_blur_sim', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const json = await res.json();
      if (json.status !== 'success') return;

      const single = json.single;
      const swarm = json.swarm;

      renderMatrixToCanvas(ctxBlurSingle, single.reconstructed_image);
      renderMatrixToCanvas(ctxBlurSwarm, swarm.reconstructed_image);

      if (metricSingleEta) metricSingleEta.textContent = single.eta_blur.toFixed(2);
      if (metricSingleTime) metricSingleTime.textContent = `${Math.round(single.scan_time_days)} days`;
      if (metricSingleRmse) metricSingleRmse.textContent = single.rmse.toFixed(3);
      if (badgeSingleStatus) {
        if (single.eta_blur > 1.0) {
          badgeSingleStatus.textContent = `Severe Blur (η = ${single.eta_blur.toFixed(1)})`;
          badgeSingleStatus.className = 'badge badge-warning';
        } else {
          badgeSingleStatus.textContent = 'Sharp';
          badgeSingleStatus.className = 'badge badge-success';
        }
      }

      if (metricSwarmEta) metricSwarmEta.textContent = swarm.eta_blur.toFixed(2);
      if (metricSwarmTime) metricSwarmTime.textContent = `${Math.round(swarm.scan_time_days)} days`;
      if (metricSwarmRmse) metricSwarmRmse.textContent = swarm.rmse.toFixed(3);
      if (badgeSwarmStatus) {
        if (swarm.eta_blur <= 1.0) {
          badgeSwarmStatus.textContent = `Sharp Recovery (η = ${swarm.eta_blur.toFixed(2)})`;
          badgeSwarmStatus.className = 'badge badge-success';
        } else {
          badgeSwarmStatus.textContent = `Residual Blur (η = ${swarm.eta_blur.toFixed(1)})`;
          badgeSwarmStatus.className = 'badge badge-warning';
        }
      }

      showToast(`Simulated N=1 vs N=${nSat} Swarm (RMSE: ${single.rmse.toFixed(3)} → ${swarm.rmse.toFixed(3)})`);
    } catch (err) {
      console.error('Swarm blur simulation error:', err);
    }
  }

  if (btnRunBlur) {
    btnRunBlur.addEventListener('click', runSwarmBlurSimulation);
  }

  // Ranked Exoplanet Catalog Table
  const tbodyRankedCandidates = document.getElementById('tbody-ranked-candidates');
  const badgeTopTarget = document.getElementById('badge-top-target');

  async function loadRankedCatalog() {
    if (!tbodyRankedCandidates) return;
    try {
      const res = await fetch(`/api/ranking?z_rec_au=${state.z_rec_au || 650.0}`);
      const json = await res.json();
      if (json.status !== 'success') return;
      const list = json.data || [];

      if (list.length > 0 && badgeTopTarget) {
        badgeTopTarget.textContent = `Top Target: ${list[0].name} (${list[0].sgl_score}/100)`;
      }

      tbodyRankedCandidates.innerHTML = '';
      list.forEach((cand, idx) => {
        const tr = document.createElement('tr');

        let tierClass = 'score-tier-2';
        if (cand.sgl_score >= 72.0) tierClass = 'score-tier-1';
        else if (cand.sgl_score < 50.0) tierClass = 'score-tier-inv';
        else if (Math.abs(cand.ecliptic_lat_deg) > 30.0) tierClass = 'score-tier-3';

        tr.innerHTML = `
          <td><strong>#${idx + 1}</strong></td>
          <td><strong>${cand.name}</strong></td>
          <td>${cand.dist_pc.toFixed(2)} pc</td>
          <td>${cand.ra_deg.toFixed(1)}°, ${cand.dec_deg.toFixed(1)}°</td>
          <td>${cand.telescope_ra_deg.toFixed(1)}°, ${cand.telescope_dec_deg.toFixed(1)}°</td>
          <td>${cand.ecliptic_lat_deg.toFixed(1)}°</td>
          <td>${cand.image_diameter_km.toFixed(1)} km</td>
          <td><span class="triage-score-badge ${tierClass}">${cand.sgl_score.toFixed(1)}</span></td>
          <td><small>${cand.tier}</small></td>
          <td>
            <button class="btn-table-action" data-name="${cand.name}">
              Load
            </button>
          </td>
        `;

        const btn = tr.querySelector('.btn-table-action');
        if (btn) {
          btn.addEventListener('click', () => {
            if (evalName) evalName.value = cand.name;
            if (evalDist) evalDist.value = cand.dist_pc;
            if (evalRa) evalRa.value = cand.ra_deg;
            if (evalDec) evalDec.value = cand.dec_deg;
            if (evalRadius) evalRadius.value = cand.radius_earth;
            if (evalRot) evalRot.value = cand.rot_period_hrs;
            if (evalPm) evalPm.value = cand.proper_motion_mas_yr;
            if (evalLocked) evalLocked.checked = cand.tidally_locked;

            if (blurRotPeriod) blurRotPeriod.value = cand.rot_period_hrs;
            if (blurLocked) blurLocked.checked = cand.tidally_locked;

            evaluateCandidate();
            runSwarmBlurSimulation();
            fetchTargetTelemetry(cand.name, 2048, true);
            showToast(`Loaded ${cand.name} into simulator & triage engine`);
          });
        }

        tbodyRankedCandidates.appendChild(tr);
      });
    } catch (err) {
      console.error('Ranked catalog load error:', err);
    }
  }

  // Initial simulation run, target telemetry & triage on page load
  loadCuratedTargets();
  fetchTargetTelemetry('Proxima Centauri b', 2048, false);
  loadSkyEfficiencyMap();
  evaluateCandidate();
  runSwarmBlurSimulation();
  loadRankedCatalog();
  updateStateFromInputs();

})();

