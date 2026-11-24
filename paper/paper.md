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
    orcid: 0009-0008-8025-8576
    affiliation: 1
affiliations:
  - name: Independent Researcher
    index: 1
date: 23 November 2026
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

## Exoplanet Triage & Rotational Motion Blur Modeling

On rotating exoplanets, single-spacecraft scans across the projected image cylinder $D_{\text{img}}$ can suffer severe rotational smearing when the scan duration exceeds the rotational smearing limit. The maximum dwell time before rotational blur exceeds one pixel of an $N_{\text{pix}} \times N_{\text{pix}}$ map is:
$$t_{\text{blur}} = \frac{P_{\text{rot}}}{\pi N_{\text{pix}}}$$
For a constellation of $N_{\text{sat}}$ spacecraft dividing the image cylinder, the total scan time is $t_{\text{scan}} = \frac{N_{\text{pix}}^2}{N_{\text{sat}}} t_{\text{dwell}}$, yielding the motion blur factor:
$$\eta_{\text{blur}} = \frac{t_{\text{scan}}}{t_{\text{blur}}}$$
When $\eta_{\text{blur}} > 1.0$, `sgl-sim` convolves the surface reconstruction with a latitude-dependent directional rotational blur kernel, quantitatively demonstrating how single spacecraft ($N=1$) produce smeared continent maps while multi-craft swarms ($N_{\text{sat}} \ge 4-8$) restore sharp surface feature fidelity (\autoref{fig:swarm}).

![Satellite swarm formation architectures, image-cylinder scanning patterns, and rotational motion-blur suppression as a function of spacecraft fleet size. (a) Transverse plane scanning architectures across the $D_{\text{img}}$ image cylinder. (b) Total mission scan time $t_{\text{scan}}$ versus fleet size $N_{\text{sat}}$ compared against critical rotational smearing limits for rapid, moderate, and tidally locked exoplanets. (c) Simulated 2D exoplanet surface albedo reconstructions under increasing rotational blur ($\eta_{\text{blur}}$), demonstrating how multi-spacecraft swarms ($N_{\text{sat}} \ge 6$) restore fine continent features. (d) Annual propulsion $\Delta v$ budget for station-keeping and proper-motion lateral drift tracking across candidate targets.\label{fig:swarm}](figures/figure1_swarm_patterns.png)

Candidates are ranked using a universal SGL Feasibility Index ($0 - 100$) evaluating photon flux SNR (30%), scan logistics and proper-motion drift (25%), ecliptic launch access $\cos^2\beta_{\text{ecl}}$ rewarding Solar Oberth / Jupiter gravity-assist trajectories (25%), and rotational blur immunity (20%). Spacecraft trajectory co-alignment across multi-planet systems (e.g., TRAPPIST-1 d, e, f) is computed within a $\le 3.0^\circ$ lateral propulsion deflection cone (\autoref{fig:trajectories}).

![3D Heliocentric SGL escape trajectories, all-sky observation efficiency projection, and exoplanet candidate tradespace. (a) 3D heliocentric corridors to $z_{\text{rec}} = 650\text{ AU}$ showing the Sun, Ecliptic plane disc, and $547.8\text{ AU}$ minimum focal sphere. (b) Full-sky Plate Carrée projection of SGL launch efficiency ($\cos^2\beta_{\text{ecl}}$) and target antipode distribution. (c) TRAPPIST-1 multi-planet co-alignment corridor demonstrating sequential retargeting of habitable planets d, e, and f within a $\Delta\theta \le 3.0^\circ$ deflection envelope. (d) Candidate mission tradespace plotting projected image cylinder diameter $D_{\text{img}}$ versus proper-motion lateral drift velocity $v_{\text{drift}}$, highlighting the optimal high-feasibility, low-drift corridor.\label{fig:trajectories}](figures/figure2_exoplanet_trajectories.png)

## Heliocentric Mission Trajectories & Swarm Flight Dynamics

All optical receivers operate entirely within our Solar System along hyperbolic heliocentric escape trajectories oriented toward the celestial antipode $(\alpha + 180^\circ, -\delta)$ of the chosen exoplanet. To reach the focal region ($z_{\text{rec}} \ge 547.8\text{ AU}$) within a reasonable mission timeline ($\sim 30\text{ years}$), the spacecraft executes a high-thrust Solar Oberth maneuver at perihelion $r_p \sim 0.05\text{ AU}$ ($\sim 10.8 R_\odot$), where the pre-burn velocity reaches $v_p = \sqrt{2GM_\odot / r_p} \approx 188.4\text{ km/s}$. A modest impulsive burn of $\Delta v = 5 - 12\text{ km/s}$ (or high-area-to-mass solar sail propulsion) amplifies the asymptotic hyperbolic excess velocity to:
$$v_\infty = \sqrt{(v_p + \Delta v)^2 - \frac{2GM_\odot}{r_p}} \approx 44 - 72\text{ km/s} \quad (9.2 - 15.2\text{ AU/yr})$$
allowing arrival at $650\text{ AU}$ within $30 - 45\text{ years}$.

Once in the focal region, solar gravitational acceleration is minuscule ($a_{\text{grav}} = GM_\odot / z_{\text{rec}}^2 \approx 1.4 \times 10^{-8}\text{ m/s}^2$ at $650\text{ AU}$), requiring a nominal annual hovering station-keeping budget of $\Delta v_{\text{hover}} \approx 0.44\text{ m/s/yr}$. The primary operational propulsion demand arises from tracking the stellar proper-motion lateral drift of the focal line:
$$v_{\text{drift}} = z_{\text{rec}} \mu$$
which ranges from $10.1\text{ m/s}$ ($318\text{ km/yr}$) for LHS 1140 b up to $94.3\text{ m/s}$ ($2970\text{ km/yr}$) for Teegarden's Star b, easily manageable with low-thrust electric ion propulsion (e.g., NEXT or miniature Hall-effect thrusters).

Across the transverse image cylinder ($D_{\text{img}} \approx 3 - 32\text{ km}$), `sgl-sim` models micro-satellite swarms in four geometric configurations:
1. **Concentric Ring Arrays ($N_{\text{sat}} \ge 6$):** Subdivides radial and azimuthal Fourier modes across the Einstein caustic.
2. **Hexagonal Close-Packed Grids ($N_{\text{sat}} = 7, 19$):** Minimizes inter-satellite baseline distances and provides uniform spatial quadrant scanning.
3. **Fermat Spiral Wheels ($N_{\text{sat}} \ge 8$):** Employs the golden angle $\theta_i = i \times 137.5^\circ, r_i = R\sqrt{i/N}$ to achieve optimal UV-plane aperture synthesis sampling without directional spatial aliasing.
4. **Linear Pushbroom Rakes:** Aligns spacecraft across the cylinder diameter to conduct synchronous parallel scans, reducing total scan duration by a factor of $1/N_{\text{sat}}$.

| Target Exoplanet | Distance (pc) | Radius ($R_\oplus$) | $P_{\text{rot}}$ (h) | Heliocentric Antipode $(\alpha, \delta)$ | $|\beta_{\text{ecl}}|$ ($^\circ$) | $D_{\text{img}}$ ($650\text{ AU}$) | $v_{\text{drift}}$ (m/s) | Min $N_{\text{sat}}$ | Feasibility Index | Primary Mission Tier |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| **Wolf 1061 c** | 4.31 | 1.66 | 429.6 | ($67.6^\circ, +12.7^\circ$) | 9.1 | 15.5 km | 17.3 | 4 | **91.6** | Tier 1 (Prime Near-Ecliptic) |
| **Ross 128 b** | 3.37 | 1.11 | 237.6 | ($356.9^\circ, -0.8^\circ$) | 0.5 | 13.2 km | 20.3 | 4 | **90.8** | Tier 1 (Equatorial / Ecliptic) |
| **Luyten b** | 3.80 | 1.18 | 446.4 | ($291.9^\circ, -5.2^\circ$) | 16.5 | 12.5 km | 55.8 | 4 | **85.8** | Tier 1 (Temperate Super-Earth) |
| **Tau Ceti e** | 3.65 | 1.80 | 35.0 | ($206.0^\circ, +15.9^\circ$) | 24.8 | 19.8 km | 28.7 | 8-12 | **84.8** | Tier 1 (Rapid Rotator / Swarm Req.) |
| **Teegarden b** | 3.83 | 1.05 | 117.6 | ($223.3^\circ, -16.9^\circ$) | 0.3 | 11.0 km | 94.3 | 6 | **84.3** | Tier 1 (High Drift Tracker) |
| **LHS 1140 b** | 14.99 | 1.73 | 314.4 | ($191.2^\circ, +15.3^\circ$) | 18.5 | 4.6 km | 10.1 | 2-4 | **79.9** | Tier 1 (Ultra-Low Drift / Dense) |
| **TRAPPIST-1 f** | 12.43 | 1.05 | 220.8 | ($166.6^\circ, +5.0^\circ$) | 0.6 | 3.4 km | 15.0 | 4 | **79.3** | Tier 1 (Co-aligned System Corridor) |
| **TRAPPIST-1 e** | 12.43 | 0.92 | 146.4 | ($166.6^\circ, +5.0^\circ$) | 0.6 | 3.0 km | 15.0 | 4-6 | **78.2** | Tier 1 (Prime Habitable Earth-size) |
| **Proxima Cen b**| 1.30 | 1.03 | 268.3 | ($37.3^\circ, +62.7^\circ$) | 44.8 | 31.8 km | 57.6 | 6 | **77.6** | Tier 1 (Maximum SNR / High $i_{\text{ecl}}$) |
| **TRAPPIST-1 d** | 12.43 | 0.79 | 97.2 | ($166.6^\circ, +5.0^\circ$) | 0.6 | 2.5 km | 15.0 | 6 | **76.8** | Tier 1 (Co-aligned System Corridor) |
: Prime exoplanet targets for SGL focal-line observation in our Solar System evaluated across heliocentric orbital coordinates, projected image cylinder diameter, proper-motion drift, required swarm size to suppress rotational blur, and universal SGL Feasibility Score. {#tbl:targets}

# Software Architecture

`sgl-sim` is organized as an Astropy-compatible scientific package structured in a clean `src/` layout:
- `sgl_sim.relativity`: Schwarzschild metrics, weak-field deflections, and strong-field null geodesic integrators.
- `sgl_sim.optics`: Focal line geometry, wave-optics Bessel PSF synthesis, and Einstein ring properties.
- `sgl_sim.caustics`: Analytical and numerical solutions to the $J_2$ quadrupolar lens equation, astroid geometry, and azimuthal ring intensity profiles.
- `sgl_sim.deconvolution`: Baumbach-Allen coronal noise models, SNR budgets, synthetic exoplanet generation, and 2D Wiener filtering.
- `sgl_sim.radiometry`: Extended-source SGL photon budget, Baumbach-Allen corona photon noise, direct and blur signal flux decomposition.
- `sgl_sim.imaging`: Physical forward-model simulator of rotating exoplanets scanned by telescope swarms, including blur matrices, noise injection, and surface recovery.
- `sgl_sim.reference_bodies`: Realistic Earth and Moon global albedo maps for ground-truth image reconstruction benchmarks.
- `sgl_sim.orbital`: Keplerian and hovering focal-line orbital mechanics, Solar Oberth escape trajectories, swarm formation generators, image cylinder geometry, and station-keeping $\Delta v$.
- `sgl_sim.tradespace`: Grid evaluators across $(z_{\text{rec}}, D_{\text{tel}})$ mission parameters.
- `sgl_sim.targets`: NASA Exoplanet Archive and Astropy coordinate resolver, celestial antipodes, 3D heliocentric positioning, and proper-motion focal line drift.
- `sgl_sim.triage`: Universal SGL feasibility classifier, all-sky efficiency mapping ($72 \times 36$), mission co-alignment analyzer, and single-craft vs. swarm rotational blur modeling.
- `sgl_sim.manim_scenes`: Interactive GPU-accelerated 3Blue1Brown ManimGL scenes for visualizing the focal line, Einstein cross transitions, and wave PSF profiles.
- `sgl_sim.exporters`: Multi-extension NASA FITS (`astropy.io.fits`), CSV, and JSON exporters.
- `sgl_sim.web`: A synchronized interactive scientific dashboard powered by Flask, vanilla HTML5/Canvas, and responsive CSS.

# Acknowledgements

The author acknowledges foundational research on the Solar Gravitational Lens conducted by Slava G. Turyshev and Viktor T. Toth, as well as the broader Astropy community for developing core astronomical infrastructure [@Astropy2022; @Virtanen2020]. Software architecture, wave-optics algorithms, and code scaffolding were developed with assistance from Antigravity (Advanced Agentic Coding, Google DeepMind).

# References
