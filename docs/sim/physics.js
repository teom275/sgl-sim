/*
 * sgl-sim web physics: a direct JavaScript port of the formulas used by the
 * Python package (sgl_sim.relativity / optics / caustics). Constants match
 * astropy (CODATA 2018 / IAU 2015) so the numbers agree with the Python API.
 */
(function (global) {
  "use strict";

  const G = 6.6743e-11;
  const C = 299792458.0;
  const M_SUN = 1.988409870698051e30;
  const R_SUN = 6.957e8;
  const AU = 1.495978707e11;
  const J2_SUN = 2.2e-7;

  /** Schwarzschild radius in metres for a mass in solar masses. */
  const schwarzschild = (mSun) => (2 * G * mSun * M_SUN) / (C * C);

  /** Axis crossing distance z(b) = b^2 / (2 R_s), b in R_sun, result in AU. */
  function focalDistanceAU(bRsun, mSun) {
    const b = bRsun * R_SUN;
    return (b * b) / (2 * schwarzschild(mSun)) / AU;
  }

  /** Minimum focal distance for a lens of radius rRsun, in AU. */
  const zMinAU = (mSun, rRsun) => focalDistanceAU(rRsun, mSun);

  /** Einstein ring at receiver distance zAU. */
  function einsteinRing(zAU, mSun) {
    const rs = schwarzschild(mSun);
    const z = zAU * AU;
    const b = Math.sqrt(2 * rs * z);
    const theta = Math.sqrt((2 * rs) / z);
    return {
      bRing_m: b,
      bRing_rsun: b / R_SUN,
      thetaE_rad: theta,
      thetaE_arcsec: (theta * 180 / Math.PI) * 3600,
    };
  }

  /** Peak on-axis wave magnification mu_max = 4 pi^2 R_s / lambda. */
  const peakGain = (lambdaM, mSun) => (4 * Math.PI * Math.PI * schwarzschild(mSun)) / lambdaM;

  /** Bessel J0 (Numerical Recipes rational approximation, |err| < 1e-8). */
  function besselJ0(x) {
    const ax = Math.abs(x);
    if (ax < 8.0) {
      const y = x * x;
      const n = 57568490574.0 + y * (-13362590354.0 + y * (651619640.7 +
        y * (-11214424.18 + y * (77392.33017 + y * -184.9052456))));
      const d = 57568490411.0 + y * (1029532985.0 + y * (9494680.718 +
        y * (59272.64853 + y * (267.8532712 + y))));
      return n / d;
    }
    const z = 8.0 / ax;
    const y = z * z;
    const xx = ax - 0.785398164;
    const p = 1.0 + y * (-0.1098628627e-2 + y * (0.2734510407e-4 +
      y * (-0.2073370639e-5 + y * 0.2093887211e-6)));
    const q = -0.1562499995e-1 + y * (0.1430488765e-3 +
      y * (-0.6911147651e-5 + y * (0.7621095161e-6 - y * 0.934935152e-7)));
    return Math.sqrt(0.636619772 / ax) * (Math.cos(xx) * p - z * Math.sin(xx) * q);
  }

  /** Normalised PSF J0^2(k theta_E rho) at offset rho (m). */
  function psf(rhoM, zAU, lambdaM, mSun) {
    const k = (2 * Math.PI) / lambdaM;
    const arg = k * einsteinRing(zAU, mSun).thetaE_rad * rhoM;
    const j = besselJ0(arg);
    return j * j;
  }

  /** Radius of the first dark ring of the PSF, metres. */
  function psfFirstZero(zAU, lambdaM, mSun) {
    const k = (2 * Math.PI) / lambdaM;
    return 2.404825557695773 / (k * einsteinRing(zAU, mSun).thetaE_rad);
  }

  /** Astroid semi-width a = 2 R J2 z / b_ring (as in sgl_sim.caustics), metres. */
  function astroidSemiWidth(zAU, j2, mSun = 1, rRsun = 1) {
    const b = einsteinRing(zAU, mSun).bRing_m;
    return (2 * rRsun * R_SUN * j2 * zAU * AU) / b;
  }

  /** Size of the astroid relative to J2 = 2.2e-7 at 650 AU. */
  const causticScale = (j2, zAU) => astroidSemiWidth(zAU, j2) / astroidSemiWidth(650, J2_SUN);

  /**
   * Image azimuths on the Einstein ring for a receiver at (u, v) = (x0/a, y0/a):
   * roots of f(phi) = u sin(phi) - v cos(phi) - 0.5 sin(2 phi).
   */
  function einsteinCross(u, v) {
    const f = (p) => u * Math.sin(p) - v * Math.cos(p) - 0.5 * Math.sin(2 * p);
    const df = (p) => u * Math.cos(p) + v * Math.sin(p) - Math.cos(2 * p);
    const N = 720;
    const roots = [];
    for (let i = 0; i < N; i++) {
      let a = (2 * Math.PI * i) / N;
      let b = (2 * Math.PI * (i + 1)) / N;
      let fa = f(a);
      const fb = f(b);
      if (fa === 0) { roots.push(a); continue; }
      if (fa * fb > 0) continue;
      for (let it = 0; it < 50; it++) {
        const m = 0.5 * (a + b);
        const fm = f(m);
        if (fa * fm <= 0) { b = m; } else { a = m; fa = fm; }
      }
      const r = (0.5 * (a + b)) % (2 * Math.PI);
      if (!roots.some((x) => Math.min(Math.abs(x - r), 2 * Math.PI - Math.abs(x - r)) < 1e-4)) roots.push(r);
    }
    // Regularised magnification ~ 1 / |f'|, normalised to the brightest image.
    let mags = roots.map((r) => Math.min(20, Math.max(0.5, 1 / (Math.abs(df(r)) + 0.05))));
    const mx = Math.max(...mags, 1e-12);
    mags = mags.map((m) => m / mx);
    const val = Math.pow(Math.abs(u), 2 / 3) + Math.pow(Math.abs(v), 2 / 3);
    const regime = Math.abs(val - 1) <= 0.03 ? "edge" : val < 1 ? "inside" : "outside";
    return { roots, mags, astroidValue: val, regime };
  }

  global.SGL = {
    G, C, M_SUN, R_SUN, AU, J2_SUN,
    schwarzschild, focalDistanceAU, zMinAU, einsteinRing, peakGain,
    besselJ0, psf, psfFirstZero, astroidSemiWidth, causticScale, einsteinCross,
  };
})(typeof window !== "undefined" ? window : globalThis);
