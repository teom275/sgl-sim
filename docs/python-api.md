# sgl-sim Python API

Every function accepts plain floats (SI units) or `astropy.units` quantities, and most return a dictionary of named results. Everything listed here can be imported from the top-level `sgl_sim` package.

The examples below run in order as a single script: later examples reuse variables from earlier ones, such as `u`, `psf_kernel_2d`, `snr` and `result`. The comments show the output with the default parameters.

- [Modules at a glance](#modules-at-a-glance)
- [1. Relativistic deflection & minimum focal distance](#1-relativistic-deflection--minimum-focal-distance)
- [2. Wave-optics Bessel PSF & peak magnification](#2-wave-optics-bessel-psf--peak-magnification)
- [3. Stellar oblateness (J2) astroid caustics & Einstein cross](#3-stellar-oblateness-j2-astroid-caustics--einstein-cross)
- [4. 2D Wiener deconvolution pipeline](#4-2d-wiener-deconvolution-pipeline)
- [5. NASA multi-extension FITS export](#5-nasa-multi-extension-fits-export)
- [6. Real exoplanet target resolver & 3D heliocentric telemetry](#6-real-exoplanet-target-resolver--3d-heliocentric-telemetry)
- [7. Exoplanet triage, sky efficiency & swarm motion blur](#7-exoplanet-triage-sky-efficiency--swarm-motion-blur)

## Modules at a glance

| Module | What it covers | Main functions |
|---|---|---|
| `sgl_sim.relativity` | Schwarzschild geometry, weak-field deflection, RK45 null geodesics | `schwarzschild_radius`, `photon_sphere_radius`, `critical_impact_parameter`, `weak_deflection_angle`, `focal_distance`, `integrate_strong_geodesic` |
| `sgl_sim.optics` | Focal line, Einstein ring, wave-optics PSF | `minimum_focal_distance`, `einstein_ring_properties`, `peak_magnification`, `psf_intensity`, `generate_2d_psf` |
| `sgl_sim.caustics` | J2 quadrupole astroid caustic and image solver | `astroid_caustic_semi_width`, `parametric_astroid`, `check_caustic_regime`, `solve_quadrupole_images`, `generate_caustic_map_2d` |
| `sgl_sim.deconvolution` | Coronal background, SNR budget, Wiener deconvolution | `baumbach_allen_coronal_brightness`, `calculate_snr`, `generate_exoplanet_map`, `wiener_deconvolution`, `compute_rmse`, `compute_ssim` |
| `sgl_sim.orbital` | Station keeping, image cylinder, ISCO | `orbital_velocity`, `orbital_period`, `image_cylinder_diameter`, `station_keeping_delta_v`, `isco_radius`, `check_isco` |
| `sgl_sim.tradespace` | Distance × aperture SNR trade | `evaluate_tradespace` |
| `sgl_sim.targets` | Exoplanet resolver and deployment geometry | `resolve_exoplanet`, `compute_sgl_deployment_vector`, `list_curated_targets`, `TOP_15_SGL_TARGETS` |
| `sgl_sim.triage` | Feasibility scoring, sky map, swarm motion blur | `score_exoplanet_candidate`, `get_ranked_catalog`, `generate_sky_efficiency_map`, `check_mission_coalignment`, `compute_motion_blur`, `CATALOG_12_CANDIDATES` |
| `sgl_sim.exporters` | FITS, CSV and JSON output | `build_simulation_fits_hdulist`, `export_fits`, `export_csv`, `export_json` |

Each function's docstring documents its parameters, units and returned keys, for example `help(sgl_sim.solve_quadrupole_images)`.

## 1. Relativistic deflection & minimum focal distance
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
# Solar R_s: 2953.25 m | Critical b_c: 7672.77 m

# Minimum focal crossing distance for grazing solar rays
z_min_info = minimum_focal_distance(mass=1.0 * u.M_sun, radius=1.0 * u.R_sun)
print(f"Solar Gravitational Lens z_min: {z_min_info['z_min_au']:.2f} AU")
# Solar Gravitational Lens z_min: 547.76 AU
```

## 2. Wave-optics Bessel PSF & peak magnification
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
# θ_E: 1607.57 mas | μ_max: 1.17e+11

# Generate 2D normalized Bessel J_0^2 PSF kernel
psf_kernel_2d = generate_2d_psf(grid_size=32, pixel_scale_m=1.0 * u.m, z_rec=z_rec, wavelength=wavelength)
```

## 3. Stellar oblateness (J2) astroid caustics & Einstein cross
```python
from sgl_sim import astroid_caustic_semi_width, solve_quadrupole_images

# Astroid semi-width at 650 AU
caustic = astroid_caustic_semi_width(z_rec=650.0 * u.AU, j2=2.2e-7)
print(f"Astroid Semi-Width: {caustic['a_caustic_m']:.2f} m")

# Receiver inside astroid at (x0, y0) = (0.0, 0.0) m -> 4 images (Einstein Cross)
sol_inside = solve_quadrupole_images(x0=0.0 * u.m, y0=0.0 * u.m, z_rec=650.0 * u.AU)
print(f"Regime: {sol_inside['regime']} | Resolved Images: {sol_inside['num_images']}")
print(f"Image Angles (deg): {[round(deg, 1) for deg in sol_inside['image_angles_deg']]}")
# Regime: inside | Resolved Images: 4
# Image Angles (deg): [0.0, 90.0, 180.0, 270.0]
```

## 4. 2D Wiener deconvolution pipeline
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
# Noisy RMSE: 0.2236 -> Deconvolved RMSE: 0.0179
# Reconstructed SSIM: 0.9976
```

## 5. NASA multi-extension FITS export
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

## 6. Real exoplanet target resolver & 3D heliocentric telemetry
```python
from sgl_sim import resolve_exoplanet, compute_sgl_deployment_vector

# Resolve real exoplanet from NASA Exoplanet Archive (or curated offline catalog)
target = resolve_exoplanet("Proxima Centauri b")
print(f"Target: {target['name']} | Host: {target['hostname']} ({target['distance_pc']:.2f} pc)")
# Target: Proxima Centauri b | Host: Proxima Centauri (1.30 pc)
print(f"Target Coordinates: RA {target['ra_deg']:.2f}°, Dec {target['dec_deg']:.2f}° [{target['constellation']}]")

# Compute exact antipodal placement and 3D heliocentric coordinates for arrival in 2048
ephem = compute_sgl_deployment_vector(target_data=target, z_rec_au=650.0 * u.AU, arrival_year=2048)
print(f"Required Telescope Direction (Antipode): RA {ephem['telescope_ra_deg']:.2f}°, Dec {ephem['telescope_dec_deg']:+.2f}° [{ephem['telescope_constellation']}]")
print(f"Heliocentric (X, Y, Z): ({ephem['x_au']:+.1f}, {ephem['y_au']:+.1f}, {ephem['z_au']:+.1f}) AU | Norm: {ephem['vector_norm_au']:.1f} AU")
print(f"Ecliptic Inclination: {ephem['ecliptic_inclination_deg']:.2f}° out of ecliptic plane")
print(f"Light-Travel Comms Delay: {ephem['light_delay_days']:.2f} light-days ({ephem['light_delay_hours']:.1f} hours)")
print(f"Image Cylinder Diameter: D_img ≈ {ephem['image_diameter_km']:.1f} km | Proper-Motion Drift: {ephem['proper_motion_drift_m_s']:.1f} m/s")
```

## 7. Exoplanet triage, sky efficiency & swarm motion blur
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
# Candidate: TRAPPIST-1 e | Score: 78.2/100 | Tier: Tier 1: Prime Swarm/Single Target
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
