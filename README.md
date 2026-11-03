# sgl-sim: Gravitational Lens Telescopes & Mission Design Simulator

[![CI](https://img.shields.io/badge/CI-passing-brightgreen.svg?logo=github-actions)](https://github.com/teom275/sgl-sim)
[![JOSS Status](https://img.shields.io/badge/JOSS-status%3A%20draft-blue)](paper/paper.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](pyproject.toml)
[![Astropy-compatible](https://img.shields.io/badge/astropy-compatible-orange.svg)](https://www.astropy.org/)
[![ORCID](https://img.shields.io/badge/ORCID-0009--0008--8025--8576-A6CE39.svg?logo=orcid&logoColor=white)](https://orcid.org/0009-0008-8025-8576)
[![DOI](https://img.shields.io/badge/DOI-pending-lightgrey.svg)](https://github.com/teom275/sgl-sim)

**`sgl-sim`** is an open-source, peer-review-ready scientific Python package and interactive mission-design simulator for **Gravitational Lens Telescopes (Solar & Black Hole Focal Line Missions)**. 

Adhering strictly to **Journal of Open Source Software (JOSS)** and **Astropy package** standards, `sgl-sim` models:
- **Relativistic Null Geodesics:** Schwarzschild metrics, critical photon capture parameters ($b_c = \frac{3\sqrt{3}}{2} R_s$), weak-field deflections, and RK45 numerical null geodesic integration.
- **Wave Optics & Focal Line Properties:** Finite diffraction-limited Bessel $J_0^2$ point spread functions (PSF), on-axis peak wave magnifications ($\mu_{\max} \sim 10^{11}$), and minimum focal distances ($z_{\min} \approx 547.8\text{ AU}$ for the Sun).
- **Stellar Oblateness Caustics ($J_2$):** Analytical and numerical solvers for the quadrupolar lens equation, predicting transverse astroid caustics, 4-image Einstein Cross configurations, cusp arcs, and fold bifurcations.
- **Noise Modeling & Exoplanet Deconvolution:** Baumbach-Allen solar K-coronal brightness backgrounds, per-pixel SNR budgets, and 2D Fourier-space Wiener deconvolution for surface albedo recovery.
- **Orbital Mechanics & Station-Keeping:** Focal-line hovering $\Delta v$, Keplerian orbital velocities, black hole ISCO checks, and image cylinder scan budgets.
- **Multi-Extension FITS Exporters:** NASA/Astropy compliant `.fits` files (`CAUSTIC_MAP`, `RAW_DETECTOR`, `DECONV_EXO`, and binary table `PSF_PROFILE`).
- **Real Exoplanet Target Resolver & 3D Heliocentric Telemetry:** Direct resolution via NASA Exoplanet Archive TAP API / Astropy coordinates with curated fallback for top 15 targets (Proxima Cen b, TRAPPIST-1, LHS 1140 b, etc.). Computes exact 3D heliocentric positioning, celestial antipode (RA/Dec), out-of-ecliptic inclination, proper-motion lateral drift velocity, and interstellar light-delay communication budgets.
- **SGL Target Triage, Sky Efficiency & Swarm Motion-Blur Analyzer:** Universal SGL Feasibility Index ($0-100$) and mission Tier classifier based on photon SNR, scan logistics, ecliptic access ($\cos^2\beta$), and blur immunity; full-sky Solar Lens efficiency map ($72 \times 36$); trajectory co-alignment analyzer ($\Delta \theta \le 3.0^\circ$); and single-spacecraft vs. multi-satellite swarm ($N=1 \dots 16$) rotational motion-blur modeling ($\eta_{\text{blur}} = t_{\text{scan}} / t_{\text{blur}}$).
- **Interactive Mission Dashboard & Web Simulator:** a hosted Flask dashboard plus a static in-browser simulator on GitHub Pages.

---

## Installation

### Prerequisites
- Python 3.9, 3.10, 3.11, or 3.12
- Standard virtual environment (`venv` or `conda`)

### Install from Source
```bash
git clone https://github.com/teom275/sgl-sim.git
cd sgl-sim

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode with test dependencies
pip install -e ".[test]"
```

---

## Python API Quickstart

### 1. Relativistic Deflection & Minimum Focal Distance
```python
from astropy import units as u
from sgl_sim import (
    schwarzschild_radius,
    critical_impact_parameter,
    minimum_focal_distance,
    focal_distance
)

# Calculate Schwarzschild radius & photon capture threshold
rs_sun = schwarzschild_radius(1.0 * u.M_sun)
b_crit = critical_impact_parameter(1.0 * u.M_sun)
print(f"Solar R_s: {rs_sun:.2f} m | Critical b_c: {b_crit:.2f} m")

# Minimum focal crossing distance for grazing solar rays
z_min_info = minimum_focal_distance(mass=1.0 * u.M_sun, radius=1.0 * u.R_sun)
print(f"Solar Gravitational Lens z_min: {z_min_info['z_min_au']:.2f} AU")
# Output: Solar Gravitational Lens z_min: 547.76 AU
```

### 2. Wave-Optics Bessel PSF & Peak Magnification
```python
from sgl_sim import (
    einstein_ring_properties,
    peak_magnification,
    psf_intensity,
    generate_2d_psf
)

z_rec = 650.0 * u.AU
wavelength = 1.0 * u.micron

# Einstein ring angular radius and peak wave magnification
ring = einstein_ring_properties(z_rec=z_rec)
mu_max = peak_magnification(wavelength=wavelength)
print(f"θ_E: {ring['theta_E_arcsec'] * 1000:.2f} mas | μ_max: {mu_max:.2e}")

# Generate 2D normalized Bessel J_0^2 PSF kernel
psf_kernel_2d = generate_2d_psf(grid_size=32, pixel_scale_m=1.0 * u.m, z_rec=z_rec, wavelength=wavelength)
```

### 3. Stellar Oblateness ($J_2$) Astroid Caustics & Einstein Cross
```python
from sgl_sim import astroid_caustic_semi_width, solve_quadrupole_images

# Astroid semi-width at 650 AU
caustic = astroid_caustic_semi_width(z_rec=650.0 * u.AU, j2=2.2e-7)
print(f"Astroid Semi-Width: {caustic['a_caustic_m']:.2f} m")

# Receiver inside astroid at (x0, y0) = (0.0, 0.0) m -> 4 images (Einstein Cross)
sol_inside = solve_quadrupole_images(x0=0.0 * u.m, y0=0.0 * u.m, z_rec=650.0 * u.AU)
print(f"Regime: {sol_inside['regime']} | Resolved Images: {sol_inside['num_images']}")
print(f"Image Angles (deg): {[round(deg, 1) for deg in sol_inside['image_angles_deg']]}")
```

### 4. 2D Wiener Deconvolution Pipeline
```python
from sgl_sim import generate_exoplanet_map, wiener_deconvolution, calculate_snr

# Calculate per-pixel SNR for 1m telescope, 1-day integration
snr_budget = calculate_snr(z_rec=650.0 * u.AU, aperture_m=1.0 * u.m)
snr = snr_budget["snr"]
print(f"Per-pixel SNR: {snr:.1f}")

# Generate ground truth exoplanet map (continents + oceans + polar caps)
ground_truth = generate_exoplanet_map(grid_size=32, seed=42)

# Deconvolve blurred + noise-degraded image
result = wiener_deconvolution(ground_truth=ground_truth, psf_kernel=psf_kernel_2d, snr=snr)
print(f"Noisy RMSE: {result['rmse_noisy']:.4f} -> Deconvolved RMSE: {result['rmse_deconvolved']:.4f}")
print(f"Reconstructed SSIM: {result['ssim_deconvolved']:.4f}")
```

### 5. NASA Multi-Extension FITS Export
```python
from sgl_sim import export_fits

# Export complete simulation metadata, 2D images, and radial PSF to standard FITS
fits_path = export_fits(
    sim_data={
        "mass_solar": 1.0,
        "z_rec_au": 650.0,
        "j2": 2.2e-7,
        "wavelength_m": 1.0e-6,
        "snr": snr,
        "convolved_noisy": result["convolved_noisy"],
        "deconvolved": result["deconvolved"],
        "psf_rho_m": [0.0, 10.0, 20.0, 30.0],
        "psf_intensity": [1.0, 0.45, 0.08, 0.02],
    },
    output_path="sgl_mission_run.fits"
)
print(f"Saved NASA-standard FITS file to {fits_path}")
```

### 6. Real Exoplanet Target Resolver & 3D Heliocentric Telemetry
```python
from sgl_sim import resolve_exoplanet, compute_sgl_deployment_vector

# Resolve real exoplanet from NASA Exoplanet Archive (or curated offline catalog)
target = resolve_exoplanet("Proxima Centauri b")
print(f"Target: {target['name']} | Host: {target['hostname']} ({target['distance_pc']:.2f} pc)")
print(f"Target Coordinates: RA {target['ra_deg']:.2f}°, Dec {target['dec_deg']:.2f}° [{target['constellation']}]")

# Compute exact antipodal placement and 3D heliocentric coordinates for arrival in 2048
ephem = compute_sgl_deployment_vector(target_data=target, z_rec_au=650.0 * u.AU, arrival_year=2048)
print(f"Required Telescope Direction (Antipode): RA {ephem['telescope_ra_deg']:.2f}°, Dec {ephem['telescope_dec_deg']:+.2f}° [{ephem['telescope_constellation']}]")
print(f"Heliocentric (X, Y, Z): ({ephem['x_au']:+.1f}, {ephem['y_au']:+.1f}, {ephem['z_au']:+.1f}) AU | Norm: {ephem['vector_norm_au']:.1f} AU")
print(f"Ecliptic Inclination: {ephem['ecliptic_inclination_deg']:.2f}° out of ecliptic plane")
print(f"Light-Travel Comms Delay: {ephem['light_delay_days']:.2f} light-days ({ephem['light_delay_hours']:.1f} hours)")
print(f"Image Cylinder Diameter: D_img ≈ {ephem['image_diameter_km']:.1f} km | Proper-Motion Drift: {ephem['proper_motion_drift_m_s']:.1f} m/s")
```

### 7. Exoplanet Triage, Sky Efficiency & Swarm Motion-Blur Analyzer
```python
from sgl_sim import (
    score_exoplanet_candidate,
    compute_motion_blur,
    get_ranked_catalog,
    check_mission_coalignment,
    generate_sky_efficiency_map,
)

# 1. Universal SGL Feasibility Scoring & Ecliptic Access
eval_res = score_exoplanet_candidate(
    name="TRAPPIST-1 e",
    ra_deg=346.62,
    dec_deg=-5.04,
    dist_pc=12.43,
    radius_earth=0.92,
    rot_period_hrs=146.4,
    tidally_locked=True,
    proper_motion_mas_yr=1005.0,
    z_rec_au=650.0,
)
print(f"Candidate: {eval_res['name']} | Score: {eval_res['sgl_score']}/100 | Tier: {eval_res['tier']}")
print(f"Ecliptic Access: {eval_res['ecliptic_access_score']:.2f} (beta = {eval_res['ecliptic_lat_deg']:.2f}°)")

# 2. Rotational Motion Blur: Single Spacecraft vs. Multi-Satellite Swarm
single = compute_motion_blur(image_diameter_km=5.0, planet_rot_period_hours=24.0, num_satellites=1)
swarm = compute_motion_blur(image_diameter_km=5.0, planet_rot_period_hours=24.0, num_satellites=8)
print(f"Single (N=1) Blur: eta = {single['eta_blur']:.1f} (RMSE: {single['rmse']:.3f})")
print(f"Swarm (N=8) Blur: eta = {swarm['eta_blur']:.2f} (RMSE: {swarm['rmse']:.3f})")

# 3. Check Multi-Planet Mission Co-Alignment (e.g. TRAPPIST-1 system)
active = [{"name": "TRAPPIST-1 e", "ra_deg": 346.62, "dec_deg": -5.04}]
coalign = check_mission_coalignment(active, new_target_ra=346.62, new_target_dec=-5.04)
print(f"Co-aligned? {coalign['is_coaligned']} -> {coalign['message']}")
```

---

## Try it online

- **Web simulator** (GitHub Pages, no install): <https://teom275.github.io/sgl-sim/>. It runs the focal-line, Einstein-cross and wave-optics scenes in the browser and includes the ManimGL demo videos. The site lives in [`docs/`](docs/).
- **Mission dashboard** (Flask app on Render): deploy your own copy with one click.

  [![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/teom275/sgl-sim)

![sgl-sim web simulator](docs/assets/web_simulator.png)

---

## Mission Dashboard

![sgl-sim mission dashboard](docs/assets/dashboard.png)

A web app for designing a lens mission. Every number comes from the Python API.

```bash
# Local development server
sgl-sim-server --host 127.0.0.1 --port 5000      # or: python -m sgl_sim.web.app

# Production server (what Render runs)
pip install ".[server]"
gunicorn --bind 0.0.0.0:8000 sgl_sim.web.app:app
```

Then open `http://127.0.0.1:5000`.

- **Optical-axis ruler:** shows the Sun, where the focal line begins and where the spacecraft sits. Below it are the headline numbers: z_min, Einstein ring, peak gain, per-pixel SNR and the planet image size.
- **Optics:** weak-field ray bundle for a star, or strong-field geodesics around a black hole. Also the J₀² PSF profile and the telescope view of the Einstein ring.
- **Caustic:** drag the spacecraft across the J₂ astroid and watch the four images merge into two.
- **Imaging:** ground truth → detector → Wiener reconstruction, and the SNR trade across distance × aperture.
- **Targets:** NASA Exoplanet Archive / curated resolver with antipodal pointing, heliocentric position, light delay and proper-motion drift.
- **Triage:** all-sky efficiency map, feasibility scoring with co-alignment check, single craft vs. swarm motion blur, and the ranked catalogue.
- **Downloads:** FITS, CSV and JSON of the current scenario.

### Hosting

- **Dashboard on Render:** [`render.yaml`](render.yaml) is a Render blueprint for the free plan. Use the button above, or in Render choose *New → Blueprint* and pick this repository. It redeploys on every push to `main`.
- **Web simulator on GitHub Pages:** in the repository settings, open *Pages* and serve from the `main` branch, `/docs` folder. To link the dashboard from the site, set `DASHBOARD_URL` in [`docs/sim/config.js`](docs/sim/config.js).

---

## Interactive ManimGL Scenes (3Blue1Brown `manim`)

![sgl-sim ManimGL interactive scenes](docs/assets/manim_scenes_preview.png)

`sgl_sim.manim_scenes` holds three interactive scenes built on [ManimGL](https://github.com/3b1b/manim), the animation engine 3Blue1Brown uses for its videos. Each scene first plays a short animated demo. After that the window stays open and every control is live. All the numbers come from the regular `sgl_sim` API.

```bash
pip install -e ".[manim]"          # ManimGL + small compatibility shims

manimgl src/sgl_sim/manim_scenes/sgl_interactive.py SolarLensFocalLine
manimgl src/sgl_sim/manim_scenes/sgl_interactive.py EinsteinCrossExplorer
manimgl src/sgl_sim/manim_scenes/sgl_interactive.py WavePSFExplorer
```

| Scene | What you can do |
|---|---|
| `SolarLensFocalLine` | Drag the lens mass, lens radius and receiver distance. Rays cross the axis at $z(b) = b^2 / 2R_s$, the focal line starts at $z_{\min}$, and the Einstein-ring ray pair that reaches the spacecraft is highlighted. Readouts show $\theta_E$ and $\mu_{\max}$. |
| `EinsteinCrossExplorer` | Drag the receiver (or click anywhere) in the focal plane. The $J_2$ astroid caustic grows and shrinks with $J_2$ and $z_{\text{rec}}$. The telescope view shows the 4 → 2 image transition (Einstein cross) and the azimuthal brightness of the ring. |
| `WavePSFExplorer` | Change the wavelength and $z_{\text{rec}}$ to see the $J_0^2$ PSF profile, a 2D transverse-plane image, the radius of the first dark ring (about 5 cm at 650 AU and 1 µm) and the peak gain. |

Useful ManimGL flags:
- `-w` renders the demo to an MP4 without opening a window.
- `-s` saves only the final frame.
- `-l` / `-m` render at lower resolution.
- `-e` opens an IPython shell on the live scene (e.g. `self.s_mass.set_value(2.0)`).

No LaTeX installation is needed. The drawing geometry lives in `sgl_sim/manim_scenes/model.py`, which is pure NumPy and is tested in `tests/test_manim_model.py`.

---

## Running Automated Tests

Run the complete test suite with coverage reporting:

```bash
pytest -v --cov=sgl_sim --cov-report=term-missing tests/
```

All tests verify core astrophysical benchmarks:
- Solar minimum focal distance $z_{\min} \approx 547.8\text{ AU}$
- Black hole critical capture at $b \le b_c \approx 2.598 R_s$
- Quadrupolar 4-image Einstein Cross solutions inside $J_2$ astroid
- Wiener deconvolution RMSE reduction and SSIM improvement
- Valid multi-extension FITS file generation (`astropy.io.fits`)

---

## Citation

If you use `sgl-sim` in your research, mission design studies, or educational activities, please cite the JOSS manuscript and software repository:

### BibTeX
```bibtex
@software{Maggio2026_sglsim,
  author = {Maggio, Teo},
  title = {sgl-sim: Scientific Mission Design & Wave Optics Simulator for Gravitational Lens Telescopes},
  year = {2026},
  howpublished = {\url{https://github.com/teom275/sgl-sim}},
  note = {Journal of Open Source Software (in review / submission draft)}
}
```

**Lead Author:** Teo Maggio ([ORCID: 0009-0008-8025-8576](https://orcid.org/0009-0008-8025-8576))

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
