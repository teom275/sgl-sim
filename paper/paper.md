---
title: 'sgl-sim: Scientific Mission Design & Wave Optics Simulator for Gravitational Lens Telescopes'
tags:
  - Python
  - astrophysics
  - gravitational lensing
  - solar gravitational lens
  - wave optics
  - mission design
  - astropy
authors:
  - name: Teo Maggio
    affiliation: 1
affiliations:
  - name: Independent Researcher
    index: 1
date: 18 October 2026
bibliography: paper.bib
---

# Summary

Gravitational lensing, first conceptualized in general relativity by @Einstein1936, enables natural astrophysical telescopes of unprecedented magnification and resolving power. When aligned with a distant source, the curved spacetime surrounding a star or compact object bends incoming planar wavefronts toward a semi-infinite focal line. In our Solar System, the Solar Gravitational Lens (SGL) focal line begins at $z_{\min} \approx 547.8\text{ AU}$, offering optical magnifications up to $\mu_{\max} \sim 10^{11}$ and angular resolutions on the order of nano-arcseconds [@TuryshevToth2017]. Such capabilities unlock direct multipixel surface imaging and high-resolution spectroscopy of habitable exoplanets at interstellar distances [@Turyshev2020NIAC].

`sgl-sim` is an open-source, JOSS-compliant scientific Python library and interactive mission-design simulator. It models relativistic null geodesics in Schwarzschild spacetime, physical wave-optics point spread functions (PSF), stellar oblateness perturbations ($J_2$ quadrupole astroid caustics), coronal noise contamination, and regularized Wiener deconvolution for exoplanet albedo reconstructions. In addition to a modular Python API integrating seamlessly with `astropy.units` and `astropy.io.fits`, `sgl-sim` provides an interactive mission trade-space dashboard.

# Statement of Need

Existing gravitational lensing software packages in astrophysics—most notably `lenstronomy` [@Birrer2021]—are tailored primarily for cosmological gravitational lensing. These tools simulate macroscopic galaxy-galaxy or cluster-scale lenses with large impact parameters, where observers reside at gigaparsec scales and the thin-lens geometric approximation dominates. 

In contrast, focal-line spacecraft missions such as the NASA NIAC Solar Gravitational Lens mission architecture require specialized modeling across multiple coupled regimes:
1. **Focal-Line Spacecraft Navigation**: Spacecraft operate directly along or across the optical caustic line at heliocentric distances between $548\text{ AU}$ and $1000\text{ AU}$.
2. **Diffraction and Wave Optics**: Geometric optics exhibits an unphysical singularity along the optical axis; rigorous Helmholtz-Kirchhoff wave optics using Bessel $J_0^2$ kernels is necessary to model finite wave magnification and spatial coherence [@TuryshevToth2017].
3. **Multipole Stellar Caustics**: Solar and stellar oblateness (measured by the quadrupole moment $J_2$) splits the focal line into an astroid caustic in the transverse plane, generating distinct Einstein Cross configurations and fold/cusp caustic bifurcations [@TuryshevToth2020].
4. **Mission Tradespaces and Noise Budgets**: Real spacecraft detector images are dominated by solar coronal background noise (Baumbach-Allen distribution) and require deconvolution pipelines tuned to the narrow SGL PSF.

`sgl-sim` fills this critical gap in the astronomical software ecosystem by providing mission planners, instrumentalists, and astrophysicists with an integrated suite of verified analytical and numerical tools designed specifically for local gravitational lens telescope missions.

# Mathematical Formulation

## Relativistic Geodesics & Focal Crossing

In a Schwarzschild metric describing a static lens of mass $M$, the Schwarzschild radius is:
$$R_s = \frac{2GM}{c^2}$$
The photon sphere radius is $r_{\text{ph}} = 1.5 R_s$, and the critical impact parameter below which photon capture occurs is:
$$b_c = \frac{3\sqrt{3}}{2} R_s \approx 2.598076 R_s$$

For weak-field deflection around stars ($b \gg R_s$), the deflection angle is $\alpha(b) = 2R_s / b$. Paraxial rays converge onto the optical axis at a focal distance:
$$z(b) = \frac{b^2}{2R_s}$$
The minimum focal distance for a stellar lens of physical radius $R_{\text{star}}$ occurs for grazing rays ($b = R_{\text{star}}$):
$$z_{\min} = \frac{R_{\text{star}}^2}{2R_s}$$
For solar parameters ($M = 1 M_\odot, R = 1 R_\odot$), $z_{\min} \approx 547.8\text{ AU}$. Any ray with $b < R_{\text{star}}$ is blocked by the stellar disk.

In strong gravitational fields (e.g., stellar-mass or supermassive black holes), `sgl-sim` solves the exact null geodesic differential equation in terms of inverse radius $u = 1/r$:
$$\frac{d^2u}{d\phi^2} + u = \frac{3}{2} R_s u^2$$
integrated numerically via an adaptive Runge-Kutta 4(5) scheme (`scipy.integrate.solve_ivp`). Rays with $b \le b_c$ are tagged as captured.

## Wave-Optics Point Spread Function (PSF)

At a receiver distance $z_{\text{rec}} \ge z_{\min}$, the angular Einstein radius is $\theta_E = \sqrt{2R_s / z_{\text{rec}}}$, and the corresponding impact parameter is $b_{\text{ring}} = \sqrt{2R_s z_{\text{rec}}}$. Wave diffraction yields a finite on-axis magnification at wavelength $\lambda$:
$$\mu_{\max} = \frac{4\pi^2 R_s}{\lambda}$$
The transverse intensity distribution across the focal plane as a function of radial displacement $\rho$ follows the zero-order Bessel function of the first kind:
$$I(\rho) = \mu_{\max} \left[ J_0\left(\frac{2\pi}{\lambda} \theta_E \rho \right) \right]^2$$

## Quadrupole Perturbations ($J_2$) & Astroid Caustics

Stellar rotation introduces a quadrupole potential perturbation characterized by the dimensionless parameter $J_2$ ($2.2 \times 10^{-7}$ for the Sun). This perturbation transforms the focal line into a four-cusped astroid caustic in the transverse receiver plane with semi-width:
$$a_{\text{caustic}}(z_{\text{rec}}) = 2 R_{\text{star}} J_2 \frac{z_{\text{rec}}}{b_{\text{ring}}}$$
The caustic boundary is parameterized by $X(\theta) = a_{\text{caustic}} \cos^3\theta, Y(\theta) = a_{\text{caustic}} \sin^3\theta$. A receiver inside the astroid observes four distinct stationary-phase images along the Einstein ring (Einstein Cross); crossing the caustic boundary causes pair annihilation, reducing the image count to two.

## Coronal Noise & Wiener Deconvolution

The dominant background noise source in the solar focal line is the solar K-corona, modeled via the empirical Baumbach-Allen distribution:
$$B_{\text{cor}}(r) = B_\odot \left( \frac{2.56 \times 10^{-6}}{r^6} + \frac{1.42 \times 10^{-6}}{r^{2.5}} + \frac{2.26 \times 10^{-8}}{r^{1.5}} \right)$$
where $r = b_{\text{ring}} / R_{\text{star}}$. The per-pixel signal-to-noise ratio (SNR) is evaluated for telescope aperture $D_{\text{tel}}$ and integration time $t_{\text{int}}$.

To reconstruct the surface of an exoplanet from the convolved, noise-degraded image $Y(f)$, `sgl-sim` implements a regularized 2D Wiener deconvolution filter:
$$\hat{O}(f) = \frac{H^*(f)}{|H(f)|^2 + 1/\text{SNR}^2} Y(f)$$
where $H(f)$ is the optical transfer function computed from the Bessel $J_0^2$ kernel. Quality metrics including Root Mean Square Error (RMSE) and Structural Similarity (SSIM) quantify recovery fidelity.

# Software Architecture

`sgl-sim` is organized as an Astropy-compatible scientific package structured in a clean `src/` layout:
- `sgl_sim.relativity`: Schwarzschild metrics, weak-field deflections, and strong-field null geodesic integrators.
- `sgl_sim.optics`: Focal line geometry, wave-optics Bessel PSF synthesis, and Einstein ring properties.
- `sgl_sim.caustics`: Analytical and numerical solutions to the $J_2$ quadrupolar lens equation, astroid geometry, and azimuthal ring intensity profiles.
- `sgl_sim.deconvolution`: Baumbach-Allen coronal noise models, SNR budgets, synthetic exoplanet generation, and 2D Wiener filtering.
- `sgl_sim.orbital`: Keplerian and hovering focal-line orbital mechanics, image cylinder geometry, and station-keeping $\Delta v$.
- `sgl_sim.tradespace`: Grid evaluators across $(z_{\text{rec}}, D_{\text{tel}})$ mission parameters.
- `sgl_sim.exporters`: Multi-extension NASA FITS (`astropy.io.fits`), CSV, and JSON exporters.
- `sgl_sim.web`: A synchronized interactive scientific dashboard powered by Flask, vanilla HTML5/Canvas, and responsive CSS.

# Acknowledgements

The author acknowledges foundational research on the Solar Gravitational Lens conducted by Slava G. Turyshev and Viktor T. Toth, as well as the broader Astropy community for developing core astronomical infrastructure [@Astropy2022; @Virtanen2020]. Software architecture, wave-optics algorithms, and code scaffolding were developed with assistance from Antigravity (Advanced Agentic Coding, Google DeepMind).

# References
